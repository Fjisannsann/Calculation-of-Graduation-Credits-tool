from spire.pdf import PdfDocument, PdfTableExtractor
import csv
import re
import unicodedata
import os

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\n", " ").replace("\t", " ")
    # スペースを削除
    text = re.sub(r"\s+", "", text)
    return text.strip()

def delete_bracket(text):
    if "【" in text and "】" in text:
        text = text.replace("【", "").replace("】", "")
    if "<" in text and ">" in text:
        text = text.replace("<", "").replace(">", "")
    if text.startswith("（") and text.endswith("）"):
        text = text.replace("（", "").replace("）", "")
    return normalize_text(text)

def is_header(row):
    return row == ["科目名", "単位", "成績", "年度"]

def load_with_categories(data):
    data2 = []

    big = None
    middle = None
    small = None

    for row in data:
        if len(row) == 0:
            continue

        name = row[0]

        # 大カテゴリ
        if "【" in name and "】" in name:
            big = delete_bracket(name)
            middle = None
            small = None
            continue

        # 中カテゴリ
        if "<" in name and ">" in name:
            middle = delete_bracket(name)
            small = None
            continue

        # 小カテゴリ
        if name.startswith("（") and name.endswith("）"):
            small = delete_bracket(name)
            continue

        # 科目
        if len(row) >= 4 and row[3].isdigit():
            data2.append([
                big,
                middle,
                small,
                name,
                row[1],
                row[2],
                row[3]
            ])

    return data2

# main
pdf_path = ['haru', 'kage', 'me', 'moza']

for path in pdf_path:
    full_path = os.path.join("grades", path + ".pdf")
    output_path = os.path.join("output", path + "2.csv")
    output_path2 = os.path.join("output", path + "3.csv")
    pdf = PdfDocument()
    pdf.LoadFromFile(full_path)

    extractor = PdfTableExtractor(pdf)

    # ブロックごとに格納
    blocks = []

    for pageIndex in range(pdf.Pages.Count):
        tables = extractor.ExtractTable(pageIndex)
        if tables is not None:
            for tableIndex in range(len(tables)):
                table = tables[tableIndex]

                for rowIndex in range(table.GetRowCount()):
                    row = []
                    for colIndex in range(table.GetColumnCount()):
                        text = table.GetText(rowIndex, colIndex)
                        text = normalize_text(text)
                        row.append(text)

                    # 必要なブロック数だけ確保
                    num_blocks = (len(row) + 3) // 4
                    while len(blocks) < num_blocks:
                        blocks.append([])

                    # 各ブロックに追加
                    for i in range(num_blocks):
                        chunk = row[i*4:(i+1)*4]

                        if any(cell.strip() for cell in chunk):
                            blocks[i].append(chunk)

    # --- ブロックを順番に連結 ---
    all_rows = []
    for block in blocks:
        all_rows.extend(block)

    all_rows = [row for row in all_rows if not is_header(row)]

    # --- 書き出し ---
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(all_rows)

    structured_data = load_with_categories(all_rows)

    with open(output_path2, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(structured_data)

    pdf.Dispose()