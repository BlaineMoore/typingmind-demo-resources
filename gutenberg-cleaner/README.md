# gutenberg-cleaner

Cleans Project Gutenberg ebook exports (`.md` or `.txt`) into consistent, presentation-ready markdown.

## What It Does

**Step 1 — Strip boilerplate.** Removes the standard Gutenberg licence header (everything before `*** START OF THE PROJECT GUTENBERG EBOOK …`) and footer (everything from `*** END OF THE PROJECT GUTENBERG EBOOK …` onward).

**Step 2 — Normalise chapter headings.** Combines chapter numbers and chapter names onto a single heading line, cleans stray formatting asterisks, promotes isolated `BOOK`/`PART` labels to markdown headings, and stitches split `# CHAPTER` + number lines together.

## Quick Start

```bash
# Preview changes without writing anything
python3 scripts/clean_gutenberg.py path/to/books/ --dry-run

# Process all .md and .txt files in a folder
python3 scripts/clean_gutenberg.py path/to/books/

# Process a single file
python3 scripts/clean_gutenberg.py "Dracula - Bram Stoker.md"
```

## Files

```
gutenberg-cleaner/
├── SKILL.md          # Full skill instructions for Claude Code
├── README.md         # This file
└── scripts/
    └── clean_gutenberg.py   # Python 3.9+ processing script
```

## What the Script Handles Automatically

| Situation | Transformation |
|-----------|---------------|
| Gutenberg header/footer | Stripped |
| `## ****CHAPTER I` + `### Subtitle` | → `## CHAPTER I: Subtitle` |
| `## ****CHAPTER I**` (stray asterisks) | → `## CHAPTER I` |
| `### ****Named Chapter` | → `### Named Chapter` |
| `## CHAPTER I.` + plain-text title on next line | → `## CHAPTER I: Title` |
| `# CHAPTER` + `1` on next line | → `## CHAPTER 1` |
| `BOOK I` / `PART ONE` as isolated plain text | → `## BOOK I` / `## PART ONE` |

## What Requires Manual Review

- **Section-number sub-headings** (`### I`, `### II` inside a chapter) — the script leaves these alone; verify they weren't accidentally merged.
- **Epigraphs** — block quotes or poems at the top of a chapter are left as content, not merged into the heading. Spot-check a few chapters.
- **Inconsistent heading levels** — some books mix `##` and `###` for chapters; adjust by hand if needed.
- **Plain `.txt` inputs** — boilerplate stripping works automatically; chapter headings that are bare uppercase text (not `#` headings) need a manual or custom conversion step (see SKILL.md §Step 4).

## Requirements

- Python 3.9 or later (uses `list[str]` type hints)
- No third-party dependencies
