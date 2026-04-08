import sqlite3
import csv
from collections import defaultdict

# =========================
# ① 履修データ読み込み
# =========================
def load_taken_subjects(file_path):
    subjects = []

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # 成績0は未取得扱い
            if row["grade"] == "" or int(row["grade"]) == 0:
                continue

            subjects.append({
                "subject": row["subject"],
                "credits": float(row["credits"])
            })

    return subjects


# =========================
# ② 科目 → カテゴリ取得
# =========================
def get_subject_info(cursor, subject):
    cursor.execute("""
        SELECT
            category_big,
            category_mid,
            category_small,
            category_detail
        FROM subjects
        WHERE subject=?
    """, (subject,))

    return cursor.fetchone()


# =========================
# ③ 単位集計
# =========================
def calculate_credits(cursor, taken_subjects):

    credits = {
        "big": defaultdict(float),
        "mid": defaultdict(float),
        "small": defaultdict(float),
        "detail": defaultdict(float),
        "subject": defaultdict(float)
    }

    for item in taken_subjects:

        subject = item["subject"]
        credit = item["credits"]

        info = get_subject_info(cursor, subject)

        if info is None:
            # DBに存在しない科目はスキップ
            continue

        big, mid, small, detail = info

        if big:
            credits["big"][big] += credit
        if mid:
            credits["mid"][mid] += credit
        if small:
            credits["small"][small] += credit
        if detail:
            credits["detail"][detail] += credit

        credits["subject"][subject] += credit

    return credits


# =========================
# ④ グループ単位計算
# =========================
def calculate_group_credits(cursor, credits):

    group_totals = defaultdict(float)

    cursor.execute("""
        SELECT group_name, type, name
        FROM groups
    """)

    rows = cursor.fetchall()

    for group_name, type_, name in rows:
        group_totals[group_name] += credits[type_].get(name, 0)

    return group_totals


# =========================
# ⑤ 卒業要件チェック
# =========================
def check_requirements(cursor, credits, group_totals):

    results = []

    cursor.execute("""
        SELECT
            type,
            name,
            required_credits,
            flag
        FROM graduation_credits
    """)

    rules = cursor.fetchall()

    for type_, name, required, flag in rules:

        # groupの場合
        if type_ == "group":
            current = group_totals.get(name, 0)
        else:
            current = credits[type_].get(name, 0)

        shortage = required - current

        results.append({
            "type": type_,
            "name": name,
            "current": current,
            "required": required,
            "shortage": shortage
        })

    return results


# =========================
# ⑥ 結果表示
# =========================
def print_results(results):

    print("=== 卒業判定結果 ===\n")

    for r in results:

        name = r["name"]
        current = r["current"]
        required = r["required"]
        shortage = r["shortage"]

        if shortage > 0:
            print(f"{name}: 不足 {shortage:.1f} 単位 (現在 {current} / 必要 {required})")
        else:
            print(f"{name}: OK (現在 {current} / 必要 {required})")


# =========================
# main
# =========================
def main():

    # DB接続
    conn = sqlite3.connect("graduation.db")
    cursor = conn.cursor()

    # CSV（履修データ）
    taken_subjects = load_taken_subjects("output/haru3.csv")

    # 単位集計
    credits = calculate_credits(cursor, taken_subjects)

    # グループ計算
    group_totals = calculate_group_credits(cursor, credits)

    # 判定
    results = check_requirements(cursor, credits, group_totals)

    # 出力
    print_results(results)

    conn.close()


if __name__ == "__main__":
    main()