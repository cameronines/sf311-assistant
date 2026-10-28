# SF 311 Assistant

A plain-language assistant for community volunteers to explore San Francisco
311 data: how many reports, what's already open, and how long cases take to close.

## Why I built this
In city cleanup volunteer shifts in SF, we are often instructed to file any items we can't clean ourselves with 311.  
Based on my Civic Joy Fund volunteer experience and speaking with other volunteers, there are many questions we wished we could find answers to before filing a 311 report.

## What it does
- Count requests by category and neighborhood
- List recent open requests (a duplicate check)
- Report typical closing times

## Example
Question: How long do street defects usually take to get closed in the Tenderloin?
  [tool] typical_resolution_time({'category': 'Street Defect', 'neighborhood': 'Tenderloin'})

In the Tenderloin, street defect requests typically take about **2.8 days** to close. That is the median, based on 398 cases filed 30–180 days ago.
About **90%** of those cases have been closed. The median only covers cases that closed, so the remaining 10% aren't reflected in it. "Closed" means the city closed the case, not necessarily that the defect was fixed.
I can also check how many street defect requests were filed recently or which ones are still open in the Tenderloin.


## How it works
Claude is given three fixed tools instead of writing its own queries. Category
and neighborhood are restricted to validated lists, so it can only request
data that exists. Data comes from DataSF's public 311 dataset.

## What I learned about the data
- Recent cases are mostly still open, so closing times only use cases filed
  30-180 days ago.
- "Closed" doesn't always mean "fixed."
- Some cases have no neighborhood.

## Limitations
- The duplicate check can't search by street or intersection yet.
- Medians only include cases that closed.
- Tested manually on a few questions, not yet a full evaluation.

## Testing
I wrote 12 test questions covering counts, resolution times, duplicate checks,
and questions the assistant should decline. `eval.py` runs them and checks
(1) that Claude chose the right tool with the right inputs and (2) for count
questions, that the number in the answer matches a direct query of the data.

Result: 12/12 passed. Limits: the set is small and written by me; it checks
tool choice and counts but does not grade the quality of the written
explanations or the accuracy of resolution-time and duplicate-check answers.
Results are in `eval_results.txt`.

## Next steps
- Search open requests by street name
- A 15-20 question evaluation set
- A Streamlit interface

## Setup
(pip install steps, and that you need an Anthropic API key in a .env file)
