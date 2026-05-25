---
name: gutenberg-cleaner
description: "This skill should be used when the user wants to clean up a Project Gutenberg ebook that has been exported to markdown or plain text. It strips the standard Gutenberg header/footer boilerplate and normalises chapter headings so that chapter numbers and chapter names appear on a single heading line."
category: text-processing
risk: safe
tags: "[gutenberg, markdown, ebook, cleanup, chapter-headings]"
date_added: "2026-05-25"
---

# gutenberg-cleaner

## Purpose

Clean Project Gutenberg ebook exports (`.md` or `.txt`) into consistent, presentation-ready markdown by:

1. Removing the Gutenberg licence header and footer that surrounds the actual text.
2. Normalising chapter headings so that the chapter number and chapter name appear together on one heading line.

## When to Use This Skill

Use this skill when the user:
- Has one or more Gutenberg ebook files in `.md` or `.txt` format and wants to prepare them for use in a presentation, demo, or publication.
- Wants to remove Gutenberg boilerplate while keeping the book text intact.
- Has inconsistently formatted chapter headings across a collection of books and wants them standardised.

## Step 0: Understand the Input

Before running any transformations, read a small portion of the file(s) to confirm:

1. **Boilerplate markers are present** — look for a line matching
   `*** START OF THE PROJECT GUTENBERG EBOOK …` (may have backslash-escaped asterisks in markdown exports: `\*\*\* START OF …`).
2. **The chapter heading style** — use `grep -n "^#"` to list all headings. Common patterns found in Gutenberg exports:

   | Pattern | Example |
   |---------|---------|
   | Heading + `###` subtitle | `## ****CHAPTER I` → `### IN WHICH POOH GOES VISITING` |
   | Heading + plain-text title | `## CHAPTER I.` → `A SHIFTING REEF` (next line, surrounded by blanks) |
   | Heading with stray asterisks | `## ****CHAPTER I**` |
   | Split chapter/number | `# CHAPTER` then `1` on the next non-blank line |
   | Plain-text section markers | `BOOK I` or `PART ONE` as isolated paragraphs |
   | Already combined | `## I. The Arrest of Arsène Lupin` — no action needed |
   | Named chapters only | `## STORY OF THE DOOR` — no action needed |

3. **Edge cases to watch for:**
   - `### I`, `### II` sub-headings that are *section numbers within a chapter* (Babbitt-style) — do **not** combine these with the chapter heading.
   - Epigraphs or quoted verse at the top of a chapter — do **not** fold these into the heading. Only single short title lines (≤ 100 characters, surrounded by blank lines, not starting with a lowercase letter) qualify.
   - Multi-line poems or block quotes following the chapter heading — leave as content.

## Step 1: Strip Gutenberg Boilerplate

Run the bundled script on the file or directory:

```bash
python3 scripts/clean_gutenberg.py <path/to/file_or_directory>
```

Use `--dry-run` first to preview changes without writing:

```bash
python3 scripts/clean_gutenberg.py <path> --dry-run
```

The script removes every line from the beginning of the file up to **and including** the `*** START OF THE PROJECT GUTENBERG EBOOK …` line, and every line from the `*** END OF THE PROJECT GUTENBERG EBOOK …` line to the end of the file. Leading blank lines after the START marker are also trimmed.

**If the markers are absent** (e.g., the file was already stripped, or it is a non-Gutenberg source), the script leaves the file unchanged and reports `unchanged`.

## Step 2: Run Automated Heading Normalisation

The same script applies all heading transformations in a single pass (Step 1 and Step 2 run together). The rules applied, in order, are:

### Rule A — Clean stray asterisks and combine with `###` subtitle

```
## ****CHAPTER I          →   ## CHAPTER I: IN WHICH POOH GOES VISITING
### IN WHICH POOH GOES VISITING
```

The `###` line is consumed and removed. Applied only when the `###` content is a descriptive title, **not** when it is a bare Roman numeral (e.g., `### I` — those are section dividers, not titles).

### Rule B — Clean stray asterisks on named-chapter headings

```
### ****L'ARRESTATION D'ARSÈNE LUPIN   →   ### L'ARRESTATION D'ARSÈNE LUPIN
```

### Rule C — Combine heading with plain-text title on the next line

```
## CHAPTER I.             →   ## CHAPTER I: A SHIFTING REEF
                               (blank line removed)
A SHIFTING REEF
```

Conditions for the plain-text line to qualify as a title:
- Isolated by blank lines on both sides.
- ≤ 100 characters.
- Does not begin with a lowercase letter.
- Is not itself a markdown heading (`#…`).

The trailing period is stripped from the chapter number before the colon (`CHAPTER I.` → `CHAPTER I:`).

### Rule D — Combine split `# CHAPTER` + number

```
# CHAPTER                 →   ## CHAPTER 1
                               (blank lines removed)
1
```

### Rule E — Promote isolated plain-text `BOOK`/`PART` markers to headings

```
BOOK I                    →   ## BOOK I
```

Only applied when the line is preceded and followed by blank lines or `* * *` separators.

## Step 3: Manual Review

After the script runs, quickly verify:

```bash
grep -n "^#" <file> | head -30
```

Check:
- Chapter headings look correct (number + name on one line where expected).
- No stray `****` remain in headings.
- No epigraph or prose paragraph was accidentally folded into a heading.
- Sub-section markers (`### I`, `### II` in Babbitt-style books) are still present and untouched.

Fix any remaining issues manually with targeted edits. Common manual fixes:

- A chapter that has a multi-line quoted epigraph as its "title" — the script will skip it (too long, or not followed by a blank line), but verify visually.
- A book that mixes heading levels inconsistently — adjust `##` ↔ `###` as needed for the specific book.
- Plain `.txt` files where chapter headings were uppercase text rather than markdown `#` headings — convert those to `##` headings by hand or with a targeted script.

## Step 4: Converting Plain `.txt` Files

If the input is a `.txt` file with no markdown formatting, the boilerplate stripping works identically. However, chapter headings in `.txt` files appear as isolated uppercase lines rather than `# …` headings. After stripping boilerplate:

1. Identify the heading pattern (typically `CHAPTER I` or `CHAPTER ONE` isolated by blank lines).
2. Run a targeted substitution:

```python
import re

def txt_headings_to_markdown(content):
    # Match isolated all-caps chapter lines
    return re.sub(
        r'(?m)^(CHAPTER\s+[IVXLCDM\d]+(?:\s+\S.*)?)\s*$',
        lambda m: f"## {m.group(1).strip()}",
        content,
    )
```

3. Review the result and apply Rule C (plain-text title on next line) from the script if needed.

## Reference: Heading Patterns Encountered in the Wild

| Book | Original format | Result |
|------|----------------|--------|
| Winnie-the-Pooh | `## ****CHAPTER I` + `### IN WHICH…` | `## CHAPTER I: IN WHICH…` |
| Five Children and It | `## CHAPTER I` + `### BEAUTIFUL AS THE DAY` | `## CHAPTER I: BEAUTIFUL AS THE DAY` |
| Dracula | `## ****CHAPTER I**` | `## CHAPTER I` |
| Babbitt | `## ****CHAPTER I` + `### I` (section number) | `## CHAPTER I` (section numbers left alone) |
| Arsène Lupin (French) | `### ****L'ARRESTATION…` | `### L'ARRESTATION…` |
| Peter Pan | `## Chapter I.` + plain `PETER BREAKS THROUGH` | `## Chapter I: PETER BREAKS THROUGH` |
| Wonderful Wizard of Oz | `## Chapter I` + plain `The Cyclone` | `## Chapter I: The Cyclone` |
| Twenty Thousand Leagues | `## CHAPTER I` + plain `A SHIFTING REEF` | `## CHAPTER I: A SHIFTING REEF` |
| North and South | `## CHAPTER I.` + plain `"HASTE TO THE WEDDING."` | `## CHAPTER I: "HASTE TO THE WEDDING."` |
| Study in Scarlet | `## CHAPTER I.` + plain `MR. SHERLOCK HOLMES.` | `## CHAPTER I: MR. SHERLOCK HOLMES.` |
| Sun Also Rises | `BOOK I` (plain) + `# CHAPTER` + `1` | `## BOOK I` + `## CHAPTER 1` |
| Great Gatsby | `## I`, `## II` … | No change needed |
| Jekyll & Hyde | `## STORY OF THE DOOR` | No change needed |
| Arsène Lupin (English) | `## I. The Arrest of Arsène Lupin` | No change needed |
