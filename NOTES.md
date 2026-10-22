# 311 Project Notes

## Dataset
- DataSF 311 Cases, dataset ID vw6y-z8j6 (updates nightly)
- Free API, no key needed

## Column map (what I use)
- Category: service_name (subtypes in service_subtype, service_details)
- Neighborhood: analysis_neighborhood
- Date opened: requested_datetime
- Date closed: closed_date
- Status: status_description (Open / Closed)
- Location: lat, long, address
- Resolution note: status_notes (the city's note, NOT the reporter's description)

## Findings
- Data is fresh: newest case was from the previous night
- Roughly 100 new cases per hour citywide
- Fill rates: category, status, address ~100%; neighborhood and coordinates ~98%; service_details only ~59%
- About 71% of the newest cases are still open, so recent data makes closure times look misleadingly fast. For resolution times I only use cases filed 30-180 days ago.
- "Closed" does not always mean "fixed" (e.g. "Case Resolved - WASTE NOT FOUND")
- About 10,800 cases in the past year have no neighborhood

## Ideas / to do
- Connect the three tools in tools.py to Claude
- Write 15-20 test questions with known answers
- README: add limitations and a privacy note