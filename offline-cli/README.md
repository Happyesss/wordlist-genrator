# Offline Terminal CLI

This folder contains a standalone offline CLI version of the wordlist generator.

## File

- `wordlist_cli.py`: main CLI program

## Requirements

- Python 3.9+
- No third-party dependencies

## Quick Start

```bash
cd offline-cli
python3 wordlist_cli.py -help
```

## Kali Install From Repo Link (Global Command)

Install once with your repo link and use it anywhere:

pipx install "git+https://github.com/Happyesss/wordlist-genrator.git"

Then run from any terminal path:

wordlist-cli -i

To upgrade to latest CLI UI later:

```bash
pipx reinstall "git+https://github.com/Happyesss/wordlist-genrator.git"
```

Quick update command (recommended):

```bash
pipx upgrade --force wordlist-cli
```

If `pipx` is missing:

sudo apt update && sudo apt install -y pipx
pipx ensurepath

## Example Commands

```bash
python3 wordlist_cli.py --owners "alex,rohan" --phones "9876543210" --size 50000
python3 wordlist_cli.py --owners "admin" --dob "2001-01-30" --include-random --random-count 40
python3 wordlist_cli.py --owners "test" --no-years --no-router-defaults --output out/assessment.txt
```

## Help

The CLI supports all of these help forms:

- `-help`
- `-h`
- `--help`
- `-i` interactive wizard (Cupp-style flow)

Help output includes:

- all input flags
- all generation rule flags
- output/UX flags
- usage examples

## Notes

- For authorized security testing only.
- Hard limit is 1,000,000 candidates.
- Output defaults to `wordlist.txt` in the current directory.
