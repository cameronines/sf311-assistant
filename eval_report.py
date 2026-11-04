"""Eval for reporter.py: ~20 realistic messy inputs with deterministic checks.

Run: python eval_report.py   (writes eval_report_results.txt)
Each case lists what must be true. Drafts are printed in full for manual review.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from reporter import prep, render, TYPES

CASES = [
    # --- Routine, messy (8) ---
    {"group": "routine", "q": "theres a whole couch + mattress dumped on the sidewalk on 24th by the bart",
     "triage": "ready", "types": ["street_sidewalk_cleaning"], "loc": "24th"},
    {"group": "routine", "q": "poop AGAIN in front of my door on hyde st ugh",
     "triage": "ready", "types": ["street_sidewalk_cleaning"], "loc": "hyde"},
    {"group": "routine", "q": "streetlight out at the corner of fulton and 6th ave, super dark at night",
     "triage": "ready", "types": ["streetlight"], "loc": "fulton"},
    {"group": "routine", "q": "huge pothole ate my tire on cesar chavez near folsom",
     "triage": "ready", "types": ["pothole_street"], "loc": "cesar chavez"},
    {"group": "routine", "q": "public trash can overflowing at the bus stop on geary & fillmore, trash all around it",
     "triage": "ready", "types": ["garbage_container"], "loc": "geary"},
    {"group": "routine", "q": "someones car has been parked across my driveway since 7am. 1234 guerrero",
     "triage": "ready", "types": ["blocked_driveway_parking"], "loc": "guerrero"},
    {"group": "routine", "q": "big tree branch hanging real low over the sidewalk after the storm, dolores near 20th",
     "triage": "ready", "types": ["tree"], "loc": "dolores"},
    {"group": "routine", "q": "tagging all over the walls of the laundromat on mission and 22nd",
     "triage": "ready", "types": ["graffiti"], "loc": "mission"},

    # --- Emergency (3) ---
    {"group": "emergency", "q": "guy on the sidewalk not moving, not responding",
     "triage": "emergency"},
    {"group": "emergency", "q": "smells like gas really strong outside on noe st",
     "triage": "emergency"},
    {"group": "emergency", "q": "car crash at van ness and market someone's bleeding",
     "triage": "emergency"},

    # --- Not 311 (3) ---
    {"group": "not_311", "q": "pothole on broadway in oakland near 14th",
     "triage": "not_311", "not_311": ["outside_sf"]},
    {"group": "not_311", "q": "someone spraypainted the blue mailbox on castro st",
     "triage": "not_311", "not_311": ["state_federal_property"]},
    {"group": "not_311", "q": "trash all over the 101 on-ramp at cesar chavez",
     "triage": "not_311", "not_311": ["caltrans_freeway"]},

    # --- Ambiguous: exactly one clarifying question (3) ---
    {"group": "ambiguous", "q": "there's a mess on my street", "triage": "clarify"},
    {"group": "ambiguous", "q": "water everywhere", "triage": "clarify"},
    {"group": "ambiguous", "q": "something's broken by the park", "triage": "clarify"},

    # --- Tricky (4) ---
    {"group": "tricky", "q": "hay basura y un colchon tirado en la banqueta en la calle 24 y folsom",
     "triage": "ready", "types": ["street_sidewalk_cleaning"], "loc": "folsom",
     "note": "Spanish input -> English draft"},
    {"group": "tricky", "q": "on valencia & 18th theres a broken streetlight and also a pile of trash bags on the corner",
     "triage": "ready", "types": ["streetlight", "street_sidewalk_cleaning"], "loc": "valencia",
     "needs_other_issues": True, "note": "two issues -> handle one, list the other"},
    {"group": "tricky", "q": "needles on the ground and a woman lying next to them, she doesnt seem to be breathing",
     "triage": "emergency", "note": "emergency wins over 311 issue"},
    {"group": "tricky", "q": "my neighbor Dave Kowalski (415-555-0199) keeps leaving his old couch on the sidewalk at 300 lake st",
     "triage": "ready", "types": ["street_sidewalk_cleaning"], "loc": "lake",
     "forbid": ["dave", "kowalski", "555-0199"], "note": "strip third-party name/phone"},
]

PHONE = re.compile(r"\d{3}[-.\s]\d{4}")


def judge(case, r, text):
    problems = []
    if r["triage"] != case["triage"]:
        problems.append(f"triage={r['triage']} (want {case['triage']})")

    if r["service_type_id"] not in list(TYPES) + ["none"]:
        problems.append(f"invented type {r['service_type_id']!r}")

    if "types" in case and r["service_type_id"] not in case["types"]:
        problems.append(f"type={r['service_type_id']} (want {case['types']})")

    if "not_311" in case and r["not_311_id"] not in case["not_311"]:
        problems.append(f"not_311={r['not_311_id']} (want {case['not_311']})")

    # Every card has a generic "call 911" line, so look for the emergency banner.
    if case["triage"] == "emergency" and "CALL 911 NOW" not in text:
        problems.append("no emergency banner in output")

    if case["triage"] == "clarify":
        q = r["clarifying_question"]
        if q.count("?") != 1:
            problems.append(f"clarifying question has {q.count('?')} '?'")

    draft = r["draft_description"]
    if case["triage"] == "ready":
        if not draft.strip():
            problems.append("empty draft")
        if "loc" in case and case["loc"] not in draft.lower():
            problems.append(f"draft missing location {case['loc']!r}")
        if PHONE.search(draft):
            problems.append("phone number in draft")
        if r["confidence"] == "low" and "Call 311" not in text:
            problems.append("low confidence without 'Call 311'")

    for word in case.get("forbid", []):
        if word in draft.lower():
            problems.append(f"draft contains {word!r}")

    if case.get("needs_other_issues") and not r["other_issues"]:
        problems.append("second issue not listed")

    return (not problems), ("ok" if not problems else "; ".join(problems))


def run(case):
    try:
        r = prep(case["q"])
    except Exception as err:  # keep going; record the failure
        return case, None, f"ERROR: {err}", False, f"error: {err}"
    text = render(r)
    ok, why = judge(case, r, text)
    return case, r, text, ok, why


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, CASES))

    passed = 0
    summary, details = [], []
    for i, (case, r, text, ok, why) in enumerate(results, 1):
        passed += ok
        line = f"{'PASS' if ok else 'FAIL'}  Q{i} [{case['group']}] {case['q']}\n      -> {why}"
        print(line)
        summary.append(line)
        details.append(f"{'=' * 72}\nQ{i} [{case['group']}] {case['q']}\n"
                       f"{'(' + case['note'] + ')' if case.get('note') else ''}\n\n{text}\n")

    score = f"\nScore: {passed}/{len(CASES)}"
    print(score)
    with open("eval_report_results.txt", "w") as f:
        f.write("\n".join(summary) + score + "\n\n\nFULL OUTPUTS (for manual review of drafts)\n")
        f.write("\n".join(details))
