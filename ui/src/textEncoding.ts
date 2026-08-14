export type TextEncoding = "utf-8" | "gb18030" | "big5" | "utf-16le" | "utf-16be";
export type TextEncodingChoice = "auto" | TextEncoding;
export type TextEncodingConfidence = "high" | "medium" | "low";

export type DecodedTextFile = {
  encoding: TextEncoding;
  label: string;
  text: string;
  confidence: TextEncodingConfidence;
  hadBom: boolean;
  replacementCount: number;
};

export const textEncodingOptions: {value: TextEncodingChoice; label: string}[] = [
  {value: "auto", label: "自动检测"},
  {value: "utf-8", label: "UTF-8"},
  {value: "gb18030", label: "GB18030 / GBK"},
  {value: "big5", label: "Big5（繁体）"},
  {value: "utf-16le", label: "UTF-16 LE"},
  {value: "utf-16be", label: "UTF-16 BE"},
];

const labels: Record<TextEncoding, string> = {
  "utf-8": "UTF-8",
  gb18030: "GB18030 / GBK",
  big5: "Big5",
  "utf-16le": "UTF-16 LE",
  "utf-16be": "UTF-16 BE",
};

const bomByEncoding: Partial<Record<TextEncoding, number[]>> = {
  "utf-8": [0xef, 0xbb, 0xbf],
  "utf-16le": [0xff, 0xfe],
  "utf-16be": [0xfe, 0xff],
};

function asBytes(input: ArrayBuffer | Uint8Array): Uint8Array {
  return input instanceof Uint8Array ? input : new Uint8Array(input);
}

function startsWith(bytes: Uint8Array, prefix: number[]): boolean {
  return prefix.every((value, index) => bytes[index] === value);
}

function stripMatchingBom(bytes: Uint8Array, encoding: TextEncoding): Uint8Array {
  const bom = bomByEncoding[encoding];
  return bom && startsWith(bytes, bom) ? bytes.subarray(bom.length) : bytes;
}

function decode(bytes: Uint8Array, encoding: TextEncoding, fatal: boolean): string {
  return new TextDecoder(encoding, {fatal}).decode(stripMatchingBom(bytes, encoding)).replace(/^\uFEFF/, "");
}

function occurrences(text: string, expression: RegExp): number {
  return text.match(expression)?.length ?? 0;
}

function textQuality(text: string): number {
  if (!text) return 0;
  const length = Math.max(1, text.length);
  const cjk = occurrences(text, /[\u3400-\u9fff]/g);
  const common = occurrences(
    text,
    /[的一是了我不人在有他这為之大來以個中上們到說國和地也子時道出而要於就下得可你年生自會那後能對着著事其裡里所去行過家十用發天如然作方成者多日都三小二無同麼经經法當起與好看學進種將還分此心前面又定見只主沒公從知全工現情明性]/g,
  );
  const punctuation = occurrences(text, /[，。！？；：“”‘’、《》…]/g);
  const replacements = occurrences(text, /\uFFFD/g);
  const nulls = occurrences(text, /\u0000/g);
  const controls = occurrences(text, /[\u0001-\u0008\u000b\u000c\u000e-\u001f\u007f]/g);
  const mojibake = occurrences(text, /[ÃÂ]|ï»¿|(?:æ|å|ä|ç|é|è){2,}/gi);
  const chapterHeadings = occurrences(text, /(?:^|\n)\s*第[0-9０-９一二三四五六七八九十百千万两兩零〇]+[章节節卷部回]/gm);
  const readableRatio = occurrences(text, /[^\u0000-\u001f\u007f\uFFFD]/g) / length;
  const cjkRatio = cjk / length;
  const commonRatio = common / Math.max(1, cjk);

  return (
    readableRatio * 35 +
    Math.min(36, cjkRatio * 72) +
    Math.min(28, commonRatio * 46) +
    Math.min(14, (punctuation / length) * 180) +
    Math.min(24, chapterHeadings * 6) -
    replacements * 18 -
    nulls * 24 -
    controls * 14 -
    mojibake * 8
  );
}

function replacementCount(text: string): number {
  return occurrences(text, /\uFFFD/g);
}

function decodedResult(
  bytes: Uint8Array,
  encoding: TextEncoding,
  confidence: TextEncodingConfidence,
  hadBom = false,
): DecodedTextFile {
  const text = decode(bytes, encoding, false);
  return {
    encoding,
    label: labels[encoding],
    text,
    confidence,
    hadBom,
    replacementCount: replacementCount(text),
  };
}

export function textEncodingLabel(encoding?: string): string {
  return labels[encoding as TextEncoding] ?? encoding?.toUpperCase() ?? "";
}

export function decodeTextBytes(input: ArrayBuffer | Uint8Array, encoding: TextEncoding): DecodedTextFile {
  return decodedResult(asBytes(input), encoding, "high");
}

export function detectAndDecodeText(input: ArrayBuffer | Uint8Array): DecodedTextFile {
  const bytes = asBytes(input);

  for (const encoding of ["utf-8", "utf-16le", "utf-16be"] as TextEncoding[]) {
    const bom = bomByEncoding[encoding];
    if (bom && startsWith(bytes, bom)) {
      return decodedResult(bytes, encoding, "high", true);
    }
  }

  const pairs = Math.floor(bytes.length / 2);
  if (pairs >= 4) {
    let evenNulls = 0;
    let oddNulls = 0;
    for (let index = 0; index < pairs * 2; index += 2) {
      if (bytes[index] === 0) evenNulls += 1;
      if (bytes[index + 1] === 0) oddNulls += 1;
    }
    const evenRatio = evenNulls / pairs;
    const oddRatio = oddNulls / pairs;
    if (oddRatio > 0.18 && oddRatio > evenRatio * 2.5) {
      return decodedResult(bytes, "utf-16le", oddRatio > 0.45 ? "high" : "medium");
    }
    if (evenRatio > 0.18 && evenRatio > oddRatio * 2.5) {
      return decodedResult(bytes, "utf-16be", evenRatio > 0.45 ? "high" : "medium");
    }
  }

  try {
    const utf8 = decode(bytes, "utf-8", true);
    return {
      encoding: "utf-8",
      label: labels["utf-8"],
      text: utf8,
      confidence: "high",
      hadBom: false,
      replacementCount: 0,
    };
  } catch {
    // Invalid UTF-8 is expected for legacy Chinese TXT files.
  }

  const candidates: {encoding: TextEncoding; text: string; score: number; valid: boolean}[] = [];
  for (const encoding of ["gb18030", "big5", "utf-16le", "utf-16be"] as TextEncoding[]) {
    let text = "";
    let valid = true;
    try {
      text = decode(bytes, encoding, true);
    } catch {
      valid = false;
      try {
        text = decode(bytes, encoding, false);
      } catch {
        continue;
      }
    }
    candidates.push({
      encoding,
      text,
      score: textQuality(text) + (valid ? 8 : -24),
      valid,
    });
  }

  candidates.sort((left, right) => right.score - left.score);
  const best = candidates[0];
  if (!best) {
    return decodedResult(bytes, "utf-8", "low");
  }
  const margin = best.score - (candidates[1]?.score ?? best.score - 20);
  const confidence: TextEncodingConfidence = !best.valid || margin < 5 ? "low" : margin < 14 ? "medium" : "high";
  return {
    encoding: best.encoding,
    label: labels[best.encoding],
    text: best.text,
    confidence,
    hadBom: false,
    replacementCount: replacementCount(best.text),
  };
}
