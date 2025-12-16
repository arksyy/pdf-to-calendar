import pdfplumber


def parse_games(pdf_path):
    games = []
    skipped_rows = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not any(row):
                        continue

                    if len(row) < 8:
                        skipped_rows += 1
                        continue

                    try:
                        first_col = row[0].strip() if row[0] else ""
                        if not first_col or first_col.lower() in ["jour", "day", "date"]:
                            continue

                        game = {
                            "day": row[0].strip() if row[0] else "",
                            "date": row[1].strip() if row[1] else "",
                            "time": row[2].strip() if row[2] else "",
                            "surface": row[3].strip() if row[3] else "",
                            "calibre": row[4].strip() if row[4] else "",
                            "visitor": row[5].strip() if row[5] else "",
                            "local": row[6].strip() if row[6] else "",
                            "referee": row[7].strip() if row[7] else "",
                        }

                        if game["date"] and game["time"]:
                            games.append(game)
                        else:
                            skipped_rows += 1

                    except (IndexError, AttributeError):
                        skipped_rows += 1
                        continue

    print(f"Found {len(games)} games in the PDF")
    if skipped_rows > 0:
        print(f"Skipped {skipped_rows} rows (headers or invalid data)")

    total_rows = len(games) + skipped_rows
    if total_rows > 0 and skipped_rows > total_rows * 0.5:
        print(f"WARNING: More than 50% of rows were skipped ({skipped_rows}/{total_rows})")
        print(f"  The PDF format might have changed.")

    return games
