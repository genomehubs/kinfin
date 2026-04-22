// Utilities for parsing and serializing concatenated 3-digit column codes

const CODE_RE = /^\d{3}$/;

export function parseConcatCodes(str = "") {
  if (!str) return [];
  const parts = [];
  for (let i = 0; i < str.length; i += 3) {
    const token = str.slice(i, i + 3);
    if (CODE_RE.test(token)) parts.push(token);
  }
  return parts;
}

export function serializeCodes(codes = []) {
  return codes.filter(Boolean).join("");
}

// Merge an array of repeated param values into a single concatenated string
export function mergeRepeatedParams(values = []) {
  if (!values || values.length === 0) return "";
  return values.filter(Boolean).join("");
}

export default {
  parseConcatCodes,
  serializeCodes,
  mergeRepeatedParams,
};

export function getCodesFromSearchParams(
  searchParams,
  key,
  columnDescriptions = [],
) {
  if (!searchParams.has(key)) {
    return columnDescriptions && columnDescriptions.length > 0
      ? columnDescriptions.filter((col) => col.isDefault).map((col) => col.code)
      : [];
  }

  const all = searchParams.getAll(key);
  if (all.length > 1) {
    return parseConcatCodes(mergeRepeatedParams(all));
  }

  const val = all[0] || "";
  const parsed = parseConcatCodes(val);
  return parsed.length > 0 ? parsed : [val];
}
