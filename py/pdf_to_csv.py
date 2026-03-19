import pdfplumber
import pandas as pd
import os

pdf_path = "pdf/campus.pdf"
output_dir = "output"

os.makedirs(output_dir, exist_ok=True)

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"=== PDF INFO ===")
        print(f"Total pages: {len(pdf.pages)}")

        for page_num, page in enumerate(pdf.pages):
            print(f"\n========== Page {page_num+1} ==========")

            # --- テキスト確認 ---
            text = page.extract_text()
            if text:
                print("\n--- Extracted Text (先頭500文字) ---")
                print(text[:500])
            else:
                print("\n[!] No text extracted (画像PDFの可能性あり)")

            # --- 表抽出 ---
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines"
            })

            if not tables:
                print("\n[!] No tables found on this page")
                continue

            print(f"\n[+] Found {len(tables)} table(s)")

            for i, table_data in enumerate(tables):
                print(f"\n----- Table {i+1} Raw Data -----")

                if not table_data:
                    print("[!] Empty table")
                    continue

                # 生データ表示（最初の5行）
                for row in table_data[:5]:
                    print(row)

                print("\n--- Converting to DataFrame ---")

                df = pd.DataFrame(table_data)

                # None対策
                df = df.fillna("")

                # 改行・空白除去
                df = df.applymap(
                    lambda x: x.replace("\n", "").strip() if isinstance(x, str) else x
                )

                print("\n--- DataFrame Head ---")
                print(df.head())

                print("\n--- Columns ---")
                print(df.columns.tolist())

                # CSV保存
                csv_path = f"{output_dir}/page{page_num+1}_table{i+1}.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")

                print(f"\n[+] Saved: {csv_path}")

except FileNotFoundError:
    print(f"[ERROR] File not found: {pdf_path}")
except Exception as e:
    print(f"[ERROR] {e}")