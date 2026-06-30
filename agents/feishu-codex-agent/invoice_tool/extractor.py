"""Invoice information extractor."""
import re, os
from PIL import Image
import pytesseract
from invoice_tool import pdf_parser

TESS_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.isfile(TESS_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESS_CMD

_HAS_CHI = os.path.isfile(r"C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata")

_P = {
    "inv_no": [
        re.compile(r"发票号码[：:]\s*(\w+)"),
        re.compile(r"(?:No|Invoice\s*(?:No\.?|Number)?)[：:]*\s*(\w+)", re.IGNORECASE),
    ],
    "date": [
        re.compile(r"开票日期[：:]\s*(\d{4}[-./\u5e74]\d{1,2}[-./\u6708]\d{1,2})"),
        re.compile(r"(\d{4}[-./\u5e74]\d{1,2}[-./\u6708]\d{1,2})"),
    ],
    "amt": [
        re.compile(r"价税合计[^0-9]*?([\d,]+\.\d{2})"),
        re.compile(r"合计[：:]*?[^0-9]*?([\d,]+\.\d{2})"),
        re.compile(r"Total[：:]*\s*([\d,]+\.\d{2})"),
    ],
    "seller": [
        re.compile(r"销售方[名称]?[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"销货单位[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"Seller[：:]*\s*(.+?)(?:\n|$)"),
    ],
}


def _ef(text, field):
    for pat in _P.get(field, []):
        m = pat.search(text)
        if m:
            v = m.group(1).strip()
            if v and len(v) < 100:
                return v
    return None


def extract_from_text(text):
    return {"invoice_no": _ef(text, "inv_no"), "date": _ef(text, "date"), "amount": _ef(text, "amt"), "seller": _ef(text, "seller")}


def extract_from_image(fp):
    try:
        img = Image.open(fp)
        lang = "chi_sim+eng" if _HAS_CHI else "eng"
        text = pytesseract.image_to_string(img, lang=lang)
        if text.strip():
            return extract_from_text(text)
    except:
        pass
    return {"invoice_no": None, "date": None, "amount": None, "seller": None}


def extract_from_pdf(fp):
    text = pdf_parser.extract_text(fp)
    if text.strip():
        r = extract_from_text(text)
        if any(v is not None for v in r.values()):
            return r
    try:
        with open(fp, "rb") as f:
            raw = f.read()
        raw_text = raw.decode("latin-1", errors="replace")
        clean = re.sub(r"[^\x20-\x7e\u4e00-\u9fff\uff00-\uffef]", "", raw_text)
        if clean.strip():
            r = extract_from_text(clean)
            if any(v is not None for v in r.values()):
                return r
    except:
        pass
    return {"invoice_no": None, "date": None, "amount": None, "seller": None}


def extract(fp):
    ext = os.path.splitext(fp)[1].lower()
    if ext == ".pdf":
        return extract_from_pdf(fp)
    elif ext in (".jpg", ".jpeg", ".png"):
        return extract_from_image(fp)
    return {"invoice_no": None, "date": None, "amount": None, "seller": None}
