# SF 311 Assistant

A plain-language assistant for community volunteers to explore San Francisco
311 data: how many reports exist, what's already open nearby, and how long
cases usually take to close.

> Personal prototype. Not affiliated with the City of San Francisco or Civic
> Joy Fund. Data comes from DataSF's public 311 dataset.

## Why I built this
On city cleanup volunteer shifts in San Francisco, we're often told to file
anything we can't clean up ourselves with 311. Items we find range from large furniture and bulk garbage to more hazardous things. Through my volunteering with Civic Joy Fund and conversations with other volunteers, I kept running into the same questions we wished we could answer *before* filing: Has someone already reported this? How long do these usually take? I built this to answer them in plain language.

## What it does
- **Count** requests by category and neighborhood over a time window
- **Duplicate check:** list still-open requests of the same type, optionally
  narrowed to a street name, and say whether the list is complete or partial
- **Typical closing time** (median days) for a category in a neighborhood

## Example: duplicate check
Asking "I want to report garbage near 16th and Mission. Has it already been
reported?" before and after I added the street filter:

| | Before | After |
|---|---|---|
| Search scope | Whole neighborhood, newest rows only | Filtered by street name |
| Report at the intersection (#202000220330) | Missed | Found |
| Completeness | Guessed the list "may be incomplete" | Reports exact totals (23 open on 16th St, 10 shown) |

<details>
<summary>Full before and after transcripts</summary>

**Before**
```
Question: I want to report garbage on the street near 16th and Mission. Has it already been reported?
  [tool] recent_similar_requests({'category': 'Street and Sidewalk Cleaning', 'neighborhood': 'Mission'})
  [tool] recent_similar_requests({'category': 'Street and Sidewalk Cleaning', 'neighborhood': 'Mission', 'limit': 50})

I didn't find an open garbage report at 16th and Mission, but I can't rule one out.
...
- My search is by neighborhood only. I can't search by intersection or exact location.
```

**After**
```
Question: I want to report garbage near 16th and Mission. Has it already been reported?
  [tool] recent_similar_requests({'category': 'Street and Sidewalk Cleaning', 'neighborhood': 'Mission', 'street': '16th St'})
  [tool] recent_similar_requests({'category': 'Street and Sidewalk Cleaning', 'neighborhood': 'Mission', 'street': 'Mission St', 'limit': 25})

Probably yes. There's an open report at the intersection itself.

**Exact match**
- Request #202000220330 is for garbage and debris at "Intersection 16th St, Mission St". It was filed 2026-10-25 and is still open.

**Nearby open reports**
These are other open garbage and debris reports on the same two streets. I can't measure distance, so I can't tell you how close any of them are to your spot.
- On 16th St, there are 23 open reports in the Mission. My list showed only 10 of them, so it's partial. Most of those 10 were filed 10/24–10/25. The ones with street numbers are in the 2859–2895 16th St block and at 3074 and 2199 16th St. Two more are at 16th St and Potrero Ave.
- On Mission St, there are 15 open reports, and my list showed all of them. Two are at intersections close to yours: 17th St and Mission St (#202000223406, filed 10/25) and 14th St and Mission St (#202000225470, filed 10/26). Others are at street numbers such as 2208, 2239, 2255, 2294, 2337, 2369 and 2416 Mission St.

**What to do next**
- If your garbage is at the 16th and Mission corner, the existing report likely covers it. You can reference #202000220330 instead of filing a new one.
- If it's a bit away from the corner, for example mid-block or at a different address, a new report may be worth filing.

I searched the "Street and Sidewalk Cleaning" category, which is where garbage and debris reports go. If you meant an overflowing public trash can, that falls under "Litter Receptacle Maintenance". I can check that category too, and I can also give you the typical closing time for these reports.
...
```

</details>

## Example: closing times
```
Question: How long do street defects usually take to get closed in the Tenderloin?
  [tool] typical_resolution_time({'category': 'Street Defect', 'neighborhood': 'Tenderloin'})

In the Tenderloin, street defect requests typically take about 2.8 days to
close. That is the median, based on 398 cases filed 30-180 days ago. About 90%
of those cases have been closed. The median only covers cases that closed, so
the remaining 10% aren't reflected in it. "Closed" means the city closed the
case, not necessarily that the defect was fixed.
```

## How it works
Claude is given three fixed tools instead of writing its own queries. Category
and neighborhood are restricted to lists of values I pulled from the dataset,
so Claude can only request data that exists. The street filter cleans input
against a character whitelist and matches on street-name boundaries (so "6TH ST"
doesn't match "16TH ST"). The system prompt tells Claude to say "closed" and
not "fixed," to mention the share of cases closed, and to report counts
neutrally without speculating about people or neighborhoods.

## What I learned about the data
- **Recent cases are mostly still open.** About 71% of the newest 1,000 cases
  were open, so closing times computed on recent data would look misleadingly
  fast. Resolution times use only cases filed 30-180 days ago.
- **"Closed" doesn't always mean "fixed."** Some cases close with notes like
  "Case Resolved - WASTE NOT FOUND."
- **Some columns are patchy.** `service_details` was filled on about 59% of
  rows, and about 10,800 cases in a year have no neighborhood.
- **Newer records are formatted differently** (ID style, subtype naming). I
  noticed this but haven't investigated why.
- **No reporter description.** `status_notes` is the city's resolution note,
  not what the person who filed wrote, so matching happens on category, not
  free text.

## Limitations
- The duplicate check matches street names in address text. It doesn't measure
  distance, and it can't tell whether an open report is the *same* issue.
- Medians only include cases that closed.
- Cases with no neighborhood are excluded from neighborhood questions.
- Each question is answered independently, with no conversation memory.
- Results can include street addresses from the public dataset. The tool
  doesn't collect or store anything about the person asking.

## Testing
I wrote 12 test questions covering counts, resolution times, duplicate checks,
and questions the assistant should decline. `eval.py` checks (1) that Claude
chose the right tool with the right inputs and (2) for count questions, that
the number in the answer matches a direct query of the data.

**Result: 12/12 passed** (run October 2026; output in `eval_results.txt`).
The set is small and written by me. It checks tool choice and counts, but not
the quality of the written explanations or the accuracy of the resolution-time
and duplicate-check answers.


## Project files
- `assistant.py`: chat loop and Claude tool definitions
- `tools.py`: the three data functions, with input validation
- `eval.py`: the 12-question test set (results in `eval_results.txt`)
- `explore_311.py`, `check_recent.py`, `list_values.py`: scripts I used to
  inspect the dataset before designing the tools
- `test_claude.py`, `test_tools.py`: quick checks while building
- `NOTES.md`: working notes on the data

## Setup
Requires Python 3.9+ and an Anthropic API key.

```bash
git clone https://github.com/cameronines/sf311-assistant.git
cd sf311-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your-key-here" > .env
python assistant.py     # interactive questions
python eval.py          # run the test set
```

## Next steps
- Search by exact location (lat/long) instead of street-name text
- Grade resolution-time and duplicate-check answers, and grow the test set
- A simple web interface