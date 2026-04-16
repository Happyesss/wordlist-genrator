#!/usr/bin/env python3
"""Offline terminal wordlist generator CLI.

This module powers both:
- installed command: wordlist-cli
- repo script wrapper: offline-cli/wordlist_cli.py
"""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()

HARD_LIMIT = 1_000_000
MIN_LIMIT = 100
DEFAULT_LIST_SIZE = 2500
MAX_TERMS_PER_FIELD = 30
MAX_TOTAL_NAMES = 45
MAX_TOKEN_LENGTH = 32
YEAR_START = 1900
YEAR_END = 2100

COMMON_SUFFIXES = [
    "123", "1234", "12345", "786", "007", "2023", "2024", "2025", "456", "789"
]

HINGLISH_WORDS = [
    "meraWifi", "ghar", "pyaar", "dil", "desi", "gharwali", "mohabbat",
    "meraGhar", "meraDil", "meraIndia", "wifi", "home", "family", "welcome"
]

DEFAULT_ROUTERS = [
    "jiofiber@123", "jiofiber123", "jio@123", "jio123",
    "airtel@1234", "airtel1234", "airtel@123", "airtel123",
    "tp-link123", "tplink123", "tp-link@123", "tplink@123",
    "tp-link1234", "tplink1234", "tp-link@1234", "tplink@1234"
]

DEFAULT_PHONE_PATTERNS = [
    "9810012345", "9811122334", "9812345678", "9912345678",
    "9812301234", "9812340000", "9810012346", "9810012347"
]


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
    compact = re.sub(r"[^a-zA-Z0-9@._-]", "", compact)
    return compact[:MAX_TOKEN_LENGTH]


def case_forms(value: str) -> List[str]:
    safe = sanitize_token(value)
    if not safe:
        return []
    lowered = safe.lower()
    capped = lowered[0].upper() + lowered[1:] if lowered else lowered
    uppered = safe.upper()
    return unique([lowered, capped, uppered])


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


def add_with_forms(candidates: Set[str], base: str) -> None:
    for item in case_forms(base):
        candidates.add(item)


def add_with_suffixes(candidates: Set[str], base: str, suffixes: Sequence[str]) -> None:
    for form in case_forms(base):
        candidates.add(form)
        for suffix in suffixes:
            candidates.add(f"{form}{suffix}")
            candidates.add(f"{form}@{suffix}")
            candidates.add(f"{form}#{suffix}")
            candidates.add(f"{form}!{suffix}")
            candidates.add(f"{form}{suffix}{suffix}")


def add_year_combos(candidates: Set[str], base: str) -> None:
    for form in case_forms(base):
        for year in range(YEAR_START, YEAR_END + 1):
            candidates.add(f"{form}{year}")
            candidates.add(f"{form}@{year}")
            candidates.add(f"{form}#{year}")
            candidates.add(f"{form}!{year}")


def add_router_defaults(candidates: Set[str]) -> None:
    for router in DEFAULT_ROUTERS:
        add_with_forms(candidates, router)
        candidates.add(router.replace("@", "#"))
        candidates.add(router.replace("@", "!"))
        candidates.add(router.replace("tp-link", "tplink"))


def build_random_suffixes(count: int, seed: int | None) -> List[str]:
    rng = random.Random(seed)
    values: Set[str] = set()
    capped = clamp(count, 0, 200)
    while len(values) < capped:
        values.add(str(rng.randint(1, 99999)))
    return list(values)


def stage(msg: str, quiet: bool) -> None:
    if quiet:
        return
    console.print(f"[cyan]>>[/cyan] {msg}")


def generate_wordlist(config: Dict[str, object], quiet: bool) -> Dict[str, object]:
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
        warnings.append("No names provided; using fallback base names.")

    base_names = names if names else ["owner", "admin", "guest"]
    base_locations = locations if locations else ["city", "home"]
    base_interests = interests if interests else ["wifi", "home"]
    dob_list = unique(v for dob in exact_dob for v in dob_variants(dob))
    all_phones = unique([*DEFAULT_PHONE_PATTERNS, *phones])

    random_suffixes = build_random_suffixes(random_count, config.get("seed")) if include_random else []
    suffix_pool = unique([*COMMON_SUFFIXES, *random_suffixes]) if include_random else COMMON_SUFFIXES

    candidates: Set[str] = set()

    stage("Stage 1/8: base patterns", quiet)
    for name in base_names:
        add_with_suffixes(candidates, name, suffix_pool)
        if include_years:
            add_year_combos(candidates, name)
        for dob in dob_list:
            add_with_forms(candidates, f"{name}{dob}")
            add_with_forms(candidates, f"{name}@{dob}")
            add_with_forms(candidates, f"{name}#{dob}")
            add_with_forms(candidates, f"{name}!{dob}")

    stage("Stage 2/8: name + location/interest", quiet)
    for name in base_names:
        for loc in base_locations:
            add_with_forms(candidates, f"{name}{loc}")
            add_with_forms(candidates, f"{loc}{name}")
            add_with_forms(candidates, f"{name}@{loc}")
            add_with_forms(candidates, f"{loc}@{name}")
            add_with_suffixes(candidates, f"{name}{loc}", ["123", "2024", "786"])
        for interest in base_interests:
            add_with_forms(candidates, f"{name}{interest}")
            add_with_forms(candidates, f"{name}@{interest}")
            add_with_suffixes(candidates, f"{name}{interest}", ["123", "2024", "786"])

    stage("Stage 3/8: pair combinations", quiet)
    for i, a in enumerate(base_names):
        for j, b in enumerate(base_names):
            if i == j:
                continue
            add_with_forms(candidates, f"{a}{b}")
            add_with_forms(candidates, f"{a}_{b}")
            add_with_forms(candidates, f"{a}.{b}")
            add_with_forms(candidates, f"{a}@{b}")
            add_with_suffixes(candidates, f"{a}{b}", ["123", "2024", "786", "007"])

    stage("Stage 4/8: hinglish defaults", quiet)
    for word in HINGLISH_WORDS:
        add_with_suffixes(candidates, word, ["123", "2024", "2025", "786"])
        add_with_forms(candidates, f"{word}India")
        add_with_forms(candidates, f"{word}Noida")

    stage("Stage 5/8: location + interest patterns", quiet)
    for loc in base_locations:
        add_with_suffixes(candidates, loc, suffix_pool)
    for interest in base_interests:
        add_with_suffixes(candidates, interest, suffix_pool)

    stage("Stage 6/8: phone patterns", quiet)
    for phone in all_phones:
        candidates.add(phone)
        for name in base_names:
            add_with_forms(candidates, f"{name}{phone}")
            add_with_forms(candidates, f"{phone}{name}")
            add_with_forms(candidates, f"{name}@{phone}")

    stage("Stage 7/8: router defaults", quiet)
    if include_router_defaults:
        add_router_defaults(candidates)

    stage("Stage 8/8: repeated name patterns", quiet)
    for name in base_names:
        add_with_forms(candidates, f"{name}{name}")
        add_with_forms(candidates, f"{name}123{name}")
        add_with_forms(candidates, f"{name}@123{name}")
        add_with_suffixes(candidates, f"{name}{name}", ["123", "786", "2024"])

    unique_passwords = [pwd for pwd in candidates if pwd]
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


def print_header() -> None:
    term_width = console.size.width
    logo = r"""
 _       __               ____    _      __ 
| |     / /___  ________/ / /_  (_)____/ /_ 
| | /| / / __ \/ ___/ __  / / / / / ___/ __/
| |/ |/ / /_/ / /  / /_/ / / /_/ (__  ) /_  
|__/|__/\____/_/   \__,_/_/\____/____/\__/  
                                            
   ______                           __            
  / ____/___  ____  ___  _________ / /_____  _____
 / / __/ __ \/ __ \/ _ \/ ___/ __ `/ __/ _ \/ ___/
/ /_/ / /_/ / / / /  __/ /  / /_/ / /_/  __/ /    
\____/\____/_/ /_/\___/_/   \__,_/\__/\___/_/     
"""

    # Large ASCII logo is used on wide terminals only; narrow terminals get a compact header.
    if term_width < 110:
        title = Text("WORDLIST-GENRATOR", style="bold bright_cyan")
        body = Text.assemble(
            title,
            "\n",
            ("Offline WiFi Wordlist Generator", "white"),
            "\n",
            ("Authorized security testing use only", "dim"),
        )
        console.print()
        console.print(
            Panel(
                body,
                border_style="cyan",
                padding=(0, 1),
                subtitle="v1.2.0",
                subtitle_align="right",
                title="terminal mode",
                title_align="left",
            )
        )
        return

    title = Text(logo.strip("\n"), style="bold bright_cyan")
    subtitle = Text("Offline WiFi Wordlist Generator", style="white")
    body = Text.assemble(title, "\n\n", subtitle, "\n", ("Authorized security testing use only", "dim"))

    console.print()
    console.print(
        Panel(
            body,
            border_style="cyan",
            padding=(1, 2),
            subtitle="v1.2.0",
            subtitle_align="right",
            title="terminal mode",
            title_align="left",
        )
    )


def print_interactive_banner() -> None:
    help_lines = (
        "- Press Enter to keep default\n"
        "- Leave text blank to skip a field\n"
        "- Comma-separate multi values (alex,rohan,home)\n"
        "- Type Ctrl+C to cancel"
    )
    console.print(
        Panel(
            help_lines,
            title="interactive wizard (-i)",
            border_style="bright_blue",
            padding=(1, 2),
        )
    )


def prompt_text(label: str, default: str = "") -> str:
    if default:
        return Prompt.ask(label, default=default).strip()
    return Prompt.ask(label, default="").strip()


def prompt_yes_no(label: str, default: bool) -> bool:
    return Confirm.ask(label, default=default)


def prompt_int(label: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        value = IntPrompt.ask(label, default=default)
        if minimum is not None and value < minimum:
            console.print(f"[yellow]Minimum value is {minimum}.[/yellow]")
            continue
        if maximum is not None and value > maximum:
            console.print(f"[yellow]Maximum value is {maximum}.[/yellow]")
            continue
        return value


def show_runtime_config(config: Dict[str, object]) -> None:
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")

    for key, value in config.items():
        if key in {"output", "preview", "stdout", "show_config", "quiet"}:
            continue
        table.add_row(key, str(value))

    console.print(Rule("resolved config", style="cyan"))
    console.print(table)


def build_interactive_config(args: argparse.Namespace) -> Dict[str, object]:
    print_interactive_banner()
    console.print(Rule("profile", style="bright_blue"))

    owners = prompt_text("Owner names (comma-separated)", args.owners)
    last_names = prompt_text("Last names", args.last_names)
    family = prompt_text("Family names", args.family)
    pets = prompt_text("Pet names", args.pets)
    phones = prompt_text("Phone numbers", args.phones)
    locations = prompt_text("Locations", args.locations)
    interests = prompt_text("Interests", args.interests)
    dob = prompt_text("Exact DOB tokens", args.dob)

    console.print(Rule("generation rules", style="bright_blue"))
    size = prompt_int("Desired wordlist size", args.size, MIN_LIMIT, HARD_LIMIT)
    include_random = prompt_yes_no("Include random numeric suffixes", args.include_random)
    random_count = prompt_int("Random numeric count", args.random_count, 0, 200)
    include_years = prompt_yes_no("Include year combinations (1900-2100)", args.include_years)
    include_router_defaults = prompt_yes_no("Include router default patterns", args.include_router_defaults)

    console.print(Rule("output", style="bright_blue"))
    output_default = args.output if args.output else "wordlist.txt"
    output = prompt_text("Output file path", output_default)
    quiet = prompt_yes_no("Quiet mode", args.quiet)
    stdout = prompt_yes_no("Print full list to terminal", args.stdout)
    show_config = prompt_yes_no("Show resolved config", args.show_config)
    preview = prompt_int("Preview first N passwords", args.preview, 0, 200)

    config = {
        "owners": owners,
        "last_names": last_names,
        "family": family,
        "pets": pets,
        "phones": phones,
        "locations": locations,
        "interests": interests,
        "dob": dob,
        "size": size,
        "include_random": include_random,
        "random_count": random_count,
        "seed": args.seed,
        "include_years": include_years,
        "include_router_defaults": include_router_defaults,
        "output": output,
        "preview": preview,
        "stdout": stdout,
        "show_config": show_config,
        "quiet": quiet,
    }

    if not quiet:
        show_runtime_config(config)
        if not Confirm.ask("Start generation now", default=True):
            raise KeyboardInterrupt

    return config


def build_parser() -> argparse.ArgumentParser:
    epilog = """Examples:
  wordlist-cli -i
  wordlist-cli --owners "alex,rohan" --phones "9876543210" --size 50000
  wordlist-cli --owners "admin" --dob "2001-01-30" --include-random --random-count 40
  wordlist-cli --owners "test" --no-years --no-router-defaults --output audit.txt

Install from repo link (Kali):
  pipx install "git+https://github.com/Happyesss/wordlist-genrator.git"

Notes:
  - This tool is for authorized security testing only.
  - Hard limit is 1,000,000 candidates.
  - Use -help, -h, or --help to show full help.
"""

    parser = argparse.ArgumentParser(
        prog="wordlist-cli",
        description="Offline WiFi Wordlist Generator (terminal edition)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
        add_help=False,
    )

    parser.add_argument("-h", "--help", "-help", action="help", help="Show this complete help message and exit.")
    parser.add_argument("--version", action="version", version="wordlist-cli 1.2.0")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch Cupp-style interactive wizard UI.")

    profile = parser.add_argument_group("Target Profile Inputs")
    profile.add_argument("--owners", default="", help="Comma-separated owner/primary names.")
    profile.add_argument("--last-names", default="", help="Comma-separated last names.")
    profile.add_argument("--family", default="", help="Comma-separated family member names.")
    profile.add_argument("--pets", default="", help="Comma-separated pet names.")
    profile.add_argument("--phones", default="", help="Comma-separated phone numbers.")
    profile.add_argument("--locations", default="", help="Comma-separated location/city tokens.")
    profile.add_argument("--interests", default="", help="Comma-separated interest/keyword tokens.")
    profile.add_argument("--dob", default="", help="Comma-separated DOB tokens (e.g. 2001-01-30, 30011999).")

    rules = parser.add_argument_group("Generation Rules")
    rules.add_argument("--size", type=int, default=DEFAULT_LIST_SIZE, help="Requested list size (100 to 1000000).")
    rules.add_argument("--include-random", dest="include_random", action="store_true", help="Enable random numeric suffixes.")
    rules.add_argument("--no-random", dest="include_random", action="store_false", help="Disable random numeric suffixes.")
    rules.set_defaults(include_random=True)
    rules.add_argument("--random-count", type=int, default=24, help="Number of random suffix values (0 to 200).")
    rules.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducible random suffixes.")
    rules.add_argument("--include-years", dest="include_years", action="store_true", help="Include 1900-2100 year combinations.")
    rules.add_argument("--no-years", dest="include_years", action="store_false", help="Disable year combinations.")
    rules.set_defaults(include_years=True)
    rules.add_argument("--include-router-defaults", dest="include_router_defaults", action="store_true", help="Include router/ISP default-like passwords.")
    rules.add_argument("--no-router-defaults", dest="include_router_defaults", action="store_false", help="Disable router/ISP defaults.")
    rules.set_defaults(include_router_defaults=True)

    output = parser.add_argument_group("Output and UX")
    output.add_argument("--output", default="wordlist.txt", help="Output file path for generated passwords.")
    output.add_argument("--preview", type=int, default=20, help="Preview first N generated passwords.")
    output.add_argument("--stdout", action="store_true", help="Print full generated list to stdout.")
    output.add_argument("--show-config", action="store_true", help="Print resolved runtime config before generation.")
    output.add_argument("--quiet", action="store_true", help="Minimal output mode.")

    return parser


def print_summary(result: Dict[str, object], output_path: Path) -> None:
    summary = Table(box=None, show_header=False)
    summary.add_column("k", style="cyan", no_wrap=True)
    summary.add_column("v", style="white", overflow="fold")
    summary.add_row("Output file", str(output_path))
    summary.add_row("Generated count", str(result["generated_count"]))
    summary.add_row("Requested size", f"{result['requested_size']} (raw: {result['requested_raw']})")
    summary.add_row("Unique available", str(result["total_unique"]))
    summary.add_row("Hard limit", str(result["hard_limit"]))
    summary.add_row("Clipped by limit", str(result["clipped_by_limit"]).lower())
    summary.add_row("Clipped by unique", str(result["clipped_by_candidates"]).lower())

    console.print(Rule("generation summary", style="cyan"))
    console.print(summary)

    warnings = result.get("warnings", [])
    if warnings:
        warning_text = "\n".join(f"- {warning}" for warning in warnings)
        console.print(Panel(warning_text, title="warnings", border_style="yellow"))


def print_preview(passwords: Sequence[str], preview_count: int) -> None:
    if preview_count <= 0:
        return

    table = Table(title="preview", header_style="bold cyan")
    table.add_column("#", style="dim", justify="right", width=5)
    table.add_column("candidate", style="white", overflow="fold")

    for idx, pwd in enumerate(passwords[:preview_count], start=1):
        table.add_row(str(idx), pwd)

    console.print(table)


def execute(config: Dict[str, object]) -> int:
    quiet = bool(config["quiet"])
    
    if config.get("show_config") and not quiet:
        show_runtime_config(config)

    with console.status("[cyan]Generating wordlist...[/cyan]", spinner="dots") if not quiet else nullcontext():
        result = generate_wordlist(config, quiet=quiet)

    output_path = Path(str(config["output"]))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(result["passwords"]) + "\n", encoding="utf-8")

    if not quiet:
        print_summary(result, output_path)
        preview = clamp(int(config["preview"]), 0, 200)
        print_preview(result["passwords"], preview)
        console.print("[bold green]Done.[/bold green]")

    if config.get("stdout"):
        for pwd in result["passwords"]:
            console.print(pwd)

    return 0


def nullcontext():
    class _NullContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    return _NullContext()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.quiet:
        print_header()

    try:
        if args.interactive:
            config = build_interactive_config(args)
            return execute(config)

        config: Dict[str, object] = {
            "owners": args.owners,
            "last_names": args.last_names,
            "family": args.family,
            "pets": args.pets,
            "phones": args.phones,
            "locations": args.locations,
            "interests": args.interests,
            "dob": args.dob,
            "size": args.size,
            "include_random": args.include_random,
            "random_count": clamp(args.random_count, 0, 200),
            "seed": args.seed,
            "include_years": args.include_years,
            "include_router_defaults": args.include_router_defaults,
            "output": args.output,
            "preview": args.preview,
            "stdout": args.stdout,
            "show_config": args.show_config,
            "quiet": args.quiet,
        }
        return execute(config)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
