import os
import subprocess
import re
from collections import defaultdict
from datetime import datetime, timedelta
from download_pdf import download_latest_pdf
from parse_pdf import parse_games

calendar_mapping = {"St-Aug": "Ref St-Aug", "Chauveau": "Ref Chauveau"}

print("Downloading PDFs from Gmail...")
pdf_files = download_latest_pdf()
if not pdf_files:
    print("No PDFs downloaded, exiting.")
    exit()
print(f"Downloaded {len(pdf_files)} PDF(s).")

all_games = []
for pdf_path in pdf_files:
    print(f"Parsing PDF: {pdf_path}")
    games = parse_games(pdf_path)
    if games:
        all_games.extend(games)
    else:
        print(f"WARNING: No games found in {pdf_path}")

if not all_games:
    print("ERROR: No games found in any PDFs, exiting.")
    exit()
print(f"Parsed {len(all_games)} games from PDFs.")

print("Creating events in Apple Calendar...")
grouped = defaultdict(lambda: defaultdict(list))
unmapped_locations = set()
skipped_games = 0

for game in all_games:
    surface_full = game["surface"]
    match = re.search(r"\((.*?)\)", surface_full)

    location = None
    if match:
        location_text = match.group(1).strip()
        if location_text:
            location_parts = location_text.split()
            location = location_parts[0] if location_parts else None

    cal_name = calendar_mapping.get(location)
    if not cal_name:
        if location:
            unmapped_locations.add(location)
        skipped_games += 1
        continue

    grouped[cal_name][game["date"]].append(
        {"start": game["time"], "surface": surface_full}
    )

total_events_created = 0
datetime_errors = 0
duplicates_skipped = 0
for cal_name, days in grouped.items():
    create_cal_script = f'''
    tell application "Calendar"
        set calendarExists to false
        try
            set testCal to calendar "{cal_name}"
            set calendarExists to true
        end try

        if not calendarExists then
            make new calendar with properties {{name:"{cal_name}"}}
        end if
    end tell
    '''

    try:
        subprocess.run(["osascript", "-e", create_cal_script], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create calendar '{cal_name}': {e.stderr if e.stderr else e}")
        continue

    events_created = 0
    for date_str, games_list in days.items():
        try:
            games_list.sort(key=lambda x: x["start"])
            start_time = games_list[0]["start"]

            try:
                start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
            except ValueError as e:
                print(f"Skipping event - invalid start datetime '{date_str} {start_time}': {e}")
                datetime_errors += 1
                continue

            try:
                end_time_dt = datetime.strptime(
                    f"{date_str} {games_list[-1]['start']}", "%Y-%m-%d %H:%M"
                ) + timedelta(minutes=50)
            except ValueError as e:
                print(f"Skipping event - invalid end datetime: {e}")
                datetime_errors += 1
                continue

            surface_counts = {}
            for g in games_list:
                surface_full = g["surface"]
                surface_name = re.sub(r"\s*\(.*?\)", "", surface_full).strip()
                surface_counts[surface_name] = surface_counts.get(surface_name, 0) + 1

            surface_details = [f"{surf}: {count} game{'s' if count > 1 else ''}"
                             for surf, count in sorted(surface_counts.items())]
            description = ", ".join(surface_details)
            event_name = f"{len(games_list)} games"

            start_date_str = start_dt.strftime("%B %d, %Y %I:%M:%S %p")
            end_date_str = end_time_dt.strftime("%B %d, %Y %I:%M:%S %p")
            description_escaped = description.replace('"', '\\"')
            event_name_escaped = event_name.replace('"', '\\"')

            # Check for duplicate events by checking events on the same day with same summary
            check_duplicate_script = f'''
            tell application "Calendar"
                tell calendar "{cal_name}"
                    set targetDate to date "{start_date_str}"
                    set theEvents to every event
                    set matchCount to 0
                    repeat with anEvent in theEvents
                        set eventStart to start date of anEvent
                        set eventSummary to summary of anEvent
                        if eventSummary is "{event_name_escaped}" then
                            if (eventStart as string) is (targetDate as string) then
                                set matchCount to matchCount + 1
                            end if
                        end if
                    end repeat
                    return matchCount
                end tell
            end tell
            '''

            try:
                result = subprocess.run(["osascript", "-e", check_duplicate_script], check=True, capture_output=True, text=True)
                duplicate_count = int(result.stdout.strip())

                if duplicate_count > 0:
                    print(f"Skipping duplicate event: '{event_name}' on {date_str} at {start_time}")
                    duplicates_skipped += 1
                    continue

            except (subprocess.CalledProcessError, ValueError) as e:
                print(f"Warning: Could not check for duplicates, proceeding with creation: {e}")

            create_event_script = f'''
            tell application "Calendar"
                tell calendar "{cal_name}"
                    make new event with properties {{summary:"{event_name}", start date:date "{start_date_str}", end date:date "{end_date_str}", description:"{description_escaped}"}}
                end tell
            end tell
            '''

            subprocess.run(["osascript", "-e", create_event_script], check=True, capture_output=True, text=True)
            events_created += 1

        except Exception as e:
            print(f"ERROR: Failed to create event for {cal_name} on {date_str}: {e}")
            continue

    print(f"Created {events_created} event(s) in calendar '{cal_name}'")
    total_events_created += events_created

print("\nCleaning up temporary files...")
for pdf_file in pdf_files:
    try:
        os.remove(pdf_file)
        print(f"Deleted {pdf_file}")
    except Exception as e:
        print(f"Error deleting {pdf_file}: {e}")

print("\nSUMMARY")
print(f"Total games parsed: {len(all_games)}")
print(f"Total events created: {total_events_created}")
print(f"Games skipped: {skipped_games}")
if duplicates_skipped > 0:
    print(f"Duplicate events skipped: {duplicates_skipped}")
if datetime_errors > 0:
    print(f"Datetime parsing errors: {datetime_errors}")

if unmapped_locations:
    print(f"\nWARNING: {skipped_games} game(s) skipped due to unmapped locations:")
    print(f"  Locations: {', '.join(sorted(unmapped_locations))}")
    print(f"  Add these to calendar_mapping in main.py if needed.")

if datetime_errors > 0:
    print(f"\nWARNING: {datetime_errors} event(s) skipped due to datetime parsing errors.")
    print(f"  The PDF date/time format might have changed.")

if skipped_games > len(all_games) * 0.3:
    print(f"\nWARNING: More than 30% of games were skipped!")
    print(f"  Check if calendar_mapping is correct.")

elif total_events_created > 0:
    print(f"\nSuccess! All events added to Apple Calendar.")
