from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set

MAX_TERMS_PER_FIELD = 30
MAX_TOKEN_LENGTH = 32

LEET_MAP = {
    "a": ["a", "@", "4"],
    "e": ["e", "3"],
    "i": ["i", "1", "!"],
    "o": ["o", "0"],
    "s": ["s", "$", "5"],
    "t": ["t", "7"],
    "g": ["g", "9"],
}


def unique(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def sanitize_token(token: str) -> str:
    if not token:
        return ""
    compact = re.sub(r"\s+", "", token)
    compact = re.sub(r"[^a-zA-Z0-9@._#$!-]", "", compact)
    return compact[:MAX_TOKEN_LENGTH]


def case_forms(value: str) -> List[str]:
    safe = sanitize_token(value)
    if not safe:
        return []
    lowered = safe.lower()
    capped = lowered[0].upper() + lowered[1:] if lowered else lowered
    uppered = safe.upper()
    return unique([lowered, capped, uppered])


def leet_variants(value: str, max_variants: int = 48) -> List[str]:
    base = sanitize_token(value).lower()
    if not base:
        return []

    variants: Set[str] = {base}
    for idx, ch in enumerate(base):
        substitutions = LEET_MAP.get(ch)
        if not substitutions:
            continue

        snapshot = list(variants)
        for candidate in snapshot:
            for replacement in substitutions:
                mutated = candidate[:idx] + replacement + candidate[idx + 1 :]
                variants.add(mutated)
                if len(variants) >= max_variants:
                    return list(variants)

    return list(variants)


def build_forms(value: str, include_leet: bool = True) -> List[str]:
    forms: List[str] = []
    for cased in case_forms(value):
        forms.append(cased)
        if include_leet:
            forms.extend(leet_variants(cased))

    expanded: List[str] = []
    for token in unique(forms):
        expanded.extend(case_forms(token))

    return unique(expanded)


def parse_csv(value: str) -> List[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def parse_field(value: str, label: str, warnings: List[str]) -> List[str]:
    cleaned = unique(sanitize_token(part) for part in parse_csv(value))
    cleaned = [x for x in cleaned if x]
    if len(cleaned) > MAX_TERMS_PER_FIELD:
        warnings.append(f"{label}: only first {MAX_TERMS_PER_FIELD} entries were used.")
    return cleaned[:MAX_TERMS_PER_FIELD]


def parse_phones(value: str, warnings: List[str]) -> List[str]:
    phones = []
    for token in parse_csv(value):
        digits = re.sub(r"\D+", "", token)
        if digits:
            phones.append(digits[:15])
    phones = unique(phones)
    if len(phones) > MAX_TERMS_PER_FIELD:
        warnings.append(f"Phone numbers: only first {MAX_TERMS_PER_FIELD} entries were used.")
    return phones[:MAX_TERMS_PER_FIELD]


def parse_dob(value: str, warnings: List[str]) -> List[str]:
    raw = []
    for token in parse_csv(value):
        digits = re.sub(r"\D+", "", token)
        if digits:
            raw.append(digits)
    cleaned = unique([x for x in raw if 4 <= len(x) <= 8])
    if len(raw) != len(cleaned):
        warnings.append("DOB values must be 4 to 8 digits after cleanup; invalid entries were skipped.")
    if len(cleaned) > MAX_TERMS_PER_FIELD:
        warnings.append(f"DOB entries: only first {MAX_TERMS_PER_FIELD} values were used.")
    return cleaned[:MAX_TERMS_PER_FIELD]


def dob_variants(dob_token: str) -> List[str]:
    cleaned = re.sub(r"\D+", "", str(dob_token or ""))
    variants: Set[str] = set()
    if not cleaned:
        return []

    variants.add(cleaned)

    if len(cleaned) == 8:
        dd = cleaned[0:2]
        mm = cleaned[2:4]
        yyyy = cleaned[4:8]
        variants.add(f"{dd}{mm}{yyyy}")
        variants.add(f"{dd}{mm}{yyyy[2:]}")
        variants.add(f"{yyyy}{mm}{dd}")
        variants.add(yyyy)
    elif len(cleaned) == 6:
        variants.add(cleaned[0:4])
        variants.add(cleaned[2:6])

    return list(variants)


def seed_tokens(*groups: Sequence[str]) -> List[str]:
    tokens: List[str] = []
    for group in groups:
        for value in group:
            safe = sanitize_token(value)
            if safe:
                tokens.append(safe)
    return unique(tokens)
