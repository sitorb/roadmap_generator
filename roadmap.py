from dotenv import load_dotenv
load_dotenv()

import anthropic
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Load SKILL.md ──────────────────────────────────────────────────────────────
SKILL_PATH = Path(__file__).parent / "SKILL.md"

def load_skill():
    if not SKILL_PATH.exists():
        print("❌  SKILL.md not found. Make sure it's in the same folder as this script.")
        sys.exit(1)
    return SKILL_PATH.read_text(encoding="utf-8")

# ── Pretty-print the roadmap ───────────────────────────────────────────────────
def display_roadmap(data: dict):
    print("\n" + "═" * 60)
    print(f"  🎯  ROADMAP: {data['goal']}")
    print(f"  ⏱   Total duration: {data['total_duration']}")
    print("═" * 60)

    for phase in data["phases"]:
        print(f"\n  PHASE {phase['phase_number']}: {phase['phase_name'].upper()}  [{phase['duration']}]")
        print(f"  Goal: {phase['objective']}")
        print("  " + "─" * 54)
        for s in phase["steps"]:
            checkbox = "☐"
            print(f"    {checkbox} Step {s['step']}: {s['title']}")
            print(f"         {s['description']}")

    print("\n" + "─" * 60)
    print("  💡  TIPS")
    for tip in data.get("tips", []):
        print(f"    • {tip}")

    print("\n  ⚠️   WATCH OUT")
    print(f"    {data.get('warning', '')}")
    print("═" * 60 + "\n")

# ── Save roadmap to a file ─────────────────────────────────────────────────────
def save_roadmap(data: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = data["goal"][:40].replace(" ", "_").replace("/", "-")
    filename = f"roadmap_{safe_name}_{timestamp}.json"
    output_path = Path(__file__).parent / "saved_roadmaps" / filename
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅  Roadmap saved to: saved_roadmaps/{filename}")

# ── Call Claude API ────────────────────────────────────────────────────────────
def generate_roadmap(goal: str, background: str, skill_instructions: str) -> dict:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    user_message = f"""My goal: {goal}

My background / experience level: {background if background.strip() else "Not provided"}

Please generate a complete roadmap following the SKILL.md instructions exactly.
Return ONLY valid JSON, no explanation, no markdown fences."""

    print("\n  ⏳  Generating your roadmap...\n")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=skill_instructions,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)

# ── Main flow ──────────────────────────────────────────────────────────────────
def main():
    print("\n" + "═" * 60)
    print("  🗺   ROADMAP GENERATOR  —  Powered by Claude + SKILL.md")
    print("═" * 60)

    skill_instructions = load_skill()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n❌  ANTHROPIC_API_KEY not set.")
        print("   Run:  export ANTHROPIC_API_KEY_set ur api here\n")
        sys.exit(1)

    # Get goal from user
    print("\n  What goal do you want to achieve?")
    print("  Examples:")
    print("    • Become a frontend developer in 6 months")
    print("    • Run my first 5K in 3 months")
    print("    • Switch careers from accounting to UX design\n")
    goal = input("  Your goal: ").strip()

    if not goal:
        print("❌  Please enter a goal.")
        sys.exit(1)

    # Optional background
    print("\n  Your experience level or background? (press Enter to skip)")
    print("  Example: 'Complete beginner' or 'I know basic Python'\n")
    background = input("  Background: ").strip()

    # Generate
    try:
        roadmap_data = generate_roadmap(goal, background, skill_instructions)
    except json.JSONDecodeError as e:
        print(f"\n❌  Could not parse Claude's response as JSON: {e}")
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"\n❌  API error: {e}")
        sys.exit(1)

    # Display
    display_roadmap(roadmap_data)

    # Save?
    save_choice = input("  Save this roadmap to a file? (y/n): ").strip().lower()
    if save_choice == "y":
        save_roadmap(roadmap_data)

    print("\n  Good luck! 🚀\n")

if __name__ == "__main__":
    main()