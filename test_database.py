"""Manual database inspection script; safe to import during test discovery."""

import sqlite3


def main() -> None:
    with sqlite3.connect("storage/backlinks.db") as connection:
        rows = connection.execute(
            """
            SELECT title, priority_score
            FROM prospects
            ORDER BY priority_score DESC
            LIMIT 10
            """
        ).fetchall()
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
