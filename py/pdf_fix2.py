from spire.pdf import PdfDocument, PdfTableExtractor
import csv
import re
import unicodedata
import os

# =============================
# 正規化
# =============================
REPLACE_DICT = {
    "Academic Engli sh": "Academic English",
    "Practi calEngli sh": "Practical English",
    "Academi c Engl i sh": "Academic English",
    "Pr act i cal Engl i sh": "Practical English",
    "I II": "III",
    "I I": "II",
}

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\n", " ").replace("\t", " ")

    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)

    # ローマ数字補正
    text = re.sub(r'\bI\s+I\s+I\b', 'III', text)
    text = re.sub(r'\bI\s+I\b', 'II', text)
    text = re.sub(r'\bV\s+I\b', 'VI', text)
    text = re.sub(r'\bI\s+V\b', 'IV', text)

    # 辞書補正
    for k, v in REPLACE_DICT.items():
        text = text.replace(k, v)

    # 日本語＋ローマ数字対応
    text = re.sub(r'([A-Za-z一-龥ぁ-んァ-ンー])([IVX]+)\b', r'\1 \2', text)

    text = re.sub(r"\s+", " ", text)
    return text.strip()

# =============================
# PDF → CSV（カテゴリ付き）
# =============================
def pdf_to_structured_csv(pdf_paths):
    os.makedirs("output", exist_ok=True)

    for path in pdf_paths:
        full_path = os.path.join("grades", path + ".pdf")
        output_path = os.path.join("output", path + "_structured.csv")

        pdf = PdfDocument()
        pdf.LoadFromFile(full_path)

        extractor = PdfTableExtractor(pdf)

        blocks = []

        # --- テーブル抽出 ---
        for pageIndex in range(pdf.Pages.Count):
            tables = extractor.ExtractTable(pageIndex)
            if tables is not None:
                for table in tables:
                    for rowIndex in range(table.GetRowCount()):
                        row = []
                        for colIndex in range(table.GetColumnCount()):
                            text = table.GetText(rowIndex, colIndex)
                            text = normalize_text(text)
                            row.append(text)

                        num_blocks = (len(row) + 3) // 4
                        while len(blocks) < num_blocks:
                            blocks.append([])

                        for i in range(num_blocks):
                            chunk = row[i*4:(i+1)*4]
                            if any(cell.strip() for cell in chunk):
                                blocks[i].append(chunk)

        # --- 縦連結 ---
        all_rows = []
        for block in blocks:
            all_rows.extend(block)

        # =============================
        # カテゴリ付き構造化
        # =============================
        big = None
        middle = None
        small = None

        structured = []

        for row in all_rows:
            if len(row) == 0:
                continue

            name = row[0]

            # 大カテゴリ
            if "【" in name and "】" in name:
                big = name.replace("【", "").replace("】", "")
                middle = None
                small = None
                continue

            # 中カテゴリ
            if "<" in name and ">" in name:
                middle = name.replace("<", "").replace(">", "")
                small = None
                continue

            # 小カテゴリ
            if name.startswith("(") and name.endswith(")"):
                small = name.replace("(", "").replace(")", "")
                continue

            # 無視
            if "小計" in name or name == "":
                continue

            # 科目
            if len(row) >= 4 and row[3].isdigit():
                structured.append([
                    big,
                    middle,
                    small,
                    name,
                    row[1],
                    row[2],
                    row[3]
                ])

        # =============================
        # 書き出し
        # =============================
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダ
            writer.writerow(["大カテゴリ", "中カテゴリ", "小カテゴリ", "科目名", "単位", "成績", "年度"])

            writer.writerows(structured)

        pdf.Dispose()

# =============================
# 実行
# =============================
pdf_list = ["haru", "kage", "me", "moza"]
pdf_to_structured_csv(pdf_list)