import unicodedata
import pdfplumber

HEADER_LABELS = ("Jour", "Date", "Heure", "Surface", "Calibre", "Arbitre")


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


def _cluster_words_into_lines(words, tol=3):
    """Group words sharing (approximately) the same vertical position into lines."""
    lines = []
    for w in sorted(words, key=lambda w: w["top"]):
        for line in lines:
            if abs(line["top"] - w["top"]) <= tol:
                line["words"].append(w)
                break
        else:
            lines.append({"top": w["top"], "words": [w]})
    return lines


def reconstruct_rows_from_words(page):
    """Rebuild table rows from word x-positions for borderless PDFs.

    pdfplumber detects tables from ruling lines, so a schedule whose table has
    no borders yields zero tables. Here we anchor each column to the x position
    of its header label, then bucket every word on a line into its column. The
    result mimics the shape extract_tables() produces, so parse_row handles it
    unchanged.
    """
    words = page.extract_words()
    if not words:
        return []

    lines = _cluster_words_into_lines(words)

    # Locate the header line and the left x of each column.
    col_x = None
    header_top = None
    for line in lines:
        texts = {w["text"] for w in line["words"]}
        if sum(label in texts for label in HEADER_LABELS) >= 4:
            header_top = line["top"]
            col_x = [
                next((w["x0"] for w in line["words"] if w["text"] == label), None)
                for label in HEADER_LABELS
            ]
            break

    if not col_x or any(x is None for x in col_x):
        return []

    margin = 8
    bounds = [x - margin for x in col_x]

    rows = []
    for line in lines:
        if line["top"] <= header_top:
            continue
        cols = ["" for _ in HEADER_LABELS]
        for w in sorted(line["words"], key=lambda w: w["x0"]):
            ci = 0
            for i in range(len(col_x)):
                if w["x0"] >= bounds[i]:
                    ci = i
            cols[ci] = (cols[ci] + " " + w["text"]).strip()
        if any(cols):
            rows.append(cols)
    return rows


def parse_games(pdf_path):
    games = []
    skipped_rows = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            rows = [row for table in page.extract_tables() for row in table]
            if not rows:
                # Borderless PDFs expose no ruling lines, so pdfplumber finds no
                # tables. Fall back to rebuilding rows from word positions.
                rows = reconstruct_rows_from_words(page)
            for row in rows:
                try:
                    game = parse_row(row)
                    if game:
                        games.append(game)
                    else:
                        skipped_rows += 1
                except (IndexError, AttributeError):
                    skipped_rows += 1

    print(f"Found {len(games)} games in the PDF")
    if skipped_rows > 0:
        print(f"Skipped {skipped_rows} rows (headers or invalid data)")

    total_rows = len(games) + skipped_rows
    if total_rows > 0 and skipped_rows > total_rows * 0.5:
        skipped_pct = f"{skipped_rows}/{total_rows}"
        print(f"WARNING: More than 50% of rows were skipped ({skipped_pct})")
        print("  The PDF format might have changed.")

    return games
