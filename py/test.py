import pdfplumber
import re
import pandas as pd
import os

pdf_path = "pdf/campus.pdf"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

results = []

with pdfplumber.open(pdf_path) as pdf:
    text = ""
    for page in pdf.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

# 正規化
text = text.replace("\u3000", " ")
text = re.sub(r"\s+", " ", text)

# 数値パターン位置を取得
pattern = r"\d+\.\d+\s+\d\s+\d{2}"

matches = list(re.finditer(pattern, text))

for i in range(len(matches)):
    start = matches[i].end()

    if i + 1 < len(matches):
        end = matches[i+1].start()
    else:
        end = len(text)

    # 数値部分
    nums = matches[i].group()
    credit, grade, year = re.findall(r"\d+\.\d+|\d+", nums)

    # 科目名（間の文字）
    subject = text[start:end].strip()

    # ノイズ除去
    if any(x in subject for x in ["小計", "総計", "GPA", "科目計"]):
        continue

    if len(subject) < 2:
        continue

    results.append([subject, float(credit), grade, year])

df = pd.DataFrame(results, columns=["科目名", "単位", "評価", "年度"])

# CSV出力
csv_path = f"{output_dir}/grades_fixed.csv"
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(df.head())
print("合計単位:", df["単位"].sum())