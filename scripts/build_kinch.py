#!/usr/bin/env python3
"""
Kinch Nation data builder.

Downloads the WCA TSV export, extracts national-best single/average per
(country, event, gender bucket), and writes a compact data/kinch.json.

Kinch scoring itself is done client-side (so region/gender re-scoring is
instant), this script only ships the raw national bests.
"""
import csv
import io
import json
import os
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone

EXPORT_URL = "https://www.worldcubeassociation.org/export/results/WCA_export.tsv.zip"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "kinch.json")

EVENTS = [
    "333", "222", "444", "555", "666", "777",
    "333bf", "333fm", "333oh", "clock", "minx",
    "pyram", "skewb", "sq1", "444bf", "555bf", "333mbf",
]
EVENT_SET = set(EVENTS)

# gender buckets: a=all, m, f, o=other, u=unknown/blank
def gender_bucket(g):
    g = (g or "").strip().lower()
    if g == "m":
        return "m"
    if g == "f":
        return "f"
    if g == "o":
        return "o"
    return "u"


def download_export(dest):
    req = urllib.request.Request(
        EXPORT_URL,
        headers={"User-Agent": "KinchNation/1.0 (github.com/tankuoping/kinch-nation)"},
    )
    final_url = EXPORT_URL
    with urllib.request.urlopen(req, timeout=600) as resp:
        final_url = resp.geturl()
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    return final_url


def read_tsv(zf, name):
    with zf.open(name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8", newline="")
        reader = csv.reader(text, delimiter="\t")
        header = next(reader)
        idx = {h: i for i, h in enumerate(header)}
        for row in reader:
            yield row, idx


def main():
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    print("Downloading WCA export...")
    final_url = download_export(tmp.name)
    export_name = os.path.basename(final_url.split("?")[0]) or "WCA_export.tsv.zip"
    size_mb = os.path.getsize(tmp.name) / 1e6
    print(f"Downloaded {export_name} ({size_mb:.1f} MB)")

    zf = zipfile.ZipFile(tmp.name)
    names = {n.lower(): n for n in zf.namelist()}

    def member(key):
        for low, orig in names.items():
            if key.lower() in low:
                return orig
        raise KeyError(f"{key} not found in export zip: {zf.namelist()[:10]}")

    # Countries
    countries = {}
    for row, idx in read_tsv(zf, member("Countries.tsv")):
        cid = row[idx["id"]]
        countries[cid] = {
            "name": row[idx["name"]],
            "cont": row[idx["continentId"]].lstrip("_"),
            "iso2": row[idx["iso2"]],
        }
    print(f"Countries: {len(countries)}")

    # Persons -> (country, gender bucket). subid 1 only.
    persons = {}
    for row, idx in read_tsv(zf, member("Persons.tsv")):
        if idx.get("subid") is not None and row[idx["subid"]] not in ("1", ""):
            continue
        persons[row[idx["id"]]] = (
            row[idx["countryId"]],
            gender_bucket(row[idx["gender"]]),
        )
    print(f"Persons: {len(persons)}")

    # bests[countryId][event][bucket] = [bestSingle, bestAverage]
    bests = {}

    def update(country, event, bucket, kind, value):
        ev = bests.setdefault(country, {}).setdefault(event, {})
        slot = ev.setdefault(bucket, [0, 0])
        i = 0 if kind == "s" else 1
        if slot[i] == 0 or value < slot[i]:
            slot[i] = value

    def ingest(member_name, kind):
        count = 0
        for row, idx in read_tsv(zf, member(member_name)):
            event = row[idx["eventId"]]
            if event not in EVENT_SET:
                continue
            pid = row[idx["personId"]]
            p = persons.get(pid)
            if not p:
                continue
            country, bucket = p
            if country not in countries:
                continue
            best = int(row[idx["best"]])
            if best <= 0:
                continue
            update(country, event, "a", kind, best)
            update(country, event, bucket, kind, best)
            count += 1
        print(f"{member_name}: {count} rows used")

    ingest("RanksSingle.tsv", "s")
    ingest("RanksAverage.tsv", "m")

    out_countries = []
    for cid, meta in sorted(countries.items()):
        ev = bests.get(cid)
        if not ev:
            continue
        out_countries.append({
            "id": cid,
            "name": meta["name"],
            "iso2": meta["iso2"],
            "cont": meta["cont"],
            "e": ev,
        })

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "export": export_name,
        "events": EVENTS,
        "countries": out_countries,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e3:.0f} KB, {len(out_countries)} countries)")

    os.unlink(tmp.name)


if __name__ == "__main__":
    sys.exit(main())
