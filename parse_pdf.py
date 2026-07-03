import re
import unicodedata
import pdfplumber

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TIME_RE = re.compile(r"\d{1,2}:\d{2}")


def normalize_text(text):
    """Remove accents and convert to lowercase for matching."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(
        char for char in nfd if unicodedata.category(char) != 'Mn'
    ).lower()


def determine_location(surface_str):
    """Determine location from first letter of surface name."""
    if "(" in surface_str:
        return surface_str

    if not surface_str:
        return surface_str

    first_letter = surface_str[0].upper()
    location = None

    # St-Aug: G, S, K
    if first_letter in ['G', 'S', 'K']:
        location = "St-Aug"
    # Chauveau: O, V, T
    elif first_letter in ['O', 'V', 'T']:
        location = "Chauveau"

    if location:
        return f"{surface_str} ({location})"
    return surface_str


def parse_row(row):
    """Parse a single table row into a game dict."""
    if not any(row) or len(row) < 5:
        return None

    first_col = row[0].strip() if row[0] else ""
    # Only skip actual header rows, not rows with empty first column
    if first_col and first_col.lower() in ["jour", "day", "date"]:
        return None

    date_str = row[1].strip() if row[1] else ""
    if " " in date_str:
        date_str = date_str.split()[0]

    time_str = row[2].strip() if row[2] else ""
    if time_str.count(":") == 2:
        time_str = ":".join(time_str.split(":")[:2])

    surface_str = row[3].strip() if row[3] else ""
    calibre_str = row[4].strip() if row[4] else ""
    surface_str = determine_location(surface_str)

    # Handle 5, 6, and 8-column formats
    if len(row) >= 8:
        # Old format: [Day, Date, Time, Surface, Calibre, Visitor, Local, Referee]
        game = {
            "day": row[0].strip() if row[0] else "",
            "date": date_str,
            "time": time_str,
            "surface": surface_str,
            "calibre": calibre_str,
            "visitor": row[5].strip() if row[5] else "",
            "local": row[6].strip() if row[6] else "",
            "referee": row[7].strip() if row[7] else "",
        }
    elif len(row) >= 6:
        # Format: [Day, Date, Time, Surface, Calibre, Referee]
        game = {
            "day": row[0].strip() if row[0] else "",
            "date": date_str,
            "time": time_str,
            "surface": surface_str,
            "calibre": calibre_str,
            "visitor": "",
            "local": "",
            "referee": row[5].strip() if row[5] else "",
        }
    else:
        # Minimal format: [Day, Date, Time, Surface, Calibre]
        game = {
            "day": row[0].strip() if row[0] else "",
            "date": date_str,
            "time": time_str,
            "surface": surface_str,
            "calibre": calibre_str,
            "visitor": "",
            "local": "",
            "referee": "",
        }

    if game["date"] and game["time"]:
        return game
    return None


def _cluster_chars_into_lines(chars, tol=3):
    """Group chars sharing (approximately) the same vertical position into lines.

    Iterating page.chars in order preserves PDF content-stream order within each
    line, which is what lets us recover overlapping columns (see _split_runs).
    """
    lines = []
    for c in chars:
        for line in lines:
            if abs(line["top"] - c["top"]) <= tol:
                line["chars"].append(c)
                break
        else:
            lines.append({"top": c["top"], "chars": [c]})
    lines.sort(key=lambda line: line["top"])
    return lines


def _split_runs(chars):
    """Split a line's chars (in stream order) into runs at backward x jumps.

    In this borderless schedule the left columns (Jour/Date/Heure/Surface) and
    the right columns (Calibre/Visiteur/Local/Arbitre) are emitted as two
    separate text runs that overlap horizontally. extract_words() sorts by x and
    interleaves them into garbage (e.g. "(St-AuFg5"). Because each run is emitted
    left-to-right contiguously in the content stream, a char whose x jumps back
    relative to the previous char marks the start of a new run, letting us keep
    each run's text intact.
    """
    runs = []
    cur = []
    prev_x = None
    for c in chars:
        if prev_x is not None and c["x0"] < prev_x - 3:
            runs.append(cur)
            cur = []
        cur.append(c)
        prev_x = c["x0"]
    if cur:
        runs.append(cur)
    return ["".join(c["text"] for c in run).strip() for run in runs]


def reconstruct_rows_from_words(page):
    """Rebuild table rows for borderless PDFs from char positions.

    pdfplumber detects tables from ruling lines, so a schedule whose table has
    no borders yields zero tables. We rebuild each row by clustering chars into
    lines, splitting overlapping column runs apart, then pulling the date, time,
    and surface out of the left run and the calibre out of the right run. The
    result mimics the shape extract_tables() produces, so parse_row handles it
    unchanged.
    """
    if not page.chars:
        return []

    rows = []
    for line in _cluster_chars_into_lines(page.chars):
        runs = _split_runs(line["chars"])
        if not runs:
            continue

        left = runs[0]
        date_match = DATE_RE.search(left)
        if not date_match:
            # Header rows and the wrapped second line of a time cell have no date.
            continue

        date = date_match.group(0)
        day = left[: date_match.start()].strip()
        after_date = left[date_match.end():]

        time_match = TIME_RE.search(after_date)
        if time_match:
            time = time_match.group(0)
            surface = after_date[time_match.end():].strip()
        else:
            time = ""
            surface = after_date.strip()

        calibre = ""
        if len(runs) > 1:
            calibre_parts = runs[1].split()
            if calibre_parts:
                calibre = calibre_parts[0]

        rows.append([day, date, time, surface, calibre])
    return rows


def _rows_to_games(rows):
    """Parse rows into games, returning (games, skipped_row_count)."""
    games = []
    skipped = 0
    for row in rows:
        try:
            game = parse_row(row)
            if game:
                games.append(game)
            else:
                skipped += 1
        except (IndexError, AttributeError):
            skipped += 1
    return games, skipped


def _located_count(games):
    """Count games whose surface carries an intact "(...)" location tag.

    pdfplumber's table/word extraction sorts chars by x, which interleaves
    overlapping column text and breaks the location parenthetical. A higher
    count means the extraction kept rows intact, so we use it to pick the better
    of the two extraction strategies per page.
    """
    return sum(1 for g in games if "(" in g["surface"] and ")" in g["surface"])


def parse_games(pdf_path):
    games = []
    skipped_rows = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Two strategies. extract_tables() relies on ruling lines; char
            # reconstruction rebuilds rows from content-stream order and survives
            # overlapping columns that interleave under x-sorted extraction. Keep
            # whichever recovers more rows with their location tag intact.
            table_rows = [row for table in page.extract_tables() for row in table]
            char_rows = reconstruct_rows_from_words(page)

            table_games, table_skipped = _rows_to_games(table_rows)
            char_games, char_skipped = _rows_to_games(char_rows)

            # Prefer table extraction on ties: when a real table exists its
            # columns are already clean, while char reconstruction crams
            # calibre and referee into the surface cell.
            table_score = (_located_count(table_games), len(table_games))
            char_score = (_located_count(char_games), len(char_games))
            if table_score >= char_score:
                page_games, page_skipped = table_games, table_skipped
            else:
                page_games, page_skipped = char_games, char_skipped

            games.extend(page_games)
            skipped_rows += page_skipped

    print(f"Found {len(games)} games in the PDF")
    if skipped_rows > 0:
        print(f"Skipped {skipped_rows} rows (headers or invalid data)")

    total_rows = len(games) + skipped_rows
    if total_rows > 0 and skipped_rows > total_rows * 0.5:
        skipped_pct = f"{skipped_rows}/{total_rows}"
        print(f"WARNING: More than 50% of rows were skipped ({skipped_pct})")
        print("  The PDF format might have changed.")

    return games
