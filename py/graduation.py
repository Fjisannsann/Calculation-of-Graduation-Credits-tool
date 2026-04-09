import argparse
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path


def load_taken_subjects(file_path):
    subjects = []
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            grade_str = (row.get("grade") or "").strip()
            if grade_str == "":
                continue

            grade = int(float(grade_str))
            if grade == 0:
                continue

            subjects.append(
                {
                    "subject": row["subject"],
                    "credits": float(row["credits"]),
                }
            )
    return subjects


def load_subject_info(cursor):
    cursor.execute(
        """
        SELECT
            s.subject,
            s.category_big,
            s.category_mid,
            s.category_small,
            s.category_detail,
            sf.flag
        FROM subjects s
        LEFT JOIN subject_flags sf ON s.subject = sf.subject
        """
    )

    subject_map = {}
    for subject, big, mid, small, detail, flag in cursor.fetchall():
        subject_map[subject] = {
            "big": big,
            "mid": mid,
            "small": small,
            "detail": detail,
            "flag": int(flag) if flag is not None else None,
        }
    return subject_map


def create_credit_bucket():
    return {
        "big": defaultdict(float),
        "mid": defaultdict(float),
        "small": defaultdict(float),
        "detail": defaultdict(float),
        "subject": defaultdict(float),
        "all": 0.0,
    }


def add_credit(credits, type_, name, value):
    if type_ == "all":
        credits["all"] += value
        return
    if name:
        credits[type_][name] += value


def calculate_credits(taken_subjects, subject_map):
    credits = create_credit_bucket()
    credits_by_flag = defaultdict(create_credit_bucket)

    for item in taken_subjects:
        subject = item["subject"]
        credit = item["credits"]
        info = subject_map.get(subject)
        if info is None:
            continue

        add_credit(credits, "all", None, credit)
        add_credit(credits, "subject", subject, credit)
        add_credit(credits, "big", info["big"], credit)
        add_credit(credits, "mid", info["mid"], credit)
        add_credit(credits, "small", info["small"], credit)
        add_credit(credits, "detail", info["detail"], credit)

        flag = info["flag"]
        if flag is not None:
            flagged = credits_by_flag[flag]
            add_credit(flagged, "all", None, credit)
            add_credit(flagged, "subject", subject, credit)
            add_credit(flagged, "big", info["big"], credit)
            add_credit(flagged, "mid", info["mid"], credit)
            add_credit(flagged, "small", info["small"], credit)
            add_credit(flagged, "detail", info["detail"], credit)

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
    subject_map = load_subject_info(cursor)
    credits, credits_by_flag = calculate_credits(taken_subjects, subject_map)
    group_totals = calculate_group_credits(cursor, credits)
    results = check_requirements(cursor, credits, credits_by_flag, group_totals)
    print_results(results)

    conn.close()


if __name__ == "__main__":
    main()
