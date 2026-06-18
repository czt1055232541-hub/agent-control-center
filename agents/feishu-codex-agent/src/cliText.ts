export function decodeCliChunk(chunk: Buffer | string, encoding = "auto"): string {
  if (typeof chunk === "string") {
    return chunk;
  }
  const normalized = encoding.toLowerCase();
  if (normalized !== "auto") {
    return new TextDecoder(normalized).decode(chunk);
  }
  const utf8 = new TextDecoder("utf-8").decode(chunk);
  const gb18030 = new TextDecoder("gb18030").decode(chunk);
  return mojibakeScore(gb18030) < mojibakeScore(utf8) ? gb18030 : utf8;
}

function mojibakeScore(value: string): number {
  let score = 0;
  for (const char of value) {
    if (char === "\uFFFD") {
      score += 10;
    }
  }
  const commonMojibake = /[锛绋浣犲笂笅鐨勮]/g;
  score += (value.match(commonMojibake) ?? []).length * 2;
  return score;
}
