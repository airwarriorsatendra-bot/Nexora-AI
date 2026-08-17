from pathlib import Path

db = Path("storage/backlinks.db")

if db.exists():
    db.unlink()
    print("✅ backlinks.db deleted.")
else:
    print("Database not found.")