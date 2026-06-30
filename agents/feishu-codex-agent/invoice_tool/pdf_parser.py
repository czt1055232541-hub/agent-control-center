"""Custom lightweight PDF text extractor."""
import zlib, re

class PDFTextExtractor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw = b""
        self.objects = {}
    def _read(self):
        with open(self.filepath, "rb") as f:
            self.raw = f.read()
    def _parse_objects(self):
        pattern = re.compile(rb"(\d+)\s+\d+\s+obj\s+(.*?)\s*endobj", re.DOTALL)
        for match in pattern.finditer(self.raw):
            obj_num = int(match.group(1))
            content = match.group(2)
            stream_match = re.search(rb"stream\s(.+?)\s*endstream", content, re.DOTALL)
            if stream_match:
                stream_data = stream_match.group(1).strip()
                self.objects[obj_num] = {"raw": content}
                if b"FlateDecode" in content or b"Fl" in content:
                    try:
                        self.objects[obj_num]["stream_text"] = zlib.decompress(stream_data)
                    except:
                        try:
                            self.objects[obj_num]["stream_text"] = zlib.decompress(stream_data, -zlib.MAX_WBITS)
                        except:
                            pass
                else:
                    self.objects[obj_num]["stream_text"] = stream_data
    def _text_from_stream(self, stream):
        texts = []
        cleaned = re.sub(rb"%.*?\n", b"\n", stream)
        for m in re.finditer(rb"\(([^)]*?)\)\s*Tj", cleaned):
            texts.append(m.group(1).decode("latin-1", errors="replace"))
        for m in re.finditer(rb"\[(.*?)\]\s*TJ", cleaned, re.DOTALL):
            for tm in re.finditer(rb"\(([^)]*?)\)", m.group(1)):
                texts.append(tm.group(1).decode("latin-1", errors="replace"))
        for m in re.finditer(rb"\(([^)]*?)\)\s*'", cleaned):
            texts.append(m.group(1).decode("latin-1", errors="replace"))
        return "".join(texts)
    def extract_text(self):
        self._read()
        self._parse_objects()
        all_text = []
        for obj_data in self.objects.values():
            st = obj_data.get("stream_text", b"")
            if st:
                t = self._text_from_stream(st)
                if t.strip():
                    all_text.append(t)
        return "\n".join(all_text)
    def extract_raw_text(self):
        self._read()
        texts = []
        for m in re.finditer(rb"\(([\x20-\x7e\x80-\xff]{2,}?)\)\s*Tj", self.raw):
            texts.append(m.group(1).decode("latin-1", errors="replace"))
        for m in re.finditer(rb"\(([\x20-\x7e\x80-\xff]{2,}?)\)\s*'", self.raw):
            texts.append(m.group(1).decode("latin-1", errors="replace"))
        return "\n".join(texts)

def extract_text(filepath):
    ext = PDFTextExtractor(filepath)
    try:
        t = ext.extract_text()
        if t.strip():
            return t
    except:
        pass
    try:
        return ext.extract_raw_text()
    except:
        return ""
