import re
from assistant import ask
from tools import count_requests

DEFAULT_DAYS = {"count_requests": 30, "recent_similar_requests": 14}

CASES = [
    # Counts: the number in the answer is checked against a direct query
    {"q": "How many public graffiti reports were filed in the Mission in the last 30 days?",
     "tool": "count_requests",
     "args": {"category": "Graffiti Public", "neighborhood": "Mission", "days": 30},
     "check_number": True},
    {"q": "How many noise complaints in the Tenderloin over the past 7 days?",
     "tool": "count_requests",
     "args": {"category": "Noise", "neighborhood": "Tenderloin", "days": 7},
     "check_number": True},
    {"q": "How many tree maintenance requests were filed in Sunset/Parkside in the last 30 days?",
     "tool": "count_requests",
     "args": {"category": "Tree Maintenance", "neighborhood": "Sunset/Parkside", "days": 30},
     "check_number": True},
    # Plain-language names for places
    {"q": "How many streetlight problems were reported in the Castro in the past 30 days?",
     "tool": "count_requests",
     "args": {"category": "Streetlights", "neighborhood": "Castro/Upper Market", "days": 30},
     "check_number": True},
    {"q": "How many sewer requests in the Financial District in the past 14 days?",
     "tool": "count_requests",
     "args": {"category": "Sewer", "neighborhood": "Financial District/South Beach", "days": 14},
     "check_number": True},
    # Resolution times
    {"q": "How long do street defects usually take to get closed in the Tenderloin?",
     "tool": "typical_resolution_time",
     "args": {"category": "Street Defect", "neighborhood": "Tenderloin"}},
    {"q": "What's the typical closing time for graffiti reports on public property in the Mission?",
     "tool": "typical_resolution_time",
     "args": {"category": "Graffiti Public", "neighborhood": "Mission"}},
    # Duplicate checks
    {"q": "I want to report garbage on Valencia Street in the Mission. Has it already been reported?",
     "tool": "recent_similar_requests",
     "args": {"category": "Street and Sidewalk Cleaning", "neighborhood": "Mission",
              "street_contains": "VALENCIA"}},
    {"q": "Is there already a report open for a pothole on Mission Street in the Excelsior?",
     "tool": "recent_similar_requests",
     "args": {"category": "Street Defect", "neighborhood": "Excelsior",
              "street_contains": "MISSION"}},
    # Should NOT call a tool
    {"q": "What's the weather in San Francisco today?", "tool": None},
    {"q": "How many 311 requests were filed in Oakland last month?", "tool": None},
    {"q": "How many reports were filed recently?", "tool": None},  # too vague: should ask
]


def numbers_in(text):
    return [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)
            if n.replace(",", "").isdigit()]


def judge(case, text, calls):
    tool = case["tool"]
    if tool is None:
        return (not calls), ("no tool called" if not calls
                             else f"called {calls[0][0]} but should not have")

    match = [c for c in calls if c[0] == tool]
    if not match:
        names = [c[0] for c in calls] or "no tools"
        return False, f"expected {tool}, got {names}"

    expected = case["args"]
    for name, args in match:
        problems = []
        for key in ("category", "neighborhood"):
            if args.get(key) != expected[key]:
                problems.append(f"{key}={args.get(key)!r}")
        if "days" in expected:
            if args.get("days", DEFAULT_DAYS[name]) != expected["days"]:
                problems.append(f"days={args.get('days')!r}")
        if "street_contains" in expected:
            if expected["street_contains"] not in args.get("street", "").upper():
                problems.append(f"street={args.get('street')!r}")
        if not problems:
            break
    else:
        return False, "wrong inputs: " + ", ".join(problems)

    if case.get("check_number"):
        truth = count_requests(expected["category"], expected["neighborhood"],
                               expected["days"])["count"]
        tolerance = max(3, int(truth * 0.02))
        if not any(abs(n - truth) <= tolerance for n in numbers_in(text)):
            return False, f"right tool, but answer number does not match data ({truth})"
        return True, f"right tool, number matches data ({truth})"

    return True, "right tool and inputs"


if __name__ == "__main__":
    passed = 0
    lines = []
    for i, case in enumerate(CASES, 1):
        text, calls = ask(case["q"], return_calls=True)
        ok, why = judge(case, text, calls)
        passed += ok
        line = f"{'PASS' if ok else 'FAIL'}  Q{i}: {case['q']}\n      -> {why}"
        print(line)
        lines.append(line)
    summary = f"\nScore: {passed}/{len(CASES)}"
    print(summary)
    with open("eval_results.txt", "w") as f:
        f.write("\n".join(lines) + summary + "\n")