"""
Export to Excel.
"""
import xlsxwriter

def export_to_excel(file_data, output_path):
    wb = xlsxwriter.Workbook(output_path)
    hdr = wb.add_format({"bold": True, "bg_color": "#4472C4", "font_color": "white", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 11})
    cel = wb.add_format({"border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})

    ws = wb.add_worksheet("汇总表")
    ws.set_column("A:A", 15); ws.set_column("B:B", 15); ws.set_column("C:C", 12)
    ws.set_column("D:D", 25); ws.set_column("E:E", 60); ws.set_column("F:F", 60)

    headers = ["发票号", "日期", "金额", "销售方", "源文件", "目标文件"]
    for c, h in enumerate(headers):
        ws.write(0, c, h, hdr)

    for r, d in enumerate(file_data, 1):
        info = d.get("info", {})
        ws.write(r, 0, info.get("invoice_no", ""), cel)
        ws.write(r, 1, info.get("date", ""), cel)
        ws.write(r, 2, info.get("amount", ""), cel)
        ws.write(r, 3, info.get("seller", ""), cel)
        ws.write(r, 4, d.get("source", ""), cel)
        ws.write(r, 5, d.get("dest", ""), cel)

    ws.autofilter(0, 0, len(file_data), len(headers) - 1)

    ws2 = wb.add_worksheet("统计")
    ws2.set_column("A:A", 20); ws2.set_column("B:B", 15)
    ws2.write(0, 0, "统计项", hdr); ws2.write(0, 1, "值", hdr)
    ws2.write(1, 0, "总文件数", cel); ws2.write(1, 1, len(file_data), cel)

    sellers = {}
    for d in file_data:
        s = d.get("info", {}).get("seller", "未知") or "未知"
        sellers[s] = sellers.get(s, 0) + 1

    ws2.write(3, 0, "销售方统计", hdr); ws2.write(4, 0, "销售方", hdr); ws2.write(4, 1, "数量", hdr)
    for i, (seller, count) in enumerate(sorted(sellers.items(), key=lambda x: -x[1]), 5):
        ws2.write(i, 0, seller, cel); ws2.write(i, 1, count, cel)

    wb.close()
    return output_path


def export_to_csv(file_data, output_path):
    """Export invoice summary to CSV."""
    import csv
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["发票号", "日期", "金额", "销售方", "源文件", "目标文件"])
        for d in file_data:
            info = d.get("info", {})
            writer.writerow([
                info.get("invoice_no", ""),
                info.get("date", ""),
                info.get("amount", ""),
                info.get("seller", ""),
                d.get("source", ""),
                d.get("dest", ""),
            ])
    return output_path
