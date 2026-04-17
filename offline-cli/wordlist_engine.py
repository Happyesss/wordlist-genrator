from __future__ import annotations

import random
from typing import Dict, List, Sequence, Set

from wordlist_utils import (
    build_forms,
    clamp,
    dob_variants,
    parse_dob,
    parse_field,
    parse_phones,
    seed_tokens,
    unique,
)

HARD_LIMIT = 1_000_000
MIN_LIMIT = 100
DEFAULT_LIST_SIZE = 2500
MAX_TOTAL_NAMES = 45
YEAR_START = 1900
YEAR_END = 2100

COMMON_SUFFIXES = [
    "123", "1234", "12345", "786", "007", "2023", "2024", "2025", "456", "789"
]

DEFAULT_ROUTERS = [
    "jiofiber@123", "jiofiber123", "jio@123", "jio123",
    "airtel@1234", "airtel1234", "airtel@123", "airtel123",
    "tp-link123", "tplink123", "tp-link@123", "tplink@123",
    "tp-link1234", "tplink1234", "tp-link@1234", "tplink@1234"
]

def add_with_forms(candidates: Set[str], base: str, include_leet: bool) -> None:
    for item in build_forms(base, include_leet=include_leet):
        candidates.add(item)
        candidates.add(f"@{item}")
        candidates.add(f"#{item}")
        candidates.add(f"!{item}")


def add_with_suffixes(candidates: Set[str], base: str, suffixes: Sequence[str], include_leet: bool) -> None:
    for form in build_forms(base, include_leet=include_leet):
        candidates.add(form)
        for suffix in suffixes:
            candidates.add(f"{form}{suffix}")
            candidates.add(f"{form}@{suffix}")
            candidates.add(f"{form}#{suffix}")
            candidates.add(f"{form}!{suffix}")
            candidates.add(f"{form}{suffix}{suffix}")


def add_year_combos(candidates: Set[str], base: str, include_leet: bool) -> None:
    for form in build_forms(base, include_leet=include_leet):
        for year in range(YEAR_START, YEAR_END + 1):
            candidates.add(f"{form}{year}")
            candidates.add(f"{form}@{year}")
            candidates.add(f"{form}#{year}")
            candidates.add(f"{form}!{year}")


def add_router_defaults(candidates: Set[str], include_leet: bool) -> None:
    for router in DEFAULT_ROUTERS:
        add_with_forms(candidates, router, include_leet=include_leet)
        candidates.add(router.replace("@", "#"))
        candidates.add(router.replace("@", "!"))
        candidates.add(router.replace("tp-link", "tplink"))


def build_random_suffixes(count: int, seed: int | None) -> List[str]:
    rng = random.Random(seed)
    values: Set[str] = set()
    capped = clamp(count, 0, 600)
    while len(values) < capped:
        values.add(str(rng.randint(1, 999999)))
    return list(values)


def top_up_candidates(
    candidates: Set[str], desired_size: int, bases: Sequence[str], seed: int | None, include_leet: bool
) -> int:
    if len(candidates) >= desired_size:
        return 0

    flattened_bases = seed_tokens(bases)
    form_pool: List[str] = []
    for base in flattened_bases:
        form_pool.extend(build_forms(base, include_leet=include_leet))

    form_pool = unique(form_pool)
    if not form_pool:
        return 0

    rng = random.Random(seed)
    before = len(candidates)
    max_attempts = max(7000, desired_size * 10)
    attempts = 0

    while len(candidates) < desired_size and attempts < max_attempts:
        base = form_pool[attempts % len(form_pool)]
        friend = form_pool[(attempts * 3 + 7) % len(form_pool)]

        n2 = rng.randint(10, 99)
        n4 = rng.randint(1000, 9999)
        n6 = rng.randint(100000, 999999)
        yy = rng.randint(70, 30) if False else rng.randint(70, 99)

        candidates.add(f"{base}{n4}")
        candidates.add(f"{base}@{n4}")
        candidates.add(f"{base}#{n4}")
        candidates.add(f"{base}!{n4}")
        candidates.add(f"{n4}{base}")

        candidates.add(f"{base}{friend}{n2}")
        candidates.add(f"{base}@{friend}{n4}")
        candidates.add(f"{base}.{friend}{n2}")
        candidates.add(f"{base}_{friend}{n2}")

        candidates.add(f"{base.replace('a', '@')}{n4}")
        candidates.add(f"{base.replace('i', '!')}{n2}{n2}")
        candidates.add(f"{base.replace('o', '0')}{yy}")
        candidates.add(f"{friend.replace('s', '$')}{n6}")

        if attempts % 2 == 0:
            candidates.add(f"{base}@{friend}@{n2}")
            candidates.add(f"{base}#{friend}#{n2}")
            candidates.add(f"{base}!{friend}!{n2}")

        attempts += 1

    return len(candidates) - before


def stage(msg: str, quiet: bool, printer) -> None:
    if quiet:
        return
    printer(f"[cyan]>>[/cyan] {msg}")


def generate_wordlist(config: Dict[str, object], quiet: bool, printer) -> Dict[str, object]:
    warnings: List[str] = []

    owners = parse_field(str(config["owners"]), "Owner names", warnings)
    last_names = parse_field(str(config["last_names"]), "Last names", warnings)
    family = parse_field(str(config["family"]), "Family names", warnings)
    pets = parse_field(str(config["pets"]), "Pet names", warnings)
    locations = parse_field(str(config["locations"]), "Locations", warnings)
    interests = parse_field(str(config["interests"]), "Interests", warnings)
    phones = parse_phones(str(config["phones"]), warnings)
    exact_dob = parse_dob(str(config["dob"]), warnings)

    include_router_defaults = bool(config["include_router_defaults"])
    include_years = bool(config["include_years"])
    include_random = bool(config["include_random"])
    include_leet = bool(config.get("include_leet", True))
    random_count = int(config["random_count"])
    desired_raw = int(config["size"])

    desired_size = clamp(desired_raw, MIN_LIMIT, HARD_LIMIT)
    if desired_raw < MIN_LIMIT:
        warnings.append(f"Requested size below minimum and was raised to {MIN_LIMIT}.")
    if desired_raw > HARD_LIMIT:
        warnings.append(f"Requested size exceeded hard limit and was capped at {HARD_LIMIT}.")

    names = unique([*owners, *last_names, *family, *pets])[:MAX_TOTAL_NAMES]
    if len(names) < (len(owners) + len(last_names) + len(family) + len(pets)):
        warnings.append(f"Names were trimmed to first {MAX_TOTAL_NAMES} entries for performance.")
    if not names:
        warnings.append("No name tokens provided; generation will use only supplied non-name fields.")

    base_names = names
    base_locations = locations
    base_interests = interests
    dob_list = unique(v for dob in exact_dob for v in dob_variants(dob))
    all_phones = phones

    random_suffixes = build_random_suffixes(random_count, config.get("seed")) if include_random else []
    suffix_pool = unique([*COMMON_SUFFIXES, *random_suffixes]) if include_random else COMMON_SUFFIXES

    candidates: Set[str] = set()

    stage("Stage 1/9: base patterns", quiet, printer)
    for name in base_names:
        add_with_suffixes(candidates, name, suffix_pool, include_leet=include_leet)
        if include_years:
            add_year_combos(candidates, name, include_leet=include_leet)
        for dob in dob_list:
            add_with_forms(candidates, f"{name}{dob}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}@{dob}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}#{dob}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}!{dob}", include_leet=include_leet)

    stage("Stage 2/9: name + location/interest", quiet, printer)
    for name in base_names:
        for loc in base_locations:
            add_with_forms(candidates, f"{name}{loc}", include_leet=include_leet)
            add_with_forms(candidates, f"{loc}{name}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}@{loc}", include_leet=include_leet)
            add_with_forms(candidates, f"{loc}@{name}", include_leet=include_leet)
            add_with_suffixes(candidates, f"{name}{loc}", ["123", "2024", "786"], include_leet=include_leet)
        for interest in base_interests:
            add_with_forms(candidates, f"{name}{interest}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}@{interest}", include_leet=include_leet)
            add_with_suffixes(candidates, f"{name}{interest}", ["123", "2024", "786"], include_leet=include_leet)

    stage("Stage 3/9: pair combinations", quiet, printer)
    for i, a in enumerate(base_names):
        for j, b in enumerate(base_names):
            if i == j:
                continue
            add_with_forms(candidates, f"{a}{b}", include_leet=include_leet)
            add_with_forms(candidates, f"{a}_{b}", include_leet=include_leet)
            add_with_forms(candidates, f"{a}.{b}", include_leet=include_leet)
            add_with_forms(candidates, f"{a}@{b}", include_leet=include_leet)
            add_with_suffixes(candidates, f"{a}{b}", ["123", "2024", "786", "007"], include_leet=include_leet)

    stage("Stage 4/9: location + interest patterns", quiet, printer)
    for loc in base_locations:
        add_with_suffixes(candidates, loc, suffix_pool, include_leet=include_leet)
    for interest in base_interests:
        add_with_suffixes(candidates, interest, suffix_pool, include_leet=include_leet)

    stage("Stage 5/9: phone patterns", quiet, printer)
    for phone in all_phones:
        candidates.add(phone)
        for name in base_names:
            add_with_forms(candidates, f"{name}{phone}", include_leet=include_leet)
            add_with_forms(candidates, f"{phone}{name}", include_leet=include_leet)
            add_with_forms(candidates, f"{name}@{phone}", include_leet=include_leet)

    stage("Stage 6/9: symbol swaps", quiet, printer)
    for name in base_names:
        add_with_forms(candidates, name.replace("a", "@"), include_leet=include_leet)
        add_with_forms(candidates, name.replace("i", "!"), include_leet=include_leet)
        add_with_forms(candidates, name.replace("o", "0"), include_leet=include_leet)
        add_with_forms(candidates, name.replace("s", "$"), include_leet=include_leet)

    stage("Stage 7/9: router defaults", quiet, printer)
    if include_router_defaults:
        add_router_defaults(candidates, include_leet=include_leet)

    stage("Stage 8/9: repeated name patterns", quiet, printer)
    for name in base_names:
        add_with_forms(candidates, f"{name}{name}", include_leet=include_leet)
        add_with_forms(candidates, f"{name}123{name}", include_leet=include_leet)
        add_with_forms(candidates, f"{name}@123{name}", include_leet=include_leet)
        add_with_suffixes(candidates, f"{name}{name}", ["123", "786", "2024"], include_leet=include_leet)

    stage("Top-up: expanding candidate space", quiet, printer)
    top_up_added = top_up_candidates(
        candidates,
        desired_size,
        [*base_names, *base_locations, *base_interests, *dob_list],
        config.get("seed"),
        include_leet=include_leet,
    )
    if top_up_added > 0:
        warnings.append(f"Top-up added {top_up_added} extra pattern candidates.")
    elif desired_size > len(candidates):
        warnings.append("Could not fully reach requested size without adding non-target generic seeds.")

    unique_passwords = sorted((pwd for pwd in candidates if pwd), key=lambda value: (len(value), value))
    total_unique = len(unique_passwords)
    final_list = unique_passwords[:desired_size]

    return {
        "passwords": final_list,
        "generated_count": len(final_list),
        "requested_raw": desired_raw,
        "requested_size": desired_size,
        "hard_limit": HARD_LIMIT,
        "total_unique": total_unique,
        "clipped_by_limit": desired_raw > HARD_LIMIT,
        "clipped_by_candidates": desired_size > total_unique,
        "warnings": warnings,
    }
