import requests
import pandas as pd
from datetime import datetime, timedelta
import re

URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"

VALID_CATEGORIES = [
    "Street and Sidewalk Cleaning", "Parking Enforcement", "Graffiti Public",
    "General Request", "Encampment", "Graffiti Private", "Noise",
    "Blocked Street and Sidewalk", "Tree Maintenance", "RPD General", "Sewer",
    "Sidewalk and Curb", "Street Defect", "Litter Receptacle Maintenance",
    "MTA Parking Traffic Signs Normal Priority", "Damage Property",
    "Muni Service Feedback", "Muni Employee Feedback", "Streetlights",
    "Residential Building", "Illegal Postings",
    "MTA Parking Traffic Signs High Priority", "Autonomous Vehicle Complaints",
    "Shared Spaces Request", "Taxi Complaint", "Water Quality",
    "Temporary Sign Applications", "Waste of Water",
]

VALID_NEIGHBORHOODS = [
    "Mission", "South of Market", "Tenderloin", "Bayview Hunters Point",
    "Hayes Valley", "Nob Hill", "Castro/Upper Market", "Sunset/Parkside",
    "Financial District/South Beach", "Haight Ashbury", "Bernal Heights",
    "Outer Richmond", "Marina", "Western Addition", "Excelsior",
    "West of Twin Peaks", "Inner Sunset", "Pacific Heights", "Noe Valley",
    "Inner Richmond", "Outer Mission", "Russian Hill",
    "Oceanview/Merced/Ingleside", "North Beach", "Lone Mountain/USF",
    "Portola", "Chinatown", "Mission Bay", "Potrero Hill", "Golden Gate Park",
    "Visitacion Valley", "Presidio Heights", "Glen Park", "Japantown",
    "Lakeshore", "Twin Peaks", "McLaren Park", "Seacliff", "Treasure Island",
    "Presidio", "Lincoln Park",
]


def _check(category, neighborhood):
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    if neighborhood not in VALID_NEIGHBORHOODS:
        raise ValueError(f"Unknown neighborhood: {neighborhood}")


def _days_ago(days):
    moment = datetime.now() - timedelta(days=days)
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


STREET_WORDS = {
    "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "ROAD": "RD",
    "DRIVE": "DR", "PLACE": "PL", "COURT": "CT", "LANE": "LN",
    "TERRACE": "TER", "HIGHWAY": "HWY",
}


def _clean_street(street):
    """Make a street name safe and match how DataSF writes addresses."""
    cleaned = street.upper().strip().replace("'", "").replace(".", "")
    if not re.fullmatch(r"[A-Z0-9 -]{2,40}", cleaned):
        raise ValueError(f"Street name has unusual characters: {street}")
    words = [STREET_WORDS.get(w, w) for w in cleaned.split()]
    return " ".join(words)


def _get(params):
    resp = requests.get(URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def count_requests(category, neighborhood, days=30):
    """How many requests of this type were filed in this neighborhood?"""
    _check(category, neighborhood)
    where = (
        f"service_name = '{category}' "
        f"AND analysis_neighborhood = '{neighborhood}' "
        f"AND requested_datetime > '{_days_ago(days)}'"
    )
    rows = _get({"$select": "count(*) as n", "$where": where})
    return {"category": category, "neighborhood": neighborhood,
            "days": days, "count": int(rows[0]["n"])}


def recent_similar_requests(category, neighborhood, days=14, limit=10, street=None):
    """Still-open requests of this type nearby: a duplicate check.
    Optionally narrow to one street name."""
    _check(category, neighborhood)
    days = min(int(days), 365)
    limit = min(int(limit), 50)
    where = (
        f"service_name = '{category}' "
        f"AND analysis_neighborhood = '{neighborhood}' "
        f"AND status_description = 'Open' "
        f"AND requested_datetime > '{_days_ago(days)}'"
    )
    if street:
        s = _clean_street(street)
        where += (
            f" AND (upper(address) like '% {s}%' "
            f"OR upper(address) like '{s}%')"
        )
    total = int(_get({"$select": "count(*) as n", "$where": where})[0]["n"])
    rows = _get({
        "$select": "service_request_id, requested_datetime, service_subtype, address",
        "$where": where,
        "$order": "requested_datetime DESC",
        "$limit": limit,
    })
    return {
        "category": category,
        "neighborhood": neighborhood,
        "street_filter": street,
        "total_matching": total,
        "shown": len(rows),
        "open_requests": rows,
    }


def typical_resolution_time(category, neighborhood):
    """Median days to close, using only cases filed 30-180 days ago."""
    _check(category, neighborhood)
    where = (
        f"service_name = '{category}' "
        f"AND analysis_neighborhood = '{neighborhood}' "
        f"AND requested_datetime > '{_days_ago(180)}' "
        f"AND requested_datetime < '{_days_ago(30)}'"
    )
    rows = _get({
        "$select": "requested_datetime, closed_date",
        "$where": where,
        "$limit": 20000,
    })
    if not rows:
        return {"cases_checked": 0}
    df = pd.DataFrame(rows).reindex(columns=["requested_datetime", "closed_date"])
    df["requested_datetime"] = pd.to_datetime(df["requested_datetime"])
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
    closed = df.dropna(subset=["closed_date"]).copy()
    days_to_close = (closed["closed_date"] - closed["requested_datetime"]).dt.total_seconds() / 86400
    days_to_close = days_to_close[days_to_close >= 0]
    return {
        "cases_checked": len(df),
        "hit_row_limit": len(rows) >= 20000,
        "share_closed": round(len(closed) / len(df), 2),
        "median_days_to_close": round(float(days_to_close.median()), 1)
        if len(days_to_close) else None,
    }