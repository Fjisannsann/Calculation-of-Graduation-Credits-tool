import pdfplumber

with pdfplumber.open("pdf/campus.pdf") as pdf:
    text = pdf.pages[0].extract_text()

# デバッグ（これ絶対見る）
lines = text.split("\n")

for line in lines[:50]:
    print(line)