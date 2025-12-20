import unicodedata
import pdfplumber


def normalize_text(text):
    """Remove accents and convert to lowercase for matching."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(
        char for char in nfd if unicodedata.category(char) != 'Mn'
    ).lower()


def determine_location(surface_str, calibre_str):
    """Determine location from surface name or calibre text."""
    if "(" in surface_str:
        return surface_str

    surface_normalized = normalize_text(surface_str)
    location = None

    st_aug_names = ["giguer", "salvatore", "k2d"]
    chauveau_names = ["oeufrier", "videotron", "thai"]

    if any(name in surface_normalized for name in st_aug_names):
        location = "St-Aug"
    elif any(name in surface_normalized for name in chauveau_names):
        location = "Chauveau"
    elif calibre_str:
        if "Chauveau" in calibre_str:
            location = "Chauveau"
        elif "Aug" in calibre_str:
            location = "St-Aug"

    if location:
        return f"{surface_str} ({location})"
    return surface_str


def parse_row(row):
    """Parse a single table row into a game dict."""
    if not any(row) or len(row) < 8:
        return None

    first_col = row[0].strip() if row[0] else ""
    if not first_col or first_col.lower() in ["jour", "day", "date"]:
        return None

    date_str = row[1].strip() if row[1] else ""
    if " " in date_str:
        date_str = date_str.split()[0]

    time_str = row[2].strip() if row[2] else ""
    if time_str.count(":") == 2:
        time_str = ":".join(time_str.split(":")[:2])

    surface_str = row[3].strip() if row[3] else ""
    calibre_str = row[4].strip() if row[4] else ""
    surface_str = determine_location(surface_str, calibre_str)

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

    if game["date"] and game["time"]:
        return game
    return None


def parse_games(pdf_path):
    games = []
    skipped_rows = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
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
