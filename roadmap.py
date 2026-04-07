#!/usr/bin/env python3
"""
Roadmap Generator
-----------------
Generates structured roadmaps for career, learning, and personal goals.
Features: visual timeline, step-by-step checklist, weekly plan,
          progress tracking, save/reload, and PDF export.

Requirements:
    pip install anthropic reportlab

Usage:
    python roadmap.py
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
SKILL_PATH = BASE_DIR / "SKILL.md"
SAVES_DIR  = BASE_DIR / "saved_roadmaps"
SAVES_DIR.mkdir(exist_ok=True)

# ── Colors ─────────────────────────────────────────────────────────────────────
PHASE_COLORS = ["#7F77DD", "#1D9E75", "#D85A30", "#D4537E", "#378ADD"]
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
PURPLE = "\033[35m"
RED    = "\033[31m"

# ── Helpers ────────────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header(text: str):
    width = 60
    print(f"\n{PURPLE}{BOLD}{'─' * width}{RESET}")
    print(f"{PURPLE}{BOLD}  {text}{RESET}")
    print(f"{PURPLE}{BOLD}{'─' * width}{RESET}\n")

def load_skill() -> str:
    if not SKILL_PATH.exists():
        print(f"{RED}Error: SKILL.md not found at {SKILL_PATH}{RESET}")
        sys.exit(1)
    return SKILL_PATH.read_text(encoding="utf-8")

def save_name(goal: str) -> str:
    """Convert goal text to a safe filename."""
    slug = re.sub(r"[^a-z0-9]+", "_", goal.lower())[:40].strip("_")
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{slug}_{ts}.json"

# ── API Call ───────────────────────────────────────────────────────────────────

def generate_roadmap(goal: str, api_key: str) -> dict:
    """Call Claude API using SKILL.md as the system prompt."""
    skill = load_skill()
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            f"{skill}\n\n"
            "IMPORTANT: Reply with raw JSON only. "
            "No markdown fences, no explanation, no extra text."
        ),
        messages=[
            {"role": "user", "content": f"Create a roadmap for this goal: {goal}"}
        ],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)

# ── Goal Clarification Chat ────────────────────────────────────────────────────

def clarify_goal(goal: str, api_key: str) -> str:
    """
    Have a short 3-question chat with Claude to clarify the goal.
    Returns an enriched goal string to pass into generate_roadmap.
    """
    client = anthropic.Anthropic(api_key=api_key)

    print(f"\n{PURPLE}{BOLD}  Let me ask you 3 quick questions to personalize your roadmap.{RESET}")
    print(f"  {DIM}(Press Enter to skip any question){RESET}\n")

    # ── Step 1: Claude generates 3 smart questions based on the goal ──
    print(f"  {CYAN}Thinking of the right questions for your goal...{RESET}\n")

    q_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=(
            "You are a goal coach. Given a goal, generate exactly 3 short clarifying questions "
            "that will help you build a much more personalized roadmap. "
            "The questions should uncover: current experience level, available time per week, "
            "and any specific constraints or context. "
            "Reply with ONLY the 3 questions, numbered 1. 2. 3. — nothing else."
        ),
        messages=[
            {"role": "user", "content": f"Goal: {goal}"}
        ],
    )

    questions_text = q_response.content[0].text.strip()
    questions = [
        line.strip()
        for line in questions_text.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]

    # ── Step 2: Ask the user each question and collect answers ──
    answers = []
    for i, question in enumerate(questions[:3], 1):
        # Strip the leading number if present
        clean_q = re.sub(r"^\d+[\.\)]\s*", "", question)
        print(f"  {CYAN}{BOLD}Question {i}:{RESET} {clean_q}")
        answer = input(f"  {YELLOW}Your answer:{RESET} ").strip()
        answers.append(f"Q: {clean_q}\nA: {answer if answer else 'No answer provided'}")
        print()

    # ── Step 3: Build enriched goal context ──
    qa_block = "\n".join(answers)
    enriched_goal = (
        f"Goal: {goal}\n\n"
        f"Additional context from user:\n{qa_block}"
    )

    print(f"  {GREEN}Got it! Generating your personalized roadmap now...{RESET}\n")
    return enriched_goal


# ── Display ────────────────────────────────────────────────────────────────────

def print_timeline(roadmap: dict):
    """Print a visual ASCII phase timeline."""
    phases = roadmap["phases"]
    print(f"{BOLD}  PHASE TIMELINE{RESET}")
    print()

    blocks = []
    for p in phases:
        label = f"  {p['phase']}. {p['title']}  "
        sub   = f"  ({p['duration']})  "
        width = max(len(label), len(sub))
        blocks.append((label.center(width), sub.center(width), width))

    # Top border
    print("  " + "  ".join("┌" + "─" * (w - 2) + "┐" for _, _, w in blocks))
    # Phase name row
    print("  " + "  ".join(f"│{CYAN}{BOLD}{t}{RESET}│" for t, _, _ in blocks))
    # Duration row
    print("  " + "  ".join(f"│{DIM}{s}{RESET}│" for _, s, _ in blocks))
    # Bottom border
    print("  " + "  ".join("└" + "─" * (w - 2) + "┘" for _, _, w in blocks))
    # Arrows between phases
    if len(phases) > 1:
        arrows = []
        for i, (_, _, w) in enumerate(blocks):
            if i < len(blocks) - 1:
                arrows.append(" " * w + f"  {YELLOW}→{RESET}")
            else:
                arrows.append("")
        print("  " + "".join(arrows))

    print()
    print(f"  {DIM}Total duration: {roadmap['duration']}{RESET}\n")

def print_checklist(roadmap: dict):
    """Print the step-by-step checklist with progress tracking."""
    for phase in roadmap["phases"]:
        total = len(phase["steps"])
        done  = sum(1 for s in phase["steps"] if s.get("done"))
        bar   = progress_bar(done, total)

        print(f"{BOLD}{CYAN}Phase {phase['phase']}: {phase['title']}{RESET}  "
              f"{bar}  {DIM}{done}/{total} done{RESET}")
        print()

        for step in phase["steps"]:
            tick = f"{GREEN}✓{RESET}" if step.get("done") else f"{DIM}○{RESET}"
            title_color = DIM if step.get("done") else BOLD
            print(f"  {tick}  {title_color}[{step['id']}] {step['title']}{RESET}")
            if not step.get("done"):
                print(f"      {DIM}{step['description']}{RESET}")
                if step.get("resources"):
                    res = ", ".join(step["resources"])
                    print(f"      {YELLOW}Resources:{RESET} {DIM}{res}{RESET}")
            print()

def print_weekly_plan(roadmap: dict):
    """Print the weekly/monthly plan."""
    for phase in roadmap["phases"]:
        print(f"{BOLD}{CYAN}Phase {phase['phase']}: {phase['title']}{RESET}\n")
        for week in phase.get("weekly_plan", []):
            print(f"  {BOLD}Week {week['week']}{RESET}  —  {week['focus']}")
            for task in week["tasks"]:
                print(f"    {YELLOW}•{RESET} {task}")
            print()

def print_summary(roadmap: dict):
    """Print success metrics and pitfalls."""
    print(f"{BOLD}{GREEN}Success Metrics{RESET}")
    for m in roadmap.get("success_metrics", []):
        print(f"  {GREEN}✓{RESET} {m}")
    print()

    print(f"{BOLD}{RED}Common Pitfalls to Avoid{RESET}")
    for p in roadmap.get("common_pitfalls", []):
        print(f"  {RED}✗{RESET} {p}")
    print()

def progress_bar(done: int, total: int, width: int = 12) -> str:
    if total == 0:
        return f"[{'─' * width}]"
    filled = int(width * done / total)
    bar = "█" * filled + "─" * (width - filled)
    return f"[{GREEN}{bar}{RESET}]"

def overall_progress(roadmap: dict) -> tuple[int, int]:
    total = sum(len(p["steps"]) for p in roadmap["phases"])
    done  = sum(s.get("done", False) for p in roadmap["phases"] for s in p["steps"])
    return done, total

# ── Progress Tracking ──────────────────────────────────────────────────────────

def toggle_step(roadmap: dict):
    """Let the user mark a step as done or not done."""
    print("Enter a step ID to toggle (e.g. 1.2), or press Enter to cancel:")
    step_id = input("  > ").strip()
    if not step_id:
        return

    for phase in roadmap["phases"]:
        for step in phase["steps"]:
            if step["id"] == step_id:
                step["done"] = not step.get("done", False)
                status = f"{GREEN}done{RESET}" if step["done"] else f"{DIM}not done{RESET}"
                print(f"\n  [{step_id}] {step['title']} → marked as {status}\n")
                return

    print(f"\n  {RED}Step ID '{step_id}' not found.{RESET}\n")

# ── Save / Load ────────────────────────────────────────────────────────────────

def save_roadmap(roadmap: dict) -> Path:
    filename = save_name(roadmap["goal"])
    path = SAVES_DIR / filename
    path.write_text(json.dumps(roadmap, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def list_saved() -> list[Path]:
    return sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

def load_saved_roadmap() -> dict | None:
    files = list_saved()
    if not files:
        print(f"\n  {DIM}No saved roadmaps found.{RESET}\n")
        return None

    print(f"\n{BOLD}Saved Roadmaps:{RESET}\n")
    for i, f in enumerate(files, 1):
        data = json.loads(f.read_text(encoding="utf-8"))
        done, total = overall_progress(data)
        bar = progress_bar(done, total, width=10)
        print(f"  {CYAN}{i}.{RESET} {data['goal']}")
        print(f"     {bar} {done}/{total} steps  —  {DIM}{f.name}{RESET}\n")

    print("Enter number to load, or press Enter to cancel:")
    choice = input("  > ").strip()
    if not choice.isdigit():
        return None

    idx = int(choice) - 1
    if 0 <= idx < len(files):
        return json.loads(files[idx].read_text(encoding="utf-8"))

    print(f"  {RED}Invalid choice.{RESET}")
    return None

# ── PDF Export ─────────────────────────────────────────────────────────────────

def export_pdf(roadmap: dict) -> Path:
    """Export the full roadmap to a formatted PDF using reportlab."""
    filename = save_name(roadmap["goal"]).replace(".json", ".pdf")
    path = BASE_DIR / filename

    doc    = SimpleDocTemplate(str(path), pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Custom styles
    title_style = ParagraphStyle("Title2", parent=styles["Title"],
                                 fontSize=22, textColor=colors.HexColor("#3C3489"),
                                 spaceAfter=6)
    h1_style    = ParagraphStyle("H1", parent=styles["Heading1"],
                                 fontSize=14, textColor=colors.HexColor("#534AB7"),
                                 spaceBefore=16, spaceAfter=4)
    h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                 fontSize=12, textColor=colors.HexColor("#085041"),
                                 spaceBefore=10, spaceAfter=2)
    body_style  = ParagraphStyle("Body2", parent=styles["Normal"],
                                 fontSize=10, leading=15, spaceAfter=4)
    small_style = ParagraphStyle("Small", parent=styles["Normal"],
                                 fontSize=9, textColor=colors.HexColor("#5F5E5A"),
                                 leading=13)
    done_style  = ParagraphStyle("Done", parent=styles["Normal"],
                                 fontSize=10, textColor=colors.HexColor("#888780"),
                                 leading=15, strikethrough=True)

    # ── Title ──
    story.append(Paragraph(f"Roadmap: {roadmap['goal']}", title_style))
    story.append(Paragraph(
        f"Category: {roadmap['category'].title()}  |  Duration: {roadmap['duration']}",
        small_style))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#CECBF6"), spaceAfter=12))

    # ── Phase Timeline Table ──
    story.append(Paragraph("Phase Timeline", h1_style))
    phase_data = [["Phase", "Title", "Duration"]]
    for p in roadmap["phases"]:
        phase_data.append([str(p["phase"]), p["title"], p["duration"]])

    tbl = Table(phase_data, colWidths=[2*cm, 9*cm, 5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#534AB7")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#EEEDFE"), colors.HexColor("#F8F7FF")]),
        ("FONTSIZE",    (0, 1), (-1, -1), 10),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#CECBF6")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 16))

    # ── Phases: Steps + Weekly Plan ──
    for phase in roadmap["phases"]:
        story.append(Paragraph(
            f"Phase {phase['phase']}: {phase['title']}  ({phase['duration']})", h1_style))

        # Steps checklist
        story.append(Paragraph("Steps", h2_style))
        for step in phase["steps"]:
            tick  = "✓" if step.get("done") else "○"
            style = done_style if step.get("done") else body_style
            story.append(Paragraph(f"{tick}  <b>[{step['id']}]</b> {step['title']}", style))
            if not step.get("done"):
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{step['description']}", small_style))
                if step.get("resources"):
                    res = ", ".join(step["resources"])
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Resources: {res}</i>", small_style))
            story.append(Spacer(1, 4))

        # Weekly plan
        if phase.get("weekly_plan"):
            story.append(Paragraph("Weekly Plan", h2_style))
            for week in phase["weekly_plan"]:
                story.append(Paragraph(
                    f"<b>Week {week['week']}</b> — {week['focus']}", body_style))
                for task in week["tasks"]:
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;• {task}", small_style))
                story.append(Spacer(1, 4))

        story.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.HexColor("#D3D1C7"), spaceAfter=8))

    # ── Success Metrics ──
    story.append(Paragraph("Success Metrics", h1_style))
    for m in roadmap.get("success_metrics", []):
        story.append(Paragraph(f"✓  {m}", body_style))

    story.append(Spacer(1, 10))

    # ── Common Pitfalls ──
    story.append(Paragraph("Common Pitfalls to Avoid", h1_style))
    for p in roadmap.get("common_pitfalls", []):
        story.append(Paragraph(f"✗  {p}", body_style))

    # ── Footer note ──
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y')} · Powered by Claude API",
        small_style))

    doc.build(story)
    return path

# ── Main Menu ──────────────────────────────────────────────────────────────────

def show_roadmap_menu(roadmap: dict, save_path: Path):
    """Interactive menu for a loaded roadmap."""
    while True:
        clear()
        header(f"Your Roadmap: {roadmap['goal']}")

        done, total = overall_progress(roadmap)
        bar = progress_bar(done, total, width=20)
        print(f"  Overall Progress: {bar}  {done}/{total} steps complete\n")

        print(f"  {CYAN}1.{RESET} View Phase Timeline")
        print(f"  {CYAN}2.{RESET} View Step-by-Step Checklist")
        print(f"  {CYAN}3.{RESET} View Weekly Plan")
        print(f"  {CYAN}4.{RESET} View Success Metrics & Pitfalls")
        print(f"  {CYAN}5.{RESET} Mark a Step as Done / Not Done")
        print(f"  {CYAN}6.{RESET} Export to PDF")
        print(f"  {CYAN}7.{RESET} Save Progress")
        print(f"  {CYAN}0.{RESET} Back to Main Menu")
        print()

        choice = input("  Choose an option: ").strip()

        if choice == "1":
            clear()
            header("Phase Timeline")
            print_timeline(roadmap)
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "2":
            clear()
            header("Step-by-Step Checklist")
            print_checklist(roadmap)
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "3":
            clear()
            header("Weekly Plan")
            print_weekly_plan(roadmap)
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "4":
            clear()
            header("Success Metrics & Pitfalls")
            print_summary(roadmap)
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "5":
            clear()
            header("Toggle Step")
            print_checklist(roadmap)
            toggle_step(roadmap)
            # Auto-save after toggling
            save_path.write_text(
                json.dumps(roadmap, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  {GREEN}Progress saved.{RESET}")
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "6":
            print(f"\n  {CYAN}Exporting PDF...{RESET}")
            pdf_path = export_pdf(roadmap)
            print(f"  {GREEN}PDF saved to: {pdf_path}{RESET}\n")
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "7":
            save_path.write_text(
                json.dumps(roadmap, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n  {GREEN}Roadmap saved to: {save_path}{RESET}\n")
            input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "0":
            break

def main():
    clear()
    header("Roadmap Generator — Powered by Claude AI")

    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  {YELLOW}Enter your Anthropic API key:{RESET}")
        print(f"  {DIM}(Or set the ANTHROPIC_API_KEY environment variable){RESET}\n")
        api_key = input("  API Key: ").strip()
        if not api_key:
            print(f"\n  {RED}No API key provided. Exiting.{RESET}")
            sys.exit(1)

    while True:
        clear()
        header("Main Menu")
        print(f"  {CYAN}1.{RESET} Generate a new roadmap")
        print(f"  {CYAN}2.{RESET} Load a saved roadmap")
        print(f"  {CYAN}0.{RESET} Exit")
        print()

        choice = input("  Choose an option: ").strip()

        if choice == "1":
            clear()
            header("New Roadmap")
            print("  What goal would you like to achieve?")
            print(f"  {DIM}Examples:")
            print(f"    - Become a UX designer in 6 months")
            print(f"    - Learn Spanish to conversational level")
            print(f"    - Run a 5K without stopping{RESET}\n")
            goal = input("  Your goal: ").strip()
            if not goal:
                continue

            try:
                # Ask if they want the clarification chat
                print(f"\n  {PURPLE}Would you like me to ask 3 quick questions")
                print(f"  to make your roadmap more personalized? {DIM}(recommended){RESET}")
                print(f"  {CYAN}1.{RESET} Yes, ask me questions first")
                print(f"  {CYAN}2.{RESET} No, generate roadmap directly")
                chat_choice = input("\n  Choose: ").strip()

                if chat_choice == "1":
                    enriched_goal = clarify_goal(goal, api_key)
                else:
                    enriched_goal = goal
                    print(f"\n  {CYAN}Generating your roadmap...{RESET}\n")

                roadmap   = generate_roadmap(enriched_goal, api_key)
                save_path = SAVES_DIR / save_name(roadmap["goal"])
                save_path.write_text(
                    json.dumps(roadmap, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  {GREEN}Roadmap generated and saved!{RESET}")
                show_roadmap_menu(roadmap, save_path)

            except json.JSONDecodeError as e:
                print(f"\n  {RED}Failed to parse roadmap JSON: {e}{RESET}\n")
                input(f"  {DIM}Press Enter to continue...{RESET}")
            except Exception as e:
                print(f"\n  {RED}Error: {e}{RESET}\n")
                input(f"  {DIM}Press Enter to continue...{RESET}")

        elif choice == "2":
            roadmap = load_saved_roadmap()
            if roadmap:
                save_path = SAVES_DIR / save_name(roadmap["goal"])
                # Find the actual saved file
                files = list_saved()
                # Match by goal
                for f in files:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data["goal"] == roadmap["goal"]:
                        save_path = f
                        break
                show_roadmap_menu(roadmap, save_path)

        elif choice == "0":
            print(f"\n  {DIM}Goodbye!{RESET}\n")
            break

if __name__ == "__main__":
    main()