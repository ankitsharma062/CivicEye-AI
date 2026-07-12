import sqlite3

conn = sqlite3.connect("database/civiceye.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT,
    issue TEXT,
    location TEXT,
    description TEXT,
    status TEXT,
    date TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully!")