import random
import sqlite3

DB = "storage/backlinks.db"

categories = [
    "SEO",
    "Technology",
    "Marketing",
    "Business",
    "AI",
    "Finance",
    "Health",
    "Education",
    "Travel",
    "Fashion",
]

conn = sqlite3.connect(DB)
cur = conn.cursor()

for i in range(1, 101):

    category = random.choice(categories)
    score = random.randint(40, 100)

    cur.execute(
        """
        INSERT OR IGNORE INTO prospects
        (
            title,
            url,
            description,
            category,
            emails,
            phone_numbers,
            contact_page,
            about_page,
            write_for_us,
            social_links,
            priority_score,
            status,
            notes
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"Sample Website {i}",
            f"https://sample{i}.com",
            f"Sample {category} website for testing Nexora AI.",
            category,
            f"editor{ i }@sample{i}.com",
            "+91-9000000000",
            f"https://sample{i}.com/contact",
            f"https://sample{i}.com/about",
            f"https://sample{i}.com/write-for-us",
            f"https://twitter.com/sample{i}",
            score,
            "New",
            "Seed data",
        ),
    )

conn.commit()
conn.close()

print("✅ 100 sample prospects inserted.")