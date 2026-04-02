from spire.pdf import PdfDocument, PdfTableExtractor
import csv
import re
import unicodedata
import os

REPLACE_DICT = {
    "Academic Engli sh": "Academic English",
    "Practi calEngli sh": "Practical English",
    "Academi c Engl i sh": "Academic English",
    "Pr act i cal Engl i sh": "Practical English",
    "I II": "III",
}

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)

    text = text.replace("\n", " ").replace("\t", " ")

    # 数値
    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)

    # --- ローマ数字の前にスペース ---
    text = re.sub(r'([^\s])([IVX]+)\b', r'\1 \2', text)

    # --- ローマ数字の崩れを先に修正 ---
    text = re.sub(r'\bI\s+I\s+I\b', 'III', text)
    text = re.sub(r'\bI\s+I\b', 'II', text)
    text = re.sub(r'\bV\s+I\b', 'VI', text)
    text = re.sub(r'\bI\s+V\b', 'IV', text)

    # --- 辞書補正 ---
    for k, v in REPLACE_DICT.items():
        text = text.replace(k, v)

    # スペース整理
    text = re.sub(r"\s+", " ", text)

    return text.strip()

pdf_path = ['haru', 'kage', 'me', 'moza']

for path in pdf_path:
    full_path = os.path.join("grades", path + ".pdf")
    output_path = os.path.join("output", path + ".csv")
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

    # --- 書き出し ---
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(all_rows)

pdf.Dispose()