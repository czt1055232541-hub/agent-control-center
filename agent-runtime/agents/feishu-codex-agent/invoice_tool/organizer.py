"""
File organizer.
"""
import os
import re
import shutil
from pathlib import Path

def sanitize(name, max_len=80):
    name = re.sub(r"[<>:\"/\\|?*]", "_", name)
    name = name.strip(". ")
    return name[:max_len] if len(name) > max_len else (name or "unnamed")

def fmt_date(raw):
    if not raw:
        return "unknown_date"
    m = re.search(r"(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return raw[:10] if len(raw) >= 10 else "unknown_date"

def gen_filename(info, ext):
    date = fmt_date(info.get("date"))
    amount = info.get("amount", "unknown") or "unknown"
    seller = info.get("seller", "unknown") or "unknown"
    amount = amount.replace(",", "")
    parts = [p for p in [sanitize(date), sanitize(amount), sanitize(seller)]
             if p and p != "unknown" and not p.startswith("unknown")]
    if not parts:
        parts = ["unknown"]
    name = "_".join(parts) + ext
    return sanitize(name, max_len=200)

def organize_files(files, extracted_data, output_dir, organize_by="seller"):
    results = []
    for fp, info in zip(files, extracted_data):
        src = Path(fp)
        ext = src.suffix.lower()
        new_name = gen_filename(info, ext)
        if organize_by == "seller":
            subdir = sanitize(info.get("seller", "unknown")) or "unknown"
        else:
            date = fmt_date(info.get("date"))
            subdir = date[:7] if date != "unknown_date" else "unknown"
        dest_dir = Path(output_dir) / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / new_name
        c = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{dest_path.stem}_{c}{ext}"
            c += 1
        try:
            shutil.copy2(str(src), str(dest_path))
            results.append({"source": str(src), "dest": str(dest_path), "status": "copied"})
        except Exception as e:
            results.append({"source": str(src), "dest": str(dest_path), "status": f"error: {e}"})
    return results
