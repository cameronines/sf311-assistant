"""SF311 report-prep assistant.

Turns a messy plain-language description into: an emergency check, the most
likely SF311 report type, a prep checklist, and a draft description to paste
into the official form. It never submits anything.
"""
import json
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from tools import VALID_CATEGORIES

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"

DATA = json.loads((Path(__file__).parent / "data" / "service_types.json").read_text())
TYPES = {s["id"]: s for s in DATA["service_types"]}
OTHER_FORMS = {o["id"]: o for o in DATA["other_311_forms"]}
NOT_311 = {n["id"]: n for n in DATA["not_311"]}


def _check_data():
    """Fail fast if the curated file drifts from the real dataset or itself."""
    ids = [s["id"] for s in DATA["service_types"]]
    assert len(ids) == len(set(ids)), "duplicate service type id"
    for s in DATA["service_types"]:
        for cat in s["datasf_categories"]:
            assert cat in VALID_CATEGORIES, f"{s['id']}: unknown DataSF category {cat!r}"
        for rule in s["not_this_if"]:
            assert rule.get("use", ids[0]) in TYPES, rule
            assert rule.get("use_other_form", "parks") in OTHER_FORMS, rule
            assert rule.get("use_not_311", "outside_sf") in NOT_311, rule


_check_data()

DISCLAIMER = ("Unofficial helper, not a City of San Francisco tool. It does not "
              "submit reports. Use the SF311 app, sf.gov, or call 311.")
CALL_311 = "Call 311 (415-701-2311 from outside SF) and describe it to them."

# Safety net: if the model misses an obvious emergency, still show the 911 line.
EMERGENCY_WORDS = re.compile(
    r"not breathing|unresponsive|not responding|not moving|unconscious|overdos|"
    r"bleeding|on fire|\bfire\b|smoke|gas smell|smell(s|ing)? (like |of )?gas|"
    r"power line|live wire|sparking|gun|stabb|attack", re.I)

NONE = "none"

# JSON schema for structured outputs. Enums keep the model inside the curated
# lists, the same grounding trick assistant.py uses for categories.
REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "triage": {
            "type": "string",
            "enum": ["emergency", "not_311", "clarify", "ready"],
            "description": "emergency = call 911 now; not_311 = belongs elsewhere; "
                           "clarify = need one answer before choosing a type; "
                           "ready = enough to prepare a report.",
        },
        "service_type_id": {"type": "string", "enum": list(TYPES) + [NONE],
                            "description": "Chosen type from service_types, or none."},
        "other_form_id": {"type": "string", "enum": list(OTHER_FORMS) + [NONE],
                          "description": "Use only if the issue fits an other_311_forms entry "
                                         "and no service_types entry."},
        "not_311_id": {"type": "string", "enum": list(NOT_311) + [NONE],
                       "description": "Set when triage is not_311."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string",
                   "description": "One short sentence: why this triage/type."},
        "checklist": {"type": "array", "items": {"type": "string"},
                      "description": "What to have ready. Empty unless triage is ready."},
        "draft_description": {"type": "string",
                              "description": "Text to paste into the form. Empty unless triage is ready."},
        "clarifying_question": {"type": "string",
                                "description": "Exactly one question. Empty unless triage is clarify."},
        "other_issues": {"type": "array", "items": {"type": "string"},
                         "description": "Other separate problems mentioned, each a few words."},
    },
    "required": ["triage", "service_type_id", "other_form_id", "not_311_id",
                 "confidence", "reason", "checklist", "draft_description",
                 "clarifying_question", "other_issues"],
}

RULES = """You help people in San Francisco prepare a good SF311 report.
You do not submit anything. You are not an official City tool.

Use ONLY the reference data below. Never invent report types, departments,
agencies, phone numbers, or URLs. Answer only with the required JSON object.

Decide in this order:
1. EMERGENCY. If anything matches emergency_signs, or any service type's
   emergency_notes, set triage=emergency, even if there is also a 311 issue.
   Also set service_type_id if there is a 311 issue to file once everyone is safe.
2. NOT 311. If the location is outside San Francisco, or the issue matches a
   not_311 entry, or a not_this_if rule points to a not_311 entry, set
   triage=not_311 and not_311_id.
3. CLARIFY. Only if the problem itself is too vague to choose between
   different report types (e.g. "there's a mess", "water everywhere"), set
   triage=clarify and ask exactly ONE short question, in the user's language.
   A missing location is NOT a reason to clarify; use a [location] placeholder.
4. READY. Pick the single best service_type_id, applying not_this_if rules.
   If it fits only an other_311_forms entry, set other_form_id instead and
   service_type_id=none. If nothing fits, service_type_id=none, confidence=low.

Confidence: high = clearly one type; medium = a reasonable guess between two;
low = unsure or nothing fits.

Checklist (ready only): start from the chosen type's have_ready items. For each,
say what the user already gave or what is missing, e.g. "Exact location: you
said 24th St near BART; add the nearest cross street or address". Add the photo
and contact info lines from the type's data. Keep each item short.

Draft description (ready only):
- 2 to 4 plain sentences in English, written for a city crew.
- Use only facts the user gave. Put missing details in [brackets], e.g.
  [nearest cross street], [how long it has been there].
- Describe objects and conditions, not people. Do not guess anyone's housing
  status, race, age, or behavior beyond what is needed.
- Never include names, phone numbers, emails, or license plates of other
  people. (License plates go in the form's own field, so list that in the
  checklist instead.)
- No timing promises, no blame, no exaggeration.

Multiple problems: prepare the most urgent one and list the rest in
other_issues so the person can file them separately.
"""

# Used if the model declines or gets cut off: never leave the person without a path.
FALLBACK_RESULT = {
    "triage": "ready", "service_type_id": NONE, "other_form_id": NONE,
    "not_311_id": NONE, "confidence": "low",
    "reason": "I couldn't prepare this one automatically.",
    "checklist": [], "draft_description": "", "clarifying_question": "",
    "other_issues": [],
}

SYSTEM = [
    {"type": "text", "text": RULES},
    {"type": "text",
     "text": "Reference data (data/service_types.json):\n" + json.dumps(DATA, indent=1),
     "cache_control": {"type": "ephemeral"}},
]


def prep(description):
    """Return the structured report-prep dict for one description."""
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": REPORT_SCHEMA}},
        # If a safety classifier declines, the API retries on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": description}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if response.stop_reason in ("refusal", "max_tokens") or not text:
        result = dict(FALLBACK_RESULT)
    else:
        result = json.loads(text)
    result["safety_net"] = bool(EMERGENCY_WORDS.search(description)) and result["triage"] != "emergency"
    return result


def _bullets(items):
    return "\n".join(f"  - {i}" for i in items)


def render(r):
    out = []
    t = TYPES.get(r["service_type_id"])
    form = OTHER_FORMS.get(r["other_form_id"])

    # 1. Emergency check
    if r["triage"] == "emergency":
        out.append("!! THIS SOUNDS LIKE AN EMERGENCY. CALL 911 NOW.")
        out.append(f"   {r['reason']}")
        if t:
            out.append(f"   Once everyone is safe, you can also file \"{t['title']}\" with 311.")
        out.append(f"\n{DISCLAIMER}")
        return "\n".join(out)
    if r["safety_net"]:
        out.append("!! If anyone is in danger or hurt, call 911 first.")
    else:
        out.append("1. Emergency check: no emergency signs found. If anyone is in danger, call 911.")
    if t:
        for note in t["emergency_notes"]:
            out.append(f"   Note: {note}")

    if r["triage"] == "not_311":
        n = NOT_311.get(r["not_311_id"])
        out.append("\n2. This probably isn't an SF311 issue.")
        if n:
            out.append(f"   {n['situation']}.\n   Where to go: {n['go_to']}")
            if n["source_url"]:
                out.append(f"   Source: {n['source_url']}")
        out.append(f"   {r['reason']}")
        out.append(f"   Not sure? {CALL_311}")

    elif r["triage"] == "clarify":
        out.append(f"\nOne question before I can pick a report type:\n   {r['clarifying_question']}")

    else:
        out.append("\n2. Likely SF311 report type")
        if t:
            out.append(f"   {t['title']}  ({'in the SF311 app' if t['in_app'] else 'may not be in the app'})")
            out.append(f"   Form: {t['source_url']}")
            for note in t["notes"]:
                out.append(f"   Note: {note}")
        elif form:
            out.append(f"   {form['title']}  (check the SF311 app; this one isn't in my detailed list)")
            out.append(f"   Form: {form['url']}")
        else:
            out.append("   I couldn't match this to a report type.")
        out.append(f"   Why: {r['reason']}")

        out.append("\n3. What to have ready")
        out.append(_bullets(r["checklist"]))

        out.append("\n4. Draft description (edit, then paste into the official form)")
        out.append("   " + r["draft_description"].replace("\n", "\n   "))

        out.append("\n5. Confidence: " + r["confidence"])
        if r["confidence"] == "low" or not (t or form):
            out.append(f"   I'm not sure about this one. {CALL_311}")
        elif r["confidence"] == "medium":
            out.append("   Double-check the report type in the app before submitting.")

    if r["other_issues"]:
        out.append("\nYou also mentioned (file each as a separate report):")
        out.append(_bullets(r["other_issues"]))

    out.append(f"\n{DISCLAIMER}")
    return "\n".join(out)


if __name__ == "__main__":
    print("SF311 report helper. " + DISCLAIMER)
    print("Describe the problem in your own words (blank line to quit).")
    while True:
        text = input("\nProblem: ").strip()
        if not text:
            break
        print("\n" + render(prep(text)))
