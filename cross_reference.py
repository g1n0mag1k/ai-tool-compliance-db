#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_reference.py
===================

Cross-references a client's AI tool inventory against ai_tools_db.json to
auto-populate the BAA/DPA Matrix section of an AI Data Exposure Register.

Accepts two kinds of input interchangeably:

  1. A staff-survey export (any CSV with a column containing tool names,
     e.g. "tool_name", "app", "tool").
  2. The summary CSV produced by gworkspace_oauth_enum.py
     (oauth_apps_summary_<domain>_<date>.csv, which has an "app_name" column).

Matching is fuzzy (difflib-based name matching against `vendor`, `product`,
and known aliases) since a staff survey or OAuth consent screen's
`displayText` rarely matches the DB's canonical product name exactly
("ChatGPT" vs. "OpenAI ChatGPT" vs. "ChatGPT (Free)"). Where the input
distinguishes a tier (e.g. a column named "tier" or "plan", or OAuth scope
data implying consumer vs. tenant-managed use), that narrows the match;
otherwise the script reports all matching tiers for that product and flags
the row for manual tier selection.

Output: a single CSV (bb_matrix_output.csv by default) matching the AI Data
Exposure Register's BAA/DPA Matrix column layout:
  Tool, Vendor Tier, Trains on Input, BAA Available, DPA in Place,
  Approved for PHI, Risk Note, Match Confidence, DB Source

Usage
-----
  python3 cross_reference.py --input staff_survey.csv --name-column tool_name
  python3 cross_reference.py --input oauth_apps_summary_riverside.com_2026-10-28.csv --name-column app_name
  python3 cross_reference.py --input staff_survey.csv --name-column tool --tier-column plan
"""

import argparse
import csv
import difflib
import json
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "ai_tools_db.json"

# Manual alias map for common real-world display names that don't fuzzy-match
# cleanly against the DB's canonical vendor/product strings. Add to this as
# new mismatches are found in real engagements — it's cheaper than trying
# to make the fuzzy matcher cleverer.
ALIASES = {
    "chatgpt": "OpenAI ChatGPT",
    "gpt": "OpenAI ChatGPT",
    "openai api": "OpenAI API Platform",
    "claude": "Anthropic Claude.ai",
    "claude.ai": "Anthropic Claude.ai",
    "gemini": "Google Gemini app",
    "google gemini": "Google Gemini app",
    "google workspace gemini": "Google Gemini for Google Workspace",
    "copilot": "Microsoft Copilot (consumer, copilot.microsoft.com)",
    "microsoft copilot": "Microsoft Copilot (consumer, copilot.microsoft.com)",
    "m365 copilot": "Microsoft Microsoft 365 Copilot",
    "microsoft 365 copilot": "Microsoft Microsoft 365 Copilot",
    "otter": "Otter.ai Otter.ai",
    "fireflies": "Fireflies.ai Fireflies.ai",
    "zoom ai companion": "Zoom Zoom AI Companion",
    "grammarly": "Grammarly Grammarly",
    "deepl": "DeepL DeepL",
    "dragon medical one": "Microsoft/Nuance Dragon Medical One",
    "dragon medical": "Microsoft/Nuance Dragon Medical One",
    "github copilot": "GitHub (Microsoft) GitHub Copilot",
    "cursor": "Cursor (Anysphere) Cursor",
    "canva": "Canva Canva (Magic Studio AI features)",
    "notion ai": "Notion Labs Notion AI",
    "perplexity": "Perplexity AI Perplexity",
    "grok": "xAI Grok",
    "midjourney": "Midjourney Midjourney",
    "fathom": "Fathom Fathom",
    "cocounsel": "Thomson Reuters CoCounsel",
    "harvey": "Harvey AI Harvey",
    "lexis+ ai": "LexisNexis Lexis+ AI",
    "lexis ai": "LexisNexis Lexis+ AI",
    "spellbook": "Spellbook Spellbook",
    "heidi": "Heidi Health Heidi",
    "suki": "Suki AI Suki Assistant",
    "nabla": "Nabla Nabla Copilot",
    "abridge": "Abridge Abridge",
}


def load_db(path: Path):
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    return db["tools"]


def normalize(s: str) -> str:
    return " ".join(s.lower().strip().split())


def candidate_strings(tool: dict):
    """All the strings worth fuzzy-matching a user's input against, for one DB tool."""
    yield f"{tool['vendor']} {tool['product']}"
    yield tool["product"]
    yield f"{tool['product']} {tool['tier']}"
    yield f"{tool['vendor']} {tool['product']} {tool['tier']}"


def find_matches(input_name: str, tools: list, tier_hint: str = None, cutoff: float = 0.55):
    """
    Returns a list of (score, tool_dict) tuples, best first, for a given
    input tool name. Checks the alias map first (exact, case-insensitive);
    falls back to difflib fuzzy matching across all candidate strings.
    """
    norm_input = normalize(input_name)

    # 1. Alias exact match
    if norm_input in ALIASES:
        target = normalize(ALIASES[norm_input])
        exact = [t for t in tools if normalize(f"{t['vendor']} {t['product']}") == target]
        if exact:
            scored = [(1.0, t) for t in exact]
            return _apply_tier_hint(scored, tier_hint)

    # 2. Fuzzy match across all candidate strings for all tools
    scored = []
    for t in tools:
        best_for_tool = 0.0
        for cand in candidate_strings(t):
            ratio = difflib.SequenceMatcher(None, norm_input, normalize(cand)).ratio()
            if ratio > best_for_tool:
                best_for_tool = ratio
        if best_for_tool >= cutoff:
            scored.append((best_for_tool, t))

    scored.sort(key=lambda x: -x[0])
    return _apply_tier_hint(scored, tier_hint)


def _apply_tier_hint(scored, tier_hint):
    if not tier_hint or not scored:
        return scored
    norm_hint = normalize(tier_hint)
    reordered = sorted(scored, key=lambda x: (normalize(x[1]["tier"]).find(norm_hint) == -1, -x[0]))
    return reordered


def group_by_product(matches):
    """Collapses multiple tier-matches for the same vendor+product into a
    deduped list, preserving order, for presenting tier choices to the user."""
    seen = set()
    out = []
    for score, t in matches:
        key = (t["vendor"], t["product"])
        if key not in seen:
            seen.add(key)
            out.append((score, t))
    return out


def risk_note_for(tool: dict) -> str:
    baa = tool["baa_available"]
    trains = tool["trains_on_input_by_default"]
    if baa is True and trains in (False, "n/a"):
        level = "Low"
    elif baa == "conditional":
        level = "Medium — BAA conditional, confirm activation"
    elif baa is False and trains is True:
        level = "High — no BAA, trains on input by default"
    elif baa is False:
        level = "Medium-High — no BAA available at this tier"
    else:
        level = "Review"
    return f"{level}. {tool['baa_notes']}"


def approved_for_phi(tool: dict) -> str:
    if tool["baa_available"] is True and tool["trains_on_input_by_default"] in (False, "n/a"):
        return "Y (if BAA executed for this account)"
    if tool["baa_available"] == "conditional":
        return "Conditional — confirm BAA activation"
    return "N"


def process_input(input_path: Path, name_col: str, tier_col: str, tools: list):
    rows_out = []
    unmatched = []

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if name_col not in reader.fieldnames:
            sys.exit(
                f"Column '{name_col}' not found in {input_path}. "
                f"Available columns: {', '.join(reader.fieldnames)}"
            )
        for row in reader:
            raw_name = (row.get(name_col) or "").strip()
            if not raw_name:
                continue
            tier_hint = (row.get(tier_col) or "").strip() if tier_col else None

            matches = find_matches(raw_name, tools, tier_hint=tier_hint)

            if not matches:
                unmatched.append(raw_name)
                rows_out.append({
                    "input_tool_name": raw_name,
                    "matched_db_entry": "",
                    "vendor_tier": "NOT FOUND IN DATABASE",
                    "trains_on_input": "",
                    "baa_available": "",
                    "dpa_in_place": "",
                    "approved_for_phi": "",
                    "risk_note": "Not found in ai_tools_db.json — manual research required. "
                                 "Consider contributing this tool back to the public DB once researched.",
                    "match_confidence": "0%",
                    "db_source_urls": "",
                })
                continue

            best_score, best_tool = matches[0]
            # If multiple distinct products matched closely and no tier hint
            # narrowed it, flag ambiguity rather than silently picking one.
            distinct_products = group_by_product(matches)
            ambiguous = len(distinct_products) > 1 and not tier_hint and best_score < 0.95

            rows_out.append({
                "input_tool_name": raw_name,
                "matched_db_entry": best_tool["id"],
                "vendor_tier": f"{best_tool['vendor']} {best_tool['product']} — {best_tool['tier']}",
                "trains_on_input": best_tool["trains_on_input_by_default"],
                "baa_available": best_tool["baa_available"],
                "dpa_in_place": best_tool["dpa_available"],
                "approved_for_phi": approved_for_phi(best_tool),
                "risk_note": risk_note_for(best_tool) + (
                    "  [AMBIGUOUS MATCH — multiple tiers/products possible; confirm manually, "
                    "consider adding a tier/plan column to your input CSV.]" if ambiguous else ""
                ),
                "match_confidence": f"{best_score * 100:.0f}%",
                "db_source_urls": " | ".join(best_tool["source_urls"]),
            })

    return rows_out, unmatched


def main():
    parser = argparse.ArgumentParser(
        description="Cross-reference an AI tool inventory against ai_tools_db.json "
                    "to auto-populate an AI Data Exposure Register's BAA/DPA Matrix.",
    )
    parser.add_argument("--input", required=True, help="Input CSV (staff survey or OAuth summary export).")
    parser.add_argument("--name-column", required=True,
                         help="Column in the input CSV containing the tool/app name (e.g. 'tool_name', 'app_name').")
    parser.add_argument("--tier-column", default=None,
                         help="Optional column containing a tier/plan hint (e.g. 'Free', 'Enterprise') to disambiguate matches.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH),
                         help="Path to ai_tools_db.json (default: alongside this script).")
    parser.add_argument("--output", default="baa_dpa_matrix_output.csv",
                         help="Output CSV path.")
    parser.add_argument("--cutoff", type=float, default=0.55,
                         help="Minimum fuzzy-match score (0-1) to count as a match. Lower = more permissive, "
                              "more false positives. Default 0.55.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Input file not found: {input_path}")

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"Database file not found: {db_path}. Run build_db.py first, or pass --db explicitly.")

    tools = load_db(db_path)
    print(f"Loaded {len(tools)} reference entries from {db_path}")

    rows_out, unmatched = process_input(input_path, args.name_column, args.tier_column, tools)

    fields = ["input_tool_name", "matched_db_entry", "vendor_tier", "trains_on_input",
              "baa_available", "dpa_in_place", "approved_for_phi", "risk_note",
              "match_confidence", "db_source_urls"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    print(f"Wrote {args.output} ({len(rows_out)} rows)")
    if unmatched:
        print(f"\n{len(unmatched)} tool(s) not found in the database — manual research required:")
        for u in unmatched:
            print(f"  - {u}")
        print(
            "\nConsider adding these to ai_tools_db.json (via build_db.py) once researched, "
            "so future engagements benefit from the lookup."
        )
    else:
        print("All input tools matched against the database.")


if __name__ == "__main__":
    main()
