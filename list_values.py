import requests

URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"
SINCE = "2025-10-22T00:00:00"

def top_values(column, limit):
    resp = requests.get(
        URL,
        params={
            "$select": f"{column}, count(*) as n",
            "$where": f"requested_datetime > '{SINCE}'",
            "$group": column,
            "$order": "n DESC",
            "$limit": limit,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()

print("Request categories (service_name), past year:")
for row in top_values("service_name", 40):
    print(f"  {row.get('service_name')}: {row['n']}")

print()
print("Neighborhoods (analysis_neighborhood), past year:")
for row in top_values("analysis_neighborhood", 60):
    print(f"  {row.get('analysis_neighborhood')}: {row['n']}")