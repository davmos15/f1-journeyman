#!/usr/bin/env python3
"""
Journeyman — F1 dataset builder
-------------------------------
Turns the F1DB open dataset (github.com/f1db/f1db — CC-BY-4.0, rebuilt after
every race weekend) into the season-aggregated drivers.json the game consumes.

Run:  python3 build_drivers.py [drivers.json]

Downloads the f1db-csv.zip asset from the latest F1DB release, unzips it to a
temp dir, and reads three files out of it:
  f1db-seasons-drivers.csv   per-driver, per-season totals (the table rows)
  f1db-drivers.csv           career totals, nationality, championships
  f1db-races-race-results.csv per-race finishing status (for the DNF column)

Answer pool = drivers who can be the mystery driver (a real career to reveal).
Guess pool  = everyone selectable in autocomplete (broader).
Both live in one array; guess-only drivers omit `seasons` to keep the file small.

The pools built here are a deliberate SUPERSET. The game's settings sliders
(minimum starts, earliest era) filter this file client-side, so changing them
never needs a rebuild.

Constructor, championship position, points and teammate data are all present in
F1DB and all deliberately left out of the season rows — any one of them gives
the answer away.
"""
import io, json, os, sys, zipfile, tempfile
import pandas as pd
import requests

OUT = sys.argv[1] if len(sys.argv) > 1 else "drivers.json"

# Tunables -------------------------------------------------------------
GUESS_MIN_STARTS  = 10   # to appear in autocomplete
ANSWER_MIN_STARTS = 20   # to be a possible answer (client filters up from here)
ANSWER_MIN_SEASONS = 3   # one or two seasons makes a bad puzzle — nothing to reveal

# positionText values that mean "did not see the flag". DNQ/DNPQ/DNP are
# deliberately absent: failing to qualify isn't a retirement, and the Ent/Str
# columns already tell that story.
DNF_CODES = {"DNF", "DNS", "NC", "DSQ", "EX"}

RELEASE_API = "https://api.github.com/repos/f1db/f1db/releases/latest"
ASSET_FALLBACK = "https://github.com/f1db/f1db/releases/latest/download/f1db-csv.zip"

# nationalityCountryId is a slug; title-casing it is right for nearly all of
# them, but a handful read badly ("United States Of America").
NAT_OVERRIDE = {
    "united-states-of-america": "United States",
    "united-kingdom": "United Kingdom",
    "united-arab-emirates": "United Arab Emirates",
    "czech-republic": "Czech Republic",
    "east-germany": "East Germany",
    "west-germany": "West Germany",
    "soviet-union": "Soviet Union",
}
def nat_name(slug):
    if slug in NAT_OVERRIDE:
        return NAT_OVERRIDE[slug]
    return " ".join(w.capitalize() for w in str(slug).split("-"))


def fetch_csv_zip():
    """Resolve the latest release's f1db-csv.zip and return it as bytes."""
    url = ASSET_FALLBACK
    try:
        r = requests.get(RELEASE_API, timeout=30,
                         headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        rel = r.json()
        for a in rel.get("assets", []):
            if a["name"] == "f1db-csv.zip":
                url = a["browser_download_url"]
                break
        print(f"Latest F1DB release: {rel.get('tag_name','?')}")
    except Exception as e:
        # The API is rate-limited to 60/hr unauthenticated; the permalink below
        # always points at the newest release, so a failure here is survivable.
        print(f"Release API unavailable ({e}); using the latest-download permalink")
    print("Downloading", url, "…")
    z = requests.get(url, timeout=180)
    z.raise_for_status()
    return z.content


def tier(row):
    """The F1 equivalent of the AFL game's position chip — a one-word summary
    of how far up the grid this driver got, used as a late clue."""
    if row["totalChampionshipWins"] >= 1: return "Champion"
    if row["totalRaceWins"] >= 1:         return "Race winner"
    if row["totalPodiums"] >= 1:          return "Podium finisher"
    if row["totalPoints"] > 0:            return "Points scorer"
    return "Backmarker"


print("Fetching F1DB CSV release…")
blob = fetch_csv_zip()
with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(tmp)
    p = lambda f: os.path.join(tmp, f)
    seasons_df = pd.read_csv(p("f1db-seasons-drivers.csv"))
    drivers_df = pd.read_csv(p("f1db-drivers.csv"))
    results_df = pd.read_csv(p("f1db-races-race-results.csv"),
                             usecols=["year", "driverId", "positionText"],
                             low_memory=False)

# DNFs per driver-season, derived from the per-race finishing status.
dnf = results_df[results_df["positionText"].astype(str).isin(DNF_CODES)]
dnf = dnf.groupby(["driverId", "year"]).size().to_dict()

INT_COLS = ["totalRaceEntries", "totalRaceStarts", "totalRaceWins",
            "totalPodiums", "totalPolePositions", "totalFastestLaps"]
for c in INT_COLS:
    seasons_df[c] = pd.to_numeric(seasons_df[c], errors="coerce").fillna(0).astype(int)

# Seasons where a driver was registered but never entered a race (reserve and
# test drivers) carry no information — an all-zeros row just pads the table.
seasons_df = seasons_df[seasons_df["totalRaceEntries"] > 0]

by_driver = {}
for did, g in seasons_df.groupby("driverId"):
    rows = []
    for _, s in g.sort_values("year").iterrows():
        yr = int(s["year"])
        rows.append({
            "y": yr,
            "e": int(s["totalRaceEntries"]),
            "s": int(s["totalRaceStarts"]),
            "w": int(s["totalRaceWins"]),
            "p": int(s["totalPodiums"]),
            "q": int(s["totalPolePositions"]),
            "f": int(s["totalFastestLaps"]),
            "dnf": int(dnf.get((did, yr), 0)),
        })
    by_driver[did] = rows

drivers = []
name_counts = {}
for _, d in drivers_df.iterrows():
    seasons = by_driver.get(d["id"])
    if not seasons:
        continue
    starts = int(d["totalRaceStarts"])
    answerable = starts >= ANSWER_MIN_STARTS and len(seasons) >= ANSWER_MIN_SEASONS
    guessable  = starts >= GUESS_MIN_STARTS
    if not (answerable or guessable):
        continue

    rec = {
        "name":  str(d["name"]),
        "nat":   nat_name(d["nationalityCountryId"]),
        "first": seasons[0]["y"],
        "last":  seasons[-1]["y"],
        "starts": starts,
        "wins":   int(d["totalRaceWins"]),
        "poles":  int(d["totalPolePositions"]),
        "podiums": int(d["totalPodiums"]),
        "tier":   tier(d),
        "answer": answerable,
    }
    if answerable:
        rec["seasons"] = seasons
    drivers.append(rec)
    name_counts[rec["name"]] = name_counts.get(rec["name"], 0) + 1

# Disambiguate duplicate display names (the Verstappens, Hills, Schumachers and
# Rosbergs all come through F1DB distinct today, but a future release needn't).
for d in drivers:
    if name_counts[d["name"]] > 1:
        d["name"] = f'{d["name"]} ({d["nat"]}, {d["first"]})'

drivers.sort(key=lambda d: -d["starts"])
answers = [d for d in drivers if d["answer"]]
season_rows = sum(len(d["seasons"]) for d in answers)

json.dump(drivers, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)

print(f"\nGuess pool   {len(drivers)} drivers  (>= {GUESS_MIN_STARTS} starts)")
print(f"Answer pool  {len(answers)} drivers  (>= {ANSWER_MIN_STARTS} starts, "
      f">= {ANSWER_MIN_SEASONS} seasons), {season_rows} season rows")
# what the game's defaults actually select out of that superset
dflt = [d for d in answers if d["starts"] >= 30 and d["last"] >= 1980]
print(f"Daily pool   {len(dflt)} drivers  (game defaults: 30 starts, 1980+)")
print(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB)")
