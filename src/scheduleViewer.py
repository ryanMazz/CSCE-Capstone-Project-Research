
from dataclasses import field
import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCHEDULE_DIR = Path(__file__).resolve().parent.parent / "savedSchedules"
DAY_NAMES = {
    1: "Sunday",
    2: "Monday",
    3: "Tuesday",
    4: "Wednesday",
    5: "Thursday",
    6: "Friday",
    7: "Saturday",
}
TIME_DISPLAY = "%I:%M %p" #Ensures 12 hour time
WIDTH = 60 #TODO: Change to window width


#date/time handling
def parse_time(value):
    text = str(value).strip()
    try:
        return datetime.strptime(text.upper(), TIME_DISPLAY)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None

def format_time(value):
    parsed = parse_time(value)
    return parsed.strftime(TIME_DISPLAY) if parsed else str(value)

def time_sort_key(value):
    parsed = parse_time(value)
    return parsed.hour * 60 + parsed.minute if parsed else float("inf")

def format_date(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if (parsed.hour, parsed.minute, parsed.second) == (0, 0, 0):
        return parsed.strftime("%B %d, %Y")
    return parsed.strftime("%B %d, %Y " + TIME_DISPLAY)


#display printing
def entries_by_day(fields):
    days = {day: [] for day in DAY_NAMES}
    for field in fields:
        for slot in field.get("timeSlots", []):
            for day in slot.get("days", []):
                if day in days:
                    days[day].append((field, slot))
    for entries in days.values():
        entries.sort(key=lambda pair: time_sort_key(pair[1].get("startTime", "")))
    return days

def print_field(field, slot):
    print(f"{field.get('name', '')} - {field.get('type', '')} ({field.get('origin', '')})")
    print(
        f"{slot.get('location', '')} : "
        f"{format_time(slot.get('startTime', ''))} - {format_time(slot.get('endTime', ''))}"
    )

    #instructor and credit count are optional. prints only if present
    details = []
    if field.get("instructor"):
        details.append(str(field["instructor"]))
    if field.get("credits") is not None:
        details.append(f"{field['credits']} credits")
    if details:
        print(", ".join(details))

    if field.get("notes"):
        print(field["notes"])

def display_schedule(schedule):
    print("=" * WIDTH)
    print(schedule.get("name", "Untitled schedule"))
    print(f"Author: {schedule.get('author', 'Unknown')}")
    print(f"Last modified: {format_date(schedule.get('lastModifiedDate', 'Unknown'))}")
    print("=" * WIDTH)
    if schedule.get("notes"):
        print(schedule["notes"])

    days = entries_by_day(schedule.get("fields", []))
    for day, day_name in DAY_NAMES.items():
        print("\n")
        print(day_name)
        print("-" * WIDTH)
        if not days[day]:
            print("(nothing scheduled)")
            continue
        for i, (field, slot) in enumerate(days[day]):
            if i:
                print()
            print_field(field, slot)


#menu actions
def ask(label, required=True):
    while True:
        answer = input(f"{label}: ").strip()
        if answer or not required:
            return answer
        print("  This value is required.")

def ask_time(label):
    while True:
        parsed = parse_time(ask(label))
        if parsed:
            return parsed.strftime(TIME_DISPLAY)
        print("  Enter a time such as 9:40 AM or 13:10.")

def ask_days():
    while True:
        parts = re.split(r"[,\s]+", ask("Days (1=Sunday ... 7=Saturday, e.g. 2,4,6)"))
        if all(p.isdigit() and 1 <= int(p) <= 7 for p in parts):
            return sorted({int(p) for p in parts})
        print("  Enter numbers from 1 to 7 separated by commas.")

def add_field(schedule):
    print("Add a custom field. Optional items can be left blank")
    field = {
        "name": ask("Name"),
        "type": ask("Type"),
        "origin": "created",
        "notes": ask("Notes (optional)", required=False),
    }
    instructor = ask("Instructor (optional)", required=False)
    if instructor:
        field["instructor"] = instructor
    while True:
        credits = ask("Credits (optional)", required=False)
        if not credits:
            break
        if credits.isdigit():
            field["credits"] = int(credits)
            break
        print("  Enter a whole number, or leave blank.")

    field["timeSlots"] = []
    while True:
        print(f"Time slot {len(field['timeSlots']) + 1}")
        field["timeSlots"].append({
            "days": ask_days(),
            "startTime": ask_time("Start time"),
            "endTime": ask_time("End time"),
            "location": ask("Location"),
        })
        if ask("Add another time slot? (y/n)", required=False).lower() != "y":
            break

    schedule.setdefault("fields", []).append(field)
    return f"Added \"{field['name']}\"."

def remove_field(schedule):
    fields = schedule.get("fields", [])
    if not fields:
        return ("There are no fields to remove.")
    print("Remove a field")
    for i, field in enumerate(fields, start=1):
        print(f"  {i}. {field.get('name', '')} - {field.get('type', '')}")
    choice = ask("Number to remove (blank to cancel)", required=False)
    if not choice:
        return None
    if not choice.isdigit() or not 1 <= int(choice) <= len(fields):
        return "Invalid selection; nothing removed."
    removed = fields.pop(int(choice) - 1)
    return f"Removed \"{removed.get('name', '')}\"."

def switch_schedule(schedule):
    files = sorted(SCHEDULE_DIR.glob("*.json"))
    print("Saved schedules:")
    for i, path in enumerate(files, start=1):
        print(f"  {i}. {path.name}")
    print("Opening a schedule discards any changes made to the current one.")
    choice = ask("Number to open (blank to cancel)", required=False)
    if not choice:
        return None
    if not choice.isdigit() or not 1 <= int(choice) <= len(files):
        return "Invalid selection; kept the current schedule."
    path = files[int(choice) - 1]
    try:
        loaded = load_schedule(path)
    except (OSError, json.JSONDecodeError) as err:
        return f"Could not open {path.name}: {err}"
    if not isinstance(loaded, dict):
        return f"{path.name} is not a schedule file; kept the current schedule."
    schedule.clear()
    schedule.update(loaded)
    return f"Opened {path.name}."

def edit_details(schedule):
    print("Edit schedule details (leave blank to keep the current value)")
    changed = False
    for key, label in (("name", "Name"), ("author", "Author"), ("notes", "Notes")):
        current = schedule.get(key, "")
        hint = ", - to clear" if key == "notes" else ""
        required = key != "notes" and not current
        answer = ask(f"{label} [{current}{hint}]", required=required)
        if not answer:
            continue
        new_value = "" if key == "notes" and answer == "-" else answer
        if new_value != current:
            schedule[key] = new_value
            changed = True

    if changed:
        schedule["lastModifiedDate"] = datetime.now().isoformat(timespec="seconds")
        return "Details updated."
    return "No changes made."


#saving
def format_text(text):
    return re.sub(r"[\W_]+", "-", str(text).lower()).strip("-")

def schedule_filename(schedule):
    name = format_text(schedule.get("name", "")) or "untitled"
    author = format_text(schedule.get("author", "")) or "unknown"
    return f"{name}_{author}.json"

def save_schedule(schedule):
    path = SCHEDULE_DIR / schedule_filename(schedule)
    if path.exists():
        answer = ask(f"\n{path.name} already exists. Overwrite it? (y/n)", required=False)
        if answer.lower() != "y":
            return "Save cancelled."

    previous_date = schedule.get("lastModifiedDate")
    schedule["lastModifiedDate"] = datetime.now().isoformat(timespec="seconds")
    try:
        SCHEDULE_DIR.mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as err:
        schedule["lastModifiedDate"] = previous_date
        return f"Could not save {path.name}: {err}"
    return f"Saved to {path.name}."


#menu & main
MENU_LIST = [
    ("View or switch schedule", switch_schedule),
    ("Add a field", add_field),
    ("Remove a field", remove_field),
    ("Edit schedule details", edit_details),
    ("Save schedule", save_schedule),
    ("Quit", None),
]

def menu_loop(schedule, status=None):
    status = None
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        display_schedule(schedule)
        print("\n")
        print("=" * WIDTH)
        print("Enter a command:")
        if status:
            print(status)
            print("-" * WIDTH)
        for i, (label, _) in enumerate(MENU_LIST, start=1):
            print(f"{i}. {label}")
        choice = input("\n> ").strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(MENU_LIST):
            status = f"Enter a number from 1 to {len(MENU_LIST)}."
            continue
        os.system('cls' if os.name == 'nt' else 'clear')
        action = MENU_LIST[int(choice) - 1][1]
        if action is None:
            break
        status = action(schedule)

def load_schedule(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def choose_file_init():
    if not SCHEDULE_DIR.is_dir():
        sys.exit(f"Dir not found: {SCHEDULE_DIR}")

    if len(sys.argv) > 1:
        name = sys.argv[1]
        path = SCHEDULE_DIR / (name if name.endswith(".json") else name + ".json")
        if not path.is_file():
            sys.exit(f"File not found: {path}")
        return path

    files = sorted(SCHEDULE_DIR.glob("*.json"))
    if not files:
        sys.exit(f"No valid files found in {SCHEDULE_DIR}")
    if len(files) == 1:
        return files[0]

    print("Available schedules:")
    for i, path in enumerate(files, start=1):
        print(f"  {i}. {path.name}")
    choice = input("Enter number to open or blank to return.\n> ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(files):
        sys.exit("Invalid selection.")
    return files[int(choice) - 1]

def blank_schedule(): #
    return {
        "name": "",
        "author": "",
        "lastModifiedDate": datetime.now().isoformat(timespec="seconds"),
        "notes": "",
        "fields": [],
    }

def runViewer(new=False):
    status = None
    try:
        if new:
            schedule = blank_schedule()
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Create a new schedule")
            edit_details(schedule)
            status = "New schedule created."
        else:
            path = choose_file_init()
            try:
                schedule = load_schedule(path)
            except json.JSONDecodeError as err:
                sys.exit(f"{path.name} is not valid JSON: {err}")

        menu_loop(schedule, status)
    except (EOFError, KeyboardInterrupt):
        print()