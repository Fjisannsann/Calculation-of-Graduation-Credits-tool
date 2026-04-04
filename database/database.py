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
CREATE TABLE IF NOT EXISTS subjects2 (
    category_big TEXT,
    category_mid TEXT,
    subject TEXT PRIMARY KEY,
    flag INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS groups (
    group_name TEXT,
    category_big TEXT,
    category_mid TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_big_category (
    big_category TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_groups (
    group_name TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_mid_category (
    category_mid TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_mid_category_flag (
    category_mid TEXT PRIMARY KEY,
    flag INTEGER,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_small_category (
    category_small TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_detail (
    category_detail TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requirements_subjects (
    subject TEXT PRIMARY KEY,
    required_credits INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS graduation_credits (
    credits_full INTEGER,
    required_credits INTEGER
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
insert_csv("subjects2", "database/csv/cs_subject2.csv")
insert_csv("groups", "database/csv/cs_group.csv")
insert_csv("requirements_big_category", "database/csv/requirements_big_category.csv")
insert_csv("requirements_groups", "database/csv/requirements_groups.csv")
insert_csv("requirements_mid_category", "database/csv/requirements_mid_category.csv")
insert_csv("requirements_subjects", "database/csv/requirements_subjects.csv")
insert_csv("requirements_mid_category_flag", "database/csv/requirements_mid_category_flag.csv")
insert_csv("requirements_small_category", "database/csv/requirements_small_category.csv")
insert_csv("requirements_detail", "database/csv/requirements_detail.csv")
insert_csv("graduation_credits", "database/csv/graduation_credits.csv")

conn.close()