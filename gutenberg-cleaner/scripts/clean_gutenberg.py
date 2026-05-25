#!/usr/bin/env python3
"""
clean_gutenberg.py — Clean Project Gutenberg ebook exports to plain markdown.

Usage:
    python3 clean_gutenberg.py <file_or_directory> [--dry-run]

If a directory is given, every .md and .txt file inside it is processed.
--dry-run prints a summary of changes without writing any files.
"""

import os
import re
import sys


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_roman_numeral_only(s: str) -> bool:
    """Return True if s is solely a Roman numeral (optionally with a period)."""
    return bool(re.fullmatch(r'[IVXLCDM]+\.?', s.strip()))


def skip_blanks(lines: list[str], start: int) -> int:
    """Return index of next non-blank line at or after start."""
    j = start
    while j < len(lines) and lines[j].strip() == '':
        j += 1
    return j


# ── Step 1: Strip Gutenberg boilerplate ──────────────────────────────────────

START_RE = re.compile(
    r'^\\\*\\\*\\\*\s+START OF THE PROJECT GUTENBERG EBOOK',
    re.IGNORECASE,
)
END_RE = re.compile(
    r'^\\\*\\\*\\\*\s+END OF THE PROJECT GUTENBERG EBOOK',
    re.IGNORECASE,
)

# Plain-text variant (no backslash escaping, e.g. raw .txt exports)
START_RE_PLAIN = re.compile(
    r'^\*{3}\s+START OF THE PROJECT GUTENBERG EBOOK',
    re.IGNORECASE,
)
END_RE_PLAIN = re.compile(
    r'^\*{3}\s+END OF THE PROJECT GUTENBERG EBOOK',
    re.IGNORECASE,
)


def strip_boilerplate(lines: list[str]) -> tuple[list[str], bool]:
    """Remove everything before the START marker and from the END marker on.

    Returns (new_lines, changed).
    If no markers are found the original list is returned unchanged.
    """
    start_idx = end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if start_idx is None and (
            START_RE.match(stripped) or START_RE_PLAIN.match(stripped)
        ):
            start_idx = i
        elif start_idx is not None and (
            END_RE.match(stripped) or END_RE_PLAIN.match(stripped)
        ):
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        return lines, False

    new_lines = lines[start_idx + 1 : end_idx]

    # Drop leading blank lines
    while new_lines and new_lines[0].strip() == '':
        new_lines.pop(0)

    return new_lines, True


# ── Step 2: Normalise chapter headings ───────────────────────────────────────

# Matches: ## ****CHAPTER X** or ## ****CHAPTER X  (Winnie-the-Pooh, Dracula, Babbitt style)
ASTERISK_CHAPTER_RE = re.compile(
    r'^(#{1,3})\s+\*{2,4}((?:CHAPTER|PART|BOOK)\s+\S+)\*{0,2}\s*$'
)

# Matches: ### ****DESCRIPTIVE TITLE  (French Lupin style, named chapters)
ASTERISK_HEADING_RE = re.compile(r'^(#{1,3})\s+\*{2,4}(.+)$')

# Matches chapter/part/book headings worth combining with a following title
# e.g.  ## CHAPTER XIV.   ## Chapter IV   ## PART ONE
CHAPTER_HEADING_RE = re.compile(
    r'^(#{1,3})\s+((?:CHAPTER|Chapter|PART|Part)\s+\S+\.?)\s*$'
)

# Matches a bare  # CHAPTER  with the number on the next line (Sun Also Rises)
BARE_CHAPTER_RE = re.compile(r'^#\s+CHAPTER\s*$')

# Matches isolated plain-text section markers: BOOK I / PART ONE etc.
PLAIN_SECTION_RE = re.compile(r'^(BOOK|PART)\s+\S+\s*$')


def _is_plain_title(candidate: str, next_line: str) -> bool:
    """Heuristic: is candidate a chapter title rather than the first prose line?

    A title is:
    - Short (≤ 80 chars)
    - Isolated: followed immediately by a blank line
    - Contains at least one letter (not a markdown separator like ****)
    - Does not start with markdown formatting characters (* _ ` [)
    - Does not start with a lowercase letter
    - Looks title-like: no more than 40 % of its words are lowercase
      (prose sentences have many lowercase words; titles mostly use caps or
      Title Case, possibly with a few small prepositions / articles)
    """
    if not candidate:
        return False
    if candidate.startswith('#'):
        return False
    # Must be followed immediately by a blank line
    if next_line.strip() != '':
        return False
    # Strict length limit
    if len(candidate) > 80:
        return False
    # Must contain at least one letter (exclude pure-symbol separators: **** --- etc.)
    if not re.search(r'[A-Za-z]', candidate):
        return False
    # Must not start with markdown inline formatting
    if candidate[0] in ('*', '_', '`', '['):
        return False
    # First alphabetic character must be uppercase
    first_alpha = re.search(r'[A-Za-z]', candidate)
    if first_alpha and first_alpha.group().islower():
        return False
    # Word-case ratio: prose has many lowercase words; titles mostly don't
    words = re.findall(r'[A-Za-z]+', candidate)
    if words:
        lowercase_count = sum(1 for w in words if w[0].islower())
        if lowercase_count / len(words) > 0.40:
            return False
    return True


def normalise_headings(lines: list[str]) -> tuple[list[str], int]:
    """Apply all heading-normalisation rules.

    Returns (new_lines, number_of_changes).
    """
    result: list[str] = []
    changes = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── Rule A: ## ****CHAPTER X  +  optional ### DESCRIPTIVE SUBTITLE
        m = ASTERISK_CHAPTER_RE.match(line)
        if m:
            hashes, chapter_part = m.group(1), m.group(2).strip()
            j = skip_blanks(lines, i + 1)
            # Look for a ### subtitle that is descriptive (not a bare roman numeral)
            if (
                j < len(lines)
                and re.match(r'^###\s+', lines[j])
                and not is_roman_numeral_only(lines[j][4:].strip())
            ):
                subtitle = lines[j][4:].strip()
                result.append(f"{hashes} {chapter_part}: {subtitle}")
                i = j + 1
            else:
                result.append(f"{hashes} {chapter_part}")
                i += 1
            changes += 1
            continue

        # ── Rule B: ### ****DESCRIPTIVE TITLE  (named chapter, no number)
        m = ASTERISK_HEADING_RE.match(line)
        if m:
            hashes = m.group(1)
            # Strip leading AND trailing asterisks from the captured content
            title = re.sub(r'\*+$', '', m.group(2)).strip()
            result.append(f"{hashes} {title}")
            i += 1
            changes += 1
            continue

        # ── Rule C: ## CHAPTER X  +  plain-text title on next isolated line
        m = CHAPTER_HEADING_RE.match(line)
        if m:
            hashes, chapter_part = m.group(1), m.group(2).strip()
            j = skip_blanks(lines, i + 1)
            after_candidate = lines[j + 1] if j + 1 < len(lines) else ''
            if j < len(lines) and _is_plain_title(lines[j].strip(), after_candidate):
                candidate = lines[j].strip()
                # Strip trailing period from chapter number before the colon
                clean_chapter = chapter_part.rstrip('.')
                result.append(f"{hashes} {clean_chapter}: {candidate}")
                i = j + 1
                changes += 1
                continue
            # No plain-text title — emit as-is (already clean, no asterisks)
            result.append(line)
            i += 1
            continue

        # ── Rule D: # CHAPTER  followed by a bare number on the next line
        if BARE_CHAPTER_RE.match(line):
            j = skip_blanks(lines, i + 1)
            if j < len(lines) and re.fullmatch(r'\d+', lines[j].strip()):
                result.append(f"## CHAPTER {lines[j].strip()}")
                i = j + 1
                changes += 1
                continue

        # ── Rule E: isolated plain-text BOOK/PART markers  →  ## heading
        if PLAIN_SECTION_RE.match(line.strip()):
            # Only promote if the line is truly standalone (neighbours are blank/separator)
            prev_blank = (i == 0 or lines[i - 1].strip() in ('', '* * *'))
            next_blank = (
                i + 1 >= len(lines) or lines[i + 1].strip() in ('', '* * *')
            )
            if prev_blank and next_blank:
                result.append(f"## {line.strip()}")
                i += 1
                changes += 1
                continue

        result.append(line)
        i += 1

    return result, changes


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_file(path: str, dry_run: bool = False) -> str:
    """Process a single file. Returns a human-readable status line."""
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()

    lines = original.splitlines(keepends=True)

    # Step 1: boilerplate
    lines, stripped = strip_boilerplate(lines)

    # Step 2: headings
    lines, heading_changes = normalise_headings(lines)

    new_content = ''.join(lines)

    changed = stripped or heading_changes > 0 or new_content != original
    if not changed:
        return f"  unchanged  {os.path.basename(path)}"

    summary = []
    if stripped:
        summary.append("boilerplate stripped")
    if heading_changes:
        summary.append(f"{heading_changes} heading(s) normalised")

    if not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        verb = "modified"
    else:
        verb = "would modify"

    return f"  {verb}    {os.path.basename(path)}  ({', '.join(summary)})"


def main() -> None:
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    paths = [a for a in args if not a.startswith('--')]

    if not paths:
        print(__doc__)
        sys.exit(1)

    targets: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            for fname in sorted(os.listdir(path)):
                if fname.endswith(('.md', '.txt')):
                    targets.append(os.path.join(path, fname))
        elif os.path.isfile(path):
            targets.append(path)
        else:
            print(f"Not found: {path}", file=sys.stderr)

    if not targets:
        print("No .md or .txt files found.")
        sys.exit(0)

    print(f"{'DRY RUN — ' if dry_run else ''}Processing {len(targets)} file(s):\n")
    for target in targets:
        print(process_file(target, dry_run=dry_run))


if __name__ == '__main__':
    main()
