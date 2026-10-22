import requests
import pandas as pd

URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"

resp = requests.get(URL, params={"$limit": 100}, timeout=30)
resp.raise_for_status()
df = pd.DataFrame(resp.json())

print("Columns:")
print(list(df.columns))
print()
print(df.head(5).to_string())