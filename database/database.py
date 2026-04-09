import sqlite3
import csv

conn = sqlite3.connect("graduation.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    category_big TEXT,
    category_mid TEXT,
    category_small TEXT,
    category_detail TEXT,
    subject TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subject_flags (
    subject TEXT,
    flag INTEGER,
    PRIMARY KEY (subject),
    FOREIGN KEY (subject) REFERENCES subjects(subject)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirement_groups (
    id INTEGER,
    type TEXT,
    name TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES graduation_credits(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS graduation_credits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    name TEXT,
    required_credits INTEGER,
    flag INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS types (
    type TEXT PRIMARY KEY,
    type_name TEXT,
    FOREIGN KEY (type) REFERENCES graduation_credits(type)
)
""")
conn.commit()

def insert_csv(table_name, file_path):
    with open(file_path, encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)# ヘッダーをスキップ
        placeholders = ', '.join(['?'] * len(header))
        query = f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})"
        for row in reader:
            if not any(row):
                continue
            cursor.execute(query, row)
    conn.commit()

insert_csv("subjects", "database/csv/cs_subject.csv")
insert_csv("subject_flags", "database/csv/subject_flags.csv")
insert_csv("requirement_groups", "database/csv/requirement_groups.csv")
insert_csv("graduation_credits", "database/csv/graduation_credits.csv")

conn.close()