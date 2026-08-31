#!/usr/bin/env python3
"""
Run this script LOCALLY to pull fresh real data from CDC/Nextstrain APIs
and overwrite backend/seed/signals_seed.json.

Usage (from the backend/ directory):
    python scripts/pull_fixtures.py

APIs used (all public, no auth required for basic access):
  - CDC Socrata: NWSS wastewater + TGS variant proportions
  - ReliefWeb: epidemic events
  - Nextstrain charon: H5N1 + Mpox sequence counts
  - WHO DON RSS: outbreak declarations

The output file is committed to git so Render always has seed data.
"""

import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

OUT = Path(__file__).parent.parent / "seed" / "signals_seed.json"

NWSS_URL  = "https://data.cdc.gov/resource/g653-rqe2.json"
TGS_URL   = "https://data.cdc.gov/resource/k4ax-4dxf.json"   # TGS variant data
RW_URL    = "https://api.reliefweb.int/v1/disasters"
NST_BASE  = "https://nextstrain.org/charon/getDataset"

SOCRATA_LIMIT = 5000


async def pull_nwss(client: httpx.AsyncClient) -> list[dict]:
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    rows = []
    try:
        r = await client.get(
            NWSS_URL,
            params={
                "$where": f"date_end >= '{cutoff}'",
                "$select": "wwtp_jurisdiction,wwtp_id,reporting_jurisdiction,sample_location,detect_prop_15d,date_end",
                "$limit": SOCRATA_LIMIT,
                "$order": "date_end DESC",
            },
            timeout=30,
        )
        r.raise_for_status()
        for rec in r.json():
            try:
                val = float(rec.get("detect_prop_15d") or 0)
                rows.append({
                    "source": "nwss",
                    "site_id": f"nwss-{rec.get('wwtp_id','unk')}",
                    "site_name": rec.get("reporting_jurisdiction"),
                    "pathogen": "SARS-CoV-2",
                    "signal_date": rec.get("date_end", "")[:10],
                    "metric": "detect_prop_15d",
                    "value": val,
                    "unit": "proportion",
                    "region": rec.get("wwtp_jurisdiction", "").lower(),
                })
            except (ValueError, TypeError):
                continue
        print(f"NWSS: {len(rows)} rows")
    except Exception as e:
        print(f"NWSS FAILED: {e}")
    return rows


async def pull_tgs(client: httpx.AsyncClient) -> list[dict]:
    cutoff = (date.today() - timedelta(days=60)).isoformat()
    rows = []
    try:
        r = await client.get(
            TGS_URL,
            params={
                "$where": f"collection_date >= '{cutoff}'",
                "$select": "airport,collection_date,variant,share",
                "$limit": SOCRATA_LIMIT,
                "$order": "collection_date DESC",
            },
            timeout=30,
        )
        r.raise_for_status()
        for rec in r.json():
            try:
                val = float(rec.get("share") or 0)
                airport = rec.get("airport", "unk").lower().replace(" ", "-")
                rows.append({
                    "source": "tgs",
                    "site_id": f"tgs-{airport}",
                    "site_name": rec.get("airport"),
                    "pathogen": f"SARS-CoV-2 / {rec.get('variant','?')}",
                    "signal_date": rec.get("collection_date", "")[:10],
                    "metric": "variant_proportion",
                    "value": val,
                    "unit": "proportion",
                    "region": "us_airports",
                })
            except (ValueError, TypeError):
                continue
        print(f"TGS: {len(rows)} rows")
    except Exception as e:
        print(f"TGS FAILED: {e}")
    return rows


async def pull_reliefweb(client: httpx.AsyncClient) -> list[dict]:
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    rows = []
    try:
        payload = {
            "appid": "biothreat-radar-fixtures",
            "limit": 50,
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "type.name", "value": "Epidemic"},
                    {"field": "date.created", "value": {"from": cutoff}, "operator": ">="},
                ],
            },
            "fields": {"include": ["name", "date", "country", "type", "glide"]},
            "sort": ["date.created:desc"],
        }
        r = await client.post(RW_URL, json=payload, timeout=20)
        r.raise_for_status()
        for item in r.json().get("data", []):
            fields = item.get("fields", {})
            name = fields.get("name", "Unknown Event")
            dt   = (fields.get("date") or {}).get("created", date.today().isoformat())[:10]
            countries = fields.get("country", [])
            region = countries[0].get("iso3", "global").lower() if countries else "global"
            rows.append({
                "source": "hmp",
                "site_id": f"rw-{item['id']}",
                "site_name": name,
                "pathogen": _classify(name),
                "signal_date": dt,
                "metric": "event_count",
                "value": 1.0,
                "unit": "event",
                "region": region,
            })
        print(f"ReliefWeb: {len(rows)} rows")
    except Exception as e:
        print(f"ReliefWeb FAILED: {e}")
    return rows


def _classify(name: str) -> str:
    name_l = name.lower()
    if "cholera" in name_l: return "Cholera"
    if "mpox" in name_l or "monkeypox" in name_l: return "Mpox"
    if "ebola" in name_l: return "Ebola"
    if "dengue" in name_l: return "Dengue"
    if "h5n1" in name_l or "avian influenza" in name_l: return "H5N1"
    if "marburg" in name_l: return "Marburg"
    if "lassa" in name_l: return "Lassa"
    return "Unknown"


async def pull_nextstrain(client: httpx.AsyncClient) -> list[dict]:
    rows = []
    datasets = [
        ("H5N1", ["/avian-flu/h5n1/ha", "/avian-flu/h5n1", "/flu/avian/h5n1"], "h5n1_sequences"),
        ("Mpox", ["/mpox/all-clades", "/mpox/mpxv", "/mpox/clade-iib"], "mpox_sequences"),
    ]
    for pathogen, prefixes, metric in datasets:
        for prefix in prefixes:
            try:
                r = await client.get(
                    NST_BASE,
                    params={"prefix": prefix, "type": "tree"},
                    timeout=20,
                    headers={"Accept": "application/json"},
                )
                if r.status_code != 200:
                    continue
                tips = r.json().get("tree", {}).get("terminals", [])
                if not tips:
                    # Try counting nodes in the tree
                    tree = r.json().get("tree", {})
                    tips = [tree] if tree else []
                count = len(tips)
                if count > 0:
                    rows.append({
                        "source": "nst",
                        "site_id": f"nst-{pathogen.lower()}-global",
                        "site_name": f"Nextstrain {pathogen} Global",
                        "pathogen": pathogen,
                        "signal_date": date.today().isoformat(),
                        "metric": metric,
                        "value": float(count),
                        "unit": "sequences",
                        "region": "global",
                    })
                    print(f"Nextstrain {pathogen}: {count} sequences (prefix {prefix})")
                    break
            except Exception:
                continue
        else:
            print(f"Nextstrain {pathogen}: all prefixes failed")
    return rows


async def main():
    print("Pulling fixture data from public APIs...\n")
    all_rows = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "BiothreatRadar/1.0"},
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(
            pull_nwss(client),
            pull_tgs(client),
            pull_reliefweb(client),
            pull_nextstrain(client),
            return_exceptions=True,
        )
    for r in results:
        if isinstance(r, list):
            all_rows.extend(r)

    # Deduplicate
    seen = set()
    deduped = []
    for row in all_rows:
        key = (row["source"], row["site_id"], row["signal_date"], row["metric"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    if not deduped:
        print("\nNo data pulled — keeping existing fixture file.")
        sys.exit(1)

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(deduped, f, indent=2)

    print(f"\nWrote {len(deduped)} rows to {OUT}")
    print("Commit seed/signals_seed.json and push to deploy with fresh data.")


if __name__ == "__main__":
    asyncio.run(main())
