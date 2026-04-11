import argparse
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path


def load_taken_subjects(file_path):
    subjects = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            grade_str = (row.get("grade") or "").strip()
            if grade_str == "":
                continue

            grade = int(float(grade_str))
            # 0/1 は落単扱いで単位に含めない
            if grade <= 1:
                continue

            row["credits"] = float(row["credits"])
            subjects.append(row)
    return subjects


def load_type_map(cursor):
    cursor.execute("SELECT type, type_name FROM types")
    return {type_: type_name for type_, type_name in cursor.fetchall()}


def load_subject_flag_map(cursor):
    cursor.execute("SELECT subject, flag FROM subject_flags")
    return {subject: int(flag) for subject, flag in cursor.fetchall()}


def load_subject_category_map(cursor):
    cursor.execute(
        """
        SELECT
            subject,
            category_big,
            category_mid,
            category_small,
            category_detail
        FROM subjects
        """
    )
    return {
        subject: {
            "category_big": (big or "").strip(),
            "category_mid": (mid or "").strip(),
            "category_small": (small or "").strip(),
            "category_detail": (detail or "").strip(),
        }
        for subject, big, mid, small, detail in cursor.fetchall()
    }


def create_credit_bucket():
    return {
        "big": defaultdict(float),
        "mid": defaultdict(float),
        "small": defaultdict(float),
        "detail": defaultdict(float),
        "subject": defaultdict(float),
        "all": 0.0,
    }


def resolve_row_attribute(row, type_name, subject_category_map):
    subject = (row.get("subject") or "").strip()
    subject_categories = subject_category_map.get(subject, {})

    if type_name == "all":
        return None
    if type_name == "category_subject":
        return subject
    if type_name == "category_small":
        # output/*3.csv に category_small がないため subjects で補完
        return (
            row.get("category_small")
            or row.get("3rd")
            or subject_categories.get("category_small")
            or ""
        ).strip()
    if type_name == "category_detail":
        # output/*3.csv に detail 列がない場合は subjects.category_detail を補完利用
        return (
            row.get("category_detail")
            or row.get("3rd")
            or subject_categories.get("category_detail")
            or ""
        ).strip()
    return ((row.get(type_name) or subject_categories.get(type_name) or "")).strip()


def calculate_credits(taken_subjects, type_map, subject_flag_map, subject_category_map):
    credits = create_credit_bucket()
    credits_by_flag = defaultdict(create_credit_bucket)

    for item in taken_subjects:
        credit = item["credits"]

        credits["all"] += credit
        for type_, type_name in type_map.items():
            if type_ in ("all", "group"):
                continue
            key = resolve_row_attribute(item, type_name, subject_category_map)
            if key:
                credits[type_][key] += credit

        flag = subject_flag_map.get((item.get("subject") or "").strip())
        if flag is not None:
            flagged = credits_by_flag[flag]
            flagged["all"] += credit
            for type_, type_name in type_map.items():
                if type_ in ("all", "group"):
                    continue
                key = resolve_row_attribute(item, type_name, subject_category_map)
                if key:
                    flagged[type_][key] += credit

    return credits, credits_by_flag


def calculate_group_credits(cursor, credits):
    group_totals = defaultdict(float)
    cursor.execute(
        """
        SELECT DISTINCT id, type, name
        FROM requirement_groups
        """
    )
    for req_id, type_, name in cursor.fetchall():
        if type_ == "all":
            group_totals[req_id] += credits["all"]
        elif type_ in ("big", "mid", "small", "detail", "subject"):
            group_totals[req_id] += credits[type_].get(name, 0.0)
    return group_totals


def check_requirements(cursor, credits, credits_by_flag, group_totals):
    results = []
    cursor.execute(
        """
        SELECT id, type, name, required_credits, flag
        FROM graduation_credits
        ORDER BY id
        """
    )

    for req_id, type_, name, required, flag in cursor.fetchall():
        required_value = float(required)
        flag_value = int(flag) if flag not in (None, "") else None

        if type_ == "group":
            current = group_totals.get(req_id, 0.0)
        elif type_ == "all":
            current = credits["all"]
        elif flag_value is not None:
            current = credits_by_flag[flag_value][type_].get(name, 0.0)
        else:
            current = credits[type_].get(name, 0.0)

        shortage = required_value - current
        results.append(
            {
                "id": req_id,
                "type": type_,
                "name": name,
                "current": current,
                "required": required_value,
                "shortage": shortage,
                "is_ok": shortage <= 0,
                "flag": flag_value,
            }
        )
    return results


def print_results(results):
    print("=== 卒業判定結果 ===\n")
    for r in results:
        label = r["name"]
        if r["flag"] is not None:
            label = f"{label} (flag={r['flag']})"

        if r["is_ok"]:
            print(f"{label}: OK (現在 {r['current']:.1f} / 必要 {r['required']:.1f})")
        else:
            print(
                f"{label}: 不足 {r['shortage']:.1f} 単位 "
                f"(現在 {r['current']:.1f} / 必要 {r['required']:.1f})"
            )

    all_ok = all(r["is_ok"] for r in results)
    print("\n総合判定: " + ("卒業要件を満たしています" if all_ok else "卒業要件を満たしていません"))


def parse_args():
    parser = argparse.ArgumentParser(description="履修CSVから卒業要件を判定します。")
    parser.add_argument(
        "--csv",
        default="output/3.csv",
        help="判定対象の履修CSVファイル（デフォルト: output/3.csv）",
    )
    parser.add_argument(
        "--db",
        default="graduation.db",
        help="卒業要件DBファイル（デフォルト: graduation.db）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    db_path = Path(args.db)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"DBファイルが見つかりません: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    taken_subjects = load_taken_subjects(str(csv_path))
    type_map = load_type_map(cursor)
    subject_flag_map = load_subject_flag_map(cursor)
    subject_category_map = load_subject_category_map(cursor)
    credits, credits_by_flag = calculate_credits(
        taken_subjects,
        type_map,
        subject_flag_map,
        subject_category_map,
    )
    group_totals = calculate_group_credits(cursor, credits)
    results = check_requirements(cursor, credits, credits_by_flag, group_totals)
    print_results(results)

    conn.close()


if __name__ == "__main__":
    main()

## python3 py/graduation.py --csv output/me3.csv