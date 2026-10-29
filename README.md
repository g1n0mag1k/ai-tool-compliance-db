# ai-tool-compliance-db

An open-source reference database mapping **55 AI tools across 40 vendors**
to their data-protection posture, by product tier: whether they train on
user input by default, whether a Business Associate Agreement (BAA) is
available, whether a Data Processing Agreement (DPA) is available, and
default data retention.

Built and maintained by [Andrew Rogers](https://github.com/g1n0mag1k) /
Sui-Generis, for use in HIPAA-adjacent AI governance work (AI Data
Exposure Registers, vendor risk assessments, acceptable-use policy
drafting). Released publicly because this lookup is useful to anyone doing
this kind of work, not just paying clients.

## Why this exists

When a law firm or medical practice asks "which of the AI tools my staff
are already using are actually safe to use with client or patient data?",
the honest answer requires knowing, per tool *and per pricing tier* (this
matters — "ChatGPT" the consumer app and "ChatGPT" via a BAA-covered
Enterprise account are different products from a data-handling standpoint):

- Does this tier train its models on what you type into it, by default?
- Can you turn that off?
- Will the vendor sign a BAA at this tier, and under what conditions?
- Is there at least a DPA?

That information is scattered across vendor help-center articles, privacy
policy pages, and trust-center PDFs that change without notice. This repo
is a structured, machine-readable attempt to track it in one place.

## What's in here

| File | Purpose |
|---|---|
| `ai_tools_db.json` | The database. One entry per (vendor, product, tier). |
| `ai_tools_db.csv` | Flat CSV mirror of the same data, for spreadsheet use or as a `--allowlist` input to [`gworkspace_oauth_enum.py`](../ai-exposure-register) in the AI Data Exposure Register toolchain. |
| `schema.json` | JSON Schema for `ai_tools_db.json`. Used to validate the data on every build. |
| `build_db.py` | Source of truth. Edit the `TOOLS` list here and re-run to regenerate the JSON/CSV. Do not hand-edit the generated files. |
| `cross_reference.py` | Takes a client's AI tool inventory (a staff-survey CSV, or the summary CSV from `gworkspace_oauth_enum.py`) and auto-populates a BAA/DPA Matrix by fuzzy-matching tool names against this database. |
| `test_cross_reference.py` | Test suite for the matching logic, including an end-to-end run against a realistic 14-tool survey. |

## Quick start

```bash
pip install -r requirements.txt   # jsonschema, for validation (optional)

# Regenerate the database after editing build_db.py:
python3 build_db.py

# Validate against the schema:
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('ai_tools_db.json')), json.load(open('schema.json'))); print('OK')"

# Cross-reference a client's tool list against the database:
python3 cross_reference.py --input staff_survey.csv --name-column tool_name --tier-column tier
```

`cross_reference.py` also accepts the summary CSV produced directly by the
Google Workspace OAuth enumeration script in the companion
`ai-exposure-register` toolchain:

```bash
python3 cross_reference.py \
    --input oauth_apps_summary_example.com_2026-10-28.csv \
    --name-column app_name
```

## Data model

Each entry in `tools[]` has:

| Field | Meaning |
|---|---|
| `vendor`, `product`, `tier` | Identity. A vendor+product can have multiple tiers (Free, Team, Enterprise, API), each with its own entry, because data-handling terms usually differ by tier. |
| `tier_category` | One of `Consumer Free`, `Consumer Paid`, `Business/Team`, `Enterprise`, `API/Developer` — for quick filtering. |
| `trains_on_input_by_default` | Whether the vendor uses what's typed in to train models, by default, at this tier. |
| `training_opt_out_available` | Whether an opt-out exists if training is on by default. |
| `baa_available` | `true`, `false`, or `"conditional"` (available only under specific conditions — sales-managed account, admin activation, negotiated terms). Always paired with `baa_notes` explaining the condition. |
| `dpa_available` | Whether a Data Processing Agreement is available at this tier. |
| `data_retention_default` | Vendor's stated default retention. |
| `confidence` | `"verified"` or `"general_knowledge"` — see below. |
| `source_urls` | Where `confidence: verified` entries were confirmed. |
| `last_verified` | Date of last confirmation. **Vendor policies change — treat anything older than a few months with extra caution and re-check before relying on it.** |
| `notes` | Practical guidance: what to double-check, common misconceptions, risk context. |

### Confidence levels

- **`verified`** — confirmed against the vendor's own current published
  policy page as of `last_verified`, with `source_urls` populated. As of
  this release, this covers the highest-traffic entries: OpenAI (all
  ChatGPT tiers + API), Anthropic (all Claude tiers + API), Google (Gemini
  consumer app + Gemini for Workspace), Microsoft (consumer Copilot + M365
  Copilot), and Zoom AI Companion.
- **`general_knowledge`** — reflects well-established, publicly reported
  vendor behavior, but was not individually re-verified against a live
  vendor page in this release. Lower confidence. **Re-verify directly with
  the vendor before relying on a `general_knowledge` entry for an actual
  compliance decision.**

## Important disclaimers

- **This is not legal advice.** It is a technical reference for engineers
  and consultants doing AI governance documentation work. Whether a
  specific tool is acceptable for a specific client's specific data should
  be confirmed with that client's legal counsel, especially for anything
  touching PHI or privileged communications.
- **Vendor policies change, sometimes significantly, without much notice.**
  Anthropic's consumer training policy, for example, reversed in September
  2025 (consumer chats now train models by default, where they previously
  did not). Treat every entry as a point-in-time snapshot, not a permanent
  fact.
- **"BAA available" is not the same as "BAA executed."** A vendor offering
  a BAA at a given tier doesn't mean a specific customer's account actually
  has one signed and active. Always confirm execution status with the
  specific client, not just tier eligibility from this database.
- **A personal/consumer account is not covered by an organization's
  enterprise agreement**, even when the organization has a BAA with that
  same vendor at the Enterprise tier. This is one of the most common and
  consequential misunderstandings this database exists to catch — see the
  `Google Gemini app (Consumer)` and `Microsoft Copilot (consumer)` entries
  specifically.

## Contributing

Corrections, new tools, and tier updates are welcome. To contribute:

1. Add or edit an entry in the `TOOLS` list in `build_db.py` (not the
   generated JSON/CSV directly).
2. Set `confidence` honestly — `"verified"` only if you've checked a current,
   linkable vendor source and populated `source_urls`; `"general_knowledge"`
   otherwise.
3. Run `python3 build_db.py` to regenerate the output files, then validate:
   `python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('ai_tools_db.json')), json.load(open('schema.json')))"`.
4. Run `python3 test_cross_reference.py` to make sure nothing broke.
5. Open a PR.

If you work in AI governance / compliance documentation and find this
useful, [Sui-Generis](mailto:rogersandy90@gmail.com) does paid AI Data
Exposure Register engagements for law firms and medical practices — this
database is the open-source core of that offering.

## License

MIT. See [LICENSE](./LICENSE). The data itself is provided for reference
only and is not warranted to be current or accurate — see the disclaimer
above and the `disclaimer` field in `ai_tools_db.json`.
