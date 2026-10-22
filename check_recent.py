import requests
import pandas as pd

URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"

KEY_COLUMNS = [
    "service_request_id", "requested_datetime", "closed_date",
    "status_description", "status_notes", "service_name",
    "service_subtype", "service_details", "address",
    "analysis_neighborhood", "supervisor_district", "lat", "long",
]

resp = requests.get(
    URL,
    params={
        "$select": ",".join(KEY_COLUMNS),
        "$order": "requested_datetime DESC",
        "$limit": 1000,
    },
    timeout=30,
)
resp.raise_for_status()
df = pd.DataFrame(resp.json()).reindex(columns=KEY_COLUMNS)

df["requested_datetime"] = pd.to_datetime(df["requested_datetime"])
df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")

print("Newest request:", df["requested_datetime"].max())
print("Oldest in this pull:", df["requested_datetime"].min())
print()
print("Fill rates (1.0 = always filled):")
print(df.notna().mean().round(2).to_string())
print()
print("Status counts:")
print(df["status_description"].value_counts().to_string())
print()
print("Top request types:")
print(df["service_name"].value_counts().head(10).to_string())