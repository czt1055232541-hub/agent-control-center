"""Invoice Tool - GUI & CLI application."""
import os
import sys
import threading
from pathlib import Path
from tkinter import Tk, ttk, filedialog, messagebox, StringVar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanner import scan_directory
from extractor import extract
from organizer import organize_files
from exporter import export_to_excel, export_to_csv


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("发票整理工具 v1.0")
        self.root.geometry("850x680")
        self.root.minsize(700, 550)
        self.src_dir = StringVar()
        self.out_dir = StringVar()
        self.organize_by = StringVar(value="seller")
        self.files = []
        self.extracted = []
        self.results = []
        self._build_ui()

    def _build_ui(self):
        f0 = ttk.LabelFrame(self.root, text="文件夹选择", padding=10)
        f0.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(f0, text="源文件夹:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f0, textvariable=self.src_dir, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(f0, text="浏览...", command=self._browse_src).grid(row=0, column=2)
        ttk.Label(f0, text="输出文件夹:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Entry(f0, textvariable=self.out_dir, width=60).grid(row=1, column=1, padx=5, pady=(5, 0))
        ttk.Button(f0, text="浏览...", command=self._browse_out).grid(row=1, column=2, pady=(5, 0))

        f1 = ttk.LabelFrame(self.root, text="操作", padding=10)
        f1.pack(fill="x", padx=10, pady=5)
        self.btn_scan = ttk.Button(f1, text="1. 扫描文件", command=self._scan, width=16)
        self.btn_scan.pack(side="left", padx=3)
        self.btn_extract = ttk.Button(f1, text="2. 提取信息", command=self._extract, width=16, state="disabled")
        self.btn_extract.pack(side="left", padx=3)
        self.btn_org = ttk.Button(f1, text="3. 一键整理", command=self._organize, width=16, state="disabled")
        self.btn_org.pack(side="left", padx=3)
        self.btn_export = ttk.Button(f1, text="导出Excel", command=self._export, width=16, state="disabled")
        self.btn_export.pack(side="left", padx=3)
        ttk.Separator(f1, orient="vertical").pack(side="left", padx=15, fill="y")
        ttk.Label(f1, text="分类:").pack(side="left")
        ttk.Radiobutton(f1, text="按销售方", variable=self.organize_by, value="seller").pack(side="left", padx=3)
        ttk.Radiobutton(f1, text="按日期（月份）", variable=self.organize_by, value="date").pack(side="left", padx=3)

        f2 = ttk.LabelFrame(self.root, text="文件预览", padding=5)
        f2.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ("文件名", "类型", "发票号", "日期", "金额", "销售方")
        self.tree = ttk.Treeview(f2, columns=cols, show="headings", height=14)
        widths = [200, 55, 130, 110, 95, 150]
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, minwidth=50)
        vsb = ttk.Scrollbar(f2, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.progress = ttk.Progressbar(self.root, mode="determinate", length=400)
        self.status = StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", padx=10, pady=(0, 10))

    def _browse_src(self):
        d = filedialog.askdirectory(title="选择发票文件夹")
        if d:
            self.src_dir.set(d)
            if not self.out_dir.get():
                self.out_dir.set(d)

    def _browse_out(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.out_dir.set(d)

    def _set_busy(self, busy):
        st = "disabled" if busy else "normal"
        if not busy:
            self.btn_scan["state"] = "normal"
            self.btn_extract["state"] = "normal" if self.files else "disabled"
            self.btn_org["state"] = "normal" if self.extracted else "disabled"
            self.btn_export["state"] = "normal" if self.results else "disabled"
        else:
            for b in [self.btn_scan, self.btn_extract, self.btn_org, self.btn_export]:
                b["state"] = st

    def _scan(self):
        src = self.src_dir.get()
        if not src or not os.path.isdir(src):
            messagebox.showwarning("提示", "请选择有效的源文件夹")
            return
        self._set_busy(True)
        self.status.set("扫描中...")
        def task():
            self.files = scan_directory(src)
            self.extracted = []
            self.results = []
            self.root.after(0, self._scan_done)
        threading.Thread(target=task, daemon=True).start()

    def _scan_done(self):
        self.tree.delete(*self.tree.get_children())
        for f in self.files:
            p = Path(f)
            self.tree.insert("", "end", values=(p.name, p.suffix.upper(), "", "", "", ""))
        self.status.set(f"扫描完成：{len(self.files)} 个文件")
        self._set_busy(False)

    def _extract(self):
        if not self.files:
            return
        self._set_busy(True)
        self.status.set("提取发票信息...")
        self.progress.pack(fill="x", padx=10, pady=(0, 5))
        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        def task():
            results = []
            for i, f in enumerate(self.files):
                info = extract(f)
                results.append(info)
                self.root.after(0, lambda v=i+1: self.progress.configure(value=v))
            self.root.after(0, lambda: self._extract_done(results))
        threading.Thread(target=task, daemon=True).start()

    def _extract_done(self, data):
        self.extracted = data
        self.progress.pack_forget()
        self.tree.delete(*self.tree.get_children())
        ok = 0
        for f, info in zip(self.files, data):
            p = Path(f)
            vals = (p.name, p.suffix.upper(), info.get("invoice_no","") or "",
                    info.get("date","") or "", info.get("amount","") or "",
                    info.get("seller","") or "")
            self.tree.insert("", "end", values=vals)
            if any(v for v in info.values()):
                ok += 1
        self.status.set(f"提取完成：{ok}/{len(self.files)} 个提取成功")
        self._set_busy(False)

    def _organize(self):
        out = self.out_dir.get()
        if not out:
            messagebox.showwarning("提示", "请选择输出文件夹")
            return
        if not self.extracted:
            return
        self._set_busy(True)
        self.status.set("正在整理...")
        self.progress.pack(fill="x", padx=10, pady=(0, 5))
        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        def task():
            results = organize_files(self.files, self.extracted, out, self.organize_by.get())
            self.root.after(0, lambda: self._org_done(results))
        threading.Thread(target=task, daemon=True).start()

    def _org_done(self, results):
        self.results = results
        self.progress.pack_forget()
        ok = sum(1 for r in results if r["status"] == "copied")
        err = len(results) - ok
        self.tree.delete(*self.tree.get_children())
        for r, info in zip(results, self.extracted):
            p = Path(r["source"])
            vals = (p.name, p.suffix.upper(), info.get("invoice_no","") or "",
                    info.get("date","") or "", info.get("amount","") or "",
                    info.get("seller","") or "")
            self.tree.insert("", "end", values=vals)
        msg = f"整理完成：成功{ok} 个" + (f"，失败{err} 个" if err else "")
        self.status.set(msg)
        if err:
            messagebox.showwarning("提示", f"{err} 个文件整理失败，请检查输出文件夹权限")
        self._set_busy(False)

    def _export(self):
        if not self.results:
            messagebox.showwarning("提示", "请先整理文件")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")], initialfile="发票汇总表.xlsx",
            title="导出 Excel 汇总表")
        if not fp:
            return
        self.status.set("正在导出 Excel...")
        combined = [{"source": r["source"], "dest": r["dest"], "info": info}
                    for r, info in zip(self.results, self.extracted)]
        def task():
            try:
                export_to_excel(combined, fp)
                self.root.after(0, lambda: self.status.set(f"Excel 已导出：{fp}"))
                self.root.after(0, lambda: messagebox.showinfo("导出成功", f"Excel 汇总表已保存到：\n{fp}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("导出失败", f"导出出错：{e}"))
                self.root.after(0, lambda: self.status.set("导出失败"))
        threading.Thread(target=task, daemon=True).start()


def main():
    root = Tk()
    App(root)
    root.mainloop()


def cli():
    """Command-line entry: python main.py <input_dir> [output_dir] [--by seller|date] [--csv]"""
    import argparse
    parser = argparse.ArgumentParser(description="发票整理工具 - 命令行模式")
    parser.add_argument("input_dir", help="发票文件目录")
    parser.add_argument("output_dir", nargs="?", default=None, help="输出目录（默认与输入目录相同）")
    parser.add_argument("--by", choices=["seller", "date"], default="seller", help="分类方式")
    parser.add_argument("--csv", action="store_true", help="导出为 CSV 而非 Excel")
    args = parser.parse_args()

    src = args.input_dir
    out = args.output_dir or src

    files = scan_directory(src)
    print(f"扫描到 {len(files)} 个文件")

    extracted = []
    for i, f in enumerate(files):
        info = extract(f)
        extracted.append(info)
        print(f"  [{i+1}/{len(files)}] {os.path.basename(f)} -> {info.get('invoice_no','?')} / {info.get('date','?')} / {info.get('amount','?')} / {info.get('seller','?')}")

    results = organize_files(files, extracted, out, args.by)
    ok = sum(1 for r in results if r["status"] == "copied")
    print(f"\n整理完成：成功 {ok}/{len(results)} 个")

    combined = [{"source": r["source"], "dest": r["dest"], "info": info} for r, info in zip(results, extracted)]
    if args.csv:
        csv_path = os.path.join(out, "发票汇总.csv")
        export_to_csv(combined, csv_path)
        print(f"CSV 已导出：{csv_path}")
    else:
        xlsx_path = os.path.join(out, "发票汇总.xlsx")
        export_to_excel(combined, xlsx_path)
        print(f"Excel 已导出：{xlsx_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        main()
