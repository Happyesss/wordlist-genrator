import {
  HARD_LIMIT,
  MIN_LIMIT,
  DEFAULT_LIST_SIZE,
  MAX_TERMS_PER_FIELD,
  MAX_TOKEN_LENGTH
} from "./constants.js";

export function clampNumber(value, min, max) {
  if (!Number.isFinite(value)) return min;
  return Math.min(Math.max(value, min), max);
}

export function normalizeCsv(value) {
  if (typeof value !== "string") return [];

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function sanitizeToken(token) {
  if (!token) return "";

  const normalized = token
    .normalize("NFKC")
    .replace(/\s+/g, "")
    .replace(/[^a-zA-Z0-9@._-]/g, "");

  return normalized.slice(0, MAX_TOKEN_LENGTH);
}

export function unique(values) {
  return [...new Set(values)];
}

export function capitalize(value) {
  if (!value) return value;
  return value[0].toUpperCase() + value.slice(1).toLowerCase();
}

export function caseForms(value) {
  const safe = sanitizeToken(value);
  if (!safe) return [];
  return unique([safe.toLowerCase(), capitalize(safe), safe.toUpperCase()]);
}

export function normalizedField(value, warnings, label) {
  const raw = normalizeCsv(value);
  const cleaned = unique(raw.map(sanitizeToken).filter(Boolean));

  if (cleaned.length > MAX_TERMS_PER_FIELD) {
    warnings.push(`${label}: only first ${MAX_TERMS_PER_FIELD} entries were used.`);
  }

  return cleaned.slice(0, MAX_TERMS_PER_FIELD);
}

export function normalizePhoneList(value, warnings) {
  const base = normalizeCsv(value)
    .map((item) => item.replace(/\D+/g, ""))
    .filter(Boolean)
    .map((item) => item.slice(0, 15));

  const uniquePhones = unique(base);
  if (uniquePhones.length > MAX_TERMS_PER_FIELD) {
    warnings.push(`Phone numbers: only first ${MAX_TERMS_PER_FIELD} entries were used.`);
  }

  return uniquePhones.slice(0, MAX_TERMS_PER_FIELD);
}

export function normalizeDobList(value, warnings) {
  const raw = normalizeCsv(value)
    .map((item) => item.replace(/\D+/g, ""))
    .filter(Boolean);

  const cleaned = unique(raw.filter((item) => item.length >= 4 && item.length <= 8));

  if (raw.length !== cleaned.length) {
    warnings.push("DOB values must be 4 to 8 digits after cleanup; invalid entries were skipped.");
  }

  if (cleaned.length > MAX_TERMS_PER_FIELD) {
    warnings.push(`DOB entries: only first ${MAX_TERMS_PER_FIELD} values were used.`);
  }

  return cleaned.slice(0, MAX_TERMS_PER_FIELD);
}

export function sanitizeSize(value) {
  const parsed = Number(value);
  const requestedRaw = Number.isFinite(parsed) ? Math.trunc(parsed) : DEFAULT_LIST_SIZE;
  const requestedSize = clampNumber(requestedRaw, MIN_LIMIT, HARD_LIMIT);

  return { requestedRaw, requestedSize };
}
