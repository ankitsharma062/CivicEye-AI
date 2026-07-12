import sqlite3

conn = sqlite3.connect("database/civiceye.db")

cursor = conn.cursor()

columns = [

    "ai_prediction TEXT",

    "ai_confidence REAL",

    "verification_status TEXT",

    "user_category TEXT"

]

for column in columns:

    try:

        cursor.execute(
            f"ALTER TABLE reports ADD COLUMN {column}"
        )

        print(f"{column} added")

    except Exception as e:

        print(f"{column} already exists or error:", e)

conn.commit()
conn.close()

print("Database updated successfully!")