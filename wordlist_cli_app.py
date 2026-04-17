#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from wordlist_engine import DEFAULT_LIST_SIZE, HARD_LIMIT, MIN_LIMIT, generate_wordlist
from wordlist_utils import clamp

console = Console()


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
                subtitle="v1.3.0",
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
            subtitle="v1.3.0",
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
    random_count = prompt_int("Random numeric count", args.random_count, 0, 600)
    include_years = prompt_yes_no("Include year combinations (1900-2100)", args.include_years)
    include_router_defaults = prompt_yes_no("Include router default patterns", args.include_router_defaults)
    include_leet = prompt_yes_no("Include leet/symbol swaps (a->@, o->0, i->!, s->$)", args.include_leet)

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
        "include_leet": include_leet,
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
    wordlist -i
    wordlist --owners \"alex,rohan\" --phones \"9876543210\" --size 50000
    wordlist --owners \"admin\" --dob \"2001-01-30\" --include-random --random-count 80
    wordlist --owners \"nish\" --include-leet --size 80000

Install from repo link (Kali):
  pipx install \"git+https://github.com/Happyesss/wordlist-genrator.git\"

Notes:
  - This tool is for authorized security testing only.
  - Hard limit is 1,000,000 candidates.
  - Use -help, -h, or --help to show full help.
"""

    parser = argparse.ArgumentParser(
        prog="wordlist",
        description="Offline WiFi Wordlist Generator (terminal edition)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
        add_help=False,
    )

    parser.add_argument("-h", "--help", "-help", action="help", help="Show this complete help message and exit.")
    parser.add_argument("--version", action="version", version="wordlist 1.3.0")
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
    rules.add_argument("--random-count", type=int, default=48, help="Number of random suffix values (0 to 600).")
    rules.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducible random suffixes.")
    rules.add_argument("--include-years", dest="include_years", action="store_true", help="Include 1900-2100 year combinations.")
    rules.add_argument("--no-years", dest="include_years", action="store_false", help="Disable year combinations.")
    rules.set_defaults(include_years=True)
    rules.add_argument("--include-router-defaults", dest="include_router_defaults", action="store_true", help="Include router/ISP default-like passwords.")
    rules.add_argument("--no-router-defaults", dest="include_router_defaults", action="store_false", help="Disable router/ISP defaults.")
    rules.set_defaults(include_router_defaults=False)
    rules.add_argument("--include-leet", dest="include_leet", action="store_true", help="Enable symbol swaps and leet forms (a->@, o->0, i->!, s->$).")
    rules.add_argument("--no-leet", dest="include_leet", action="store_false", help="Disable leet/symbol substitutions.")
    rules.set_defaults(include_leet=True)

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


def nullcontext():
    class _NullContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    return _NullContext()


def execute(config: Dict[str, object]) -> int:
    quiet = bool(config["quiet"])

    if config.get("show_config") and not quiet:
        show_runtime_config(config)

    with console.status("[cyan]Generating wordlist...[/cyan]", spinner="dots") if not quiet else nullcontext():
        result = generate_wordlist(config, quiet=quiet, printer=console.print)

    output_path = Path(str(config["output"])).expanduser().resolve()
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
            "random_count": clamp(args.random_count, 0, 600),
            "seed": args.seed,
            "include_years": args.include_years,
            "include_router_defaults": args.include_router_defaults,
            "include_leet": args.include_leet,
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
