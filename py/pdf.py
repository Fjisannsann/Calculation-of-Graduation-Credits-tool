from spire.pdf import PdfDocument, PdfTableExtractor
import csv

pdf_path = 'pdf/campus.pdf'
pdf = PdfDocument()
pdf.LoadFromFile(pdf_path)

extractor = PdfTableExtractor(pdf)

for pageIndex in range(pdf.Pages.Count):
    tables = extractor.ExtractTable(pageIndex)
    if tables is not None:
        for tableIndex in range(len(tables)):
            table = tables[tableIndex]
            with open("output/" + str(pageIndex+1) + "-Table" + str(tableIndex+1) + ".csv", 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for rowIndex in range(table.GetRowCount()):
                    row = []
                    for colIndex in range(table.GetColumnCount()):
                        text = table.GetText(rowIndex, colIndex)
                        text = text.replace('\n', ' ')
                        row.append(text)
                    writer.writerow(row)

pdf.Dispose()