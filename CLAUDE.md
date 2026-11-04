# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A plain-language assistant for SF community volunteers. It answers questions about San Francisco 311 data by having Claude call three fixed tools. It does not let Claude write its own queries. Data comes from DataSF's public 311 dataset (`vw6y-z8j6`, Socrata SODA API, no key needed, updated nightly).

## Commands

```bash
source .venv/bin/activate
pip install -r requirements.txt          # requests, pandas, anthropic, python-dotenv
python assistant.py                      # interactive Q&A loop (blank line quits)
python eval.py                           # 12-question eval; overwrites eval_results.txt
python test_tools.py                     # call the data tools directly (no Claude)
python test_claude.py                    # sanity-check the API key/model
```

`ANTHROPIC_API_KEY` is loaded from `.env` (gitignored). There is no test framework, linter, or build step. Every script makes live network calls to DataSF, and most also call the Anthropic API. The eval has no CLI for running a single case. To check one question, call `ask(question, return_calls=True)` from `assistant.py` and pass the result to `judge(case, text, calls)` from `eval.py`.

## Architecture

- **`tools.py`**: the data layer. It has three public functions (`count_requests`, `recent_similar_requests`, `typical_resolution_time`) that build SoQL `$where` strings and send them to `URL` through `_get`. Safety depends on input validation, not parameterization:
  - `_check` rejects any category or neighborhood that isn't in `VALID_CATEGORIES` / `VALID_NEIGHBORHOODS`. These lists were pulled from the dataset, partly with `list_values.py`.
  - `_clean_street` uppercases the input, whitelists `[A-Z0-9 -]`, and abbreviates suffixes (STREET→ST) to match DataSF address formatting. The LIKE pattern `'% {s}%' OR '{s}%'` matches on word boundaries so `6TH ST` doesn't match `16TH ST`. Any new user-controlled string that goes into a query needs the same kind of whitelist.
  - `recent_similar_requests` runs a separate `count(*)` query so it can return `total_matching` alongside `shown`. The model uses this to say whether a list is partial.
  - `typical_resolution_time` only uses cases filed 30–180 days ago, because recent cases are mostly still open and would skew the median. It calculates the median in pandas over closed cases only and also returns `share_closed`.
- **`assistant.py`**: the Claude layer. `TOOLS` contains the JSON schemas, and category and neighborhood are `enum`s built from the lists in `tools.py`. `SYSTEM` holds the behavioral rules: say "closed", not "fixed"; mention share closed; report neutrally; note when a list is partial; for intersections, search one street and look for the other in the addresses. `ask()` runs a manual tool-use loop capped at 6 turns. Tool exceptions go back to the model as `is_error` results. `ask()` keeps no conversation memory between questions. The model is set by `MODEL`.
- **`eval.py`**: `CASES` lists the expected tool and args for each question. `tool: None` means the model should decline or ask for clarification. `judge` checks the tool choice and the category, neighborhood, and days args. Default days come from `DEFAULT_DAYS`, which must match the defaults in `tools.py`. For street cases it checks a substring with `street_contains`. For `check_number` cases it compares the numbers in the answer against a live `count_requests` result, with a tolerance of max(3, 2%).
- `explore_311.py`, `check_recent.py`, `list_values.py`: one-off scripts for exploring the dataset. `NOTES.md` has the column map and data findings.

## Keep in sync

If you change a tool's signature or defaults, update all three of these: the function in `tools.py`, the schema in `TOOLS` (`assistant.py`), and `DEFAULT_DAYS`/`CASES` in `eval.py`.

## Data caveats (from NOTES.md / README)

- Columns used: `service_name` (category), `analysis_neighborhood`, `requested_datetime`, `closed_date`, `status_description` (Open/Closed), `address`, `service_subtype`.
- `status_notes` is the city's resolution note, not the reporter's description, so matching is done on category and never on free text.
- About 10.8k cases a year have no neighborhood. These are excluded from every neighborhood query.


## Project: SF311 reporting assistant

### Goal
A chat assistant that helps people prepare a good SF311 report. Given a
messy plain-language description of a problem, it returns:
1. Emergency check first (point to 911 if urgent)
2. Most likely SF311 service type, and a note if it may not be in the app
3. What to have ready: exact location, photo, whether contact info is needed
4. A clear draft description the person can paste into the official form
5. An honest "I'm not sure, call 311" when confidence is low

It does NOT submit reports. The official SF311 form stays the source of truth.

### Users
First-time reporters, volunteers filing several issues from one outing,
and people who may not know city terminology.

### Rules
- Ground answers in a local file of real SF311 service types
  (data/service_types.json). Never invent departments or categories.
- Public or synthetic data only. No real personal information.
- Claude API key from .env (ANTHROPIC_API_KEY). Never log or commit it.
- Keep it simple: smallest working slice first, commit after each working step.
- Handle: emergencies, non-311 problems, ambiguous input (ask ONE
  clarifying question).
- Not an official City of San Francisco tool. Make that clear in the
  README and the UI.

### Definition of done (v1)
A user can type a messy problem and get the right service type, prep
checklist, and draft description. Emergency and "not a 311 issue" cases
are handled.
Later: multi-issue input, duplicate check against the public 311 dataset.