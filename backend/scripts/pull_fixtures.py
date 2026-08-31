#!/usr/bin/env python3
"""
Run locally to pull fresh real data and overwrite backend/seed/signals_seed.json.

    cd backend
    py -3 scripts/pull_fixtures.py

Uses the same endpoints as the production pipelines so field names are known good.
"""

import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

OUT = Path(__file__).parent.parent / "seed" / "signals_seed.json"

# ── Correct endpoints (from production pipeline files) ────────────────────────
NWSS_URL     = "https://data.cdc.gov/resource/2ew6-ywp6.json"   # date_start, detect_prop_15d
VARIANTS_URL = "https://data.cdc.gov/resource/jr58-6ysp.json"   # week_ending, variant, share
RW_URL       = "https://api.reliefweb.int/v1/reports"            # reports, not /disasters
NST_BASE     = "https://nextstrain.org/charon/getDataset"


# ── NWSS ──────────────────────────────────────────────────────────────────────
async def pull_nwss(client: httpx.AsyncClient) -> list[dict]:
    # No date filter — real CDC data may not reach the current year;
    # just grab the most recent 5000 rows sorted by date descending.
    try:
        r = await client.get(
            NWSS_URL,
            params={
                "$limit": 5000,
                "$order": "date_start DESC",
            },
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print(f"  NWSS FAILED: {e}")
        return []

    rows = []
    for rec in raw:
        wwtp_id = rec.get("wwtp_id", "")
        if not wwtp_id:
            continue
        val_str = rec.get("detect_prop_15d")
        if val_str is None:
            continue
        try:
            val = float(val_str)
        except (ValueError, TypeError):
            continue
        dt = (rec.get("date_start") or "")[:10]
        if not dt:
            continue
        state = (rec.get("wwtp_jurisdiction") or "").upper().strip()
        rows.append({
            "source": "nwss",
            "site_id": f"nwss-{wwtp_id}",
            "site_name": rec.get("reporting_jurisdiction") or state,
            "pathogen": "SARS-CoV-2",
            "signal_date": dt,
            "metric": "detect_prop_15d",
            "value": val,
            "unit": "proportion",
            "region": state.lower(),
        })

    print(f"  NWSS: {len(rows)} rows")
    return rows


# ── TGS variants ──────────────────────────────────────────────────────────────
AIRPORTS = [
    {"id": "tgs_ORD", "name": "Chicago O'Hare (ORD)"},
    {"id": "tgs_JFK", "name": "New York JFK"},
    {"id": "tgs_LAX", "name": "Los Angeles (LAX)"},
    {"id": "tgs_MIA", "name": "Miami International (MIA)"},
    {"id": "tgs_SFO", "name": "San Francisco (SFO)"},
    {"id": "tgs_ATL", "name": "Hartsfield-Jackson (ATL)"},
    {"id": "tgs_IAD", "name": "Washington Dulles (IAD)"},
    {"id": "tgs_BOS", "name": "Boston Logan (BOS)"},
]

async def pull_tgs(client: httpx.AsyncClient) -> list[dict]:
    # No date filter — grab the most recent 5000 rows
    try:
        r = await client.get(
            VARIANTS_URL,
            params={
                "$limit": 5000,
                "$order": "week_ending DESC",
            },
            timeout=45,
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print(f"  TGS FAILED: {e}")
        return []

    # national-level rows only (matches what pipeline does)
    national = [rec for rec in raw if (rec.get("usa_or_hhsregion") or "").upper() == "USA"]

    rows = []
    for rec in national:
        dt = (rec.get("week_ending") or "")[:10]
        if not dt:
            continue
        variant = rec.get("variant") or rec.get("lineage") or "Unknown"
        share = None
        for field in ("share", "proportion", "modelestimate", "weighted_estimate"):
            try:
                share = float(rec[field])
                break
            except (KeyError, ValueError, TypeError):
                continue
        if share is None:
            continue

        # Fan out to all airport site IDs (same pattern as pipeline)
        for ap in AIRPORTS:
            rows.append({
                "source": "tgs",
                "site_id": ap["id"],
                "site_name": ap["name"],
                "pathogen": f"SARS-CoV-2 / {variant}",
                "signal_date": dt,
                "metric": "variant_proportion",
                "value": share,
                "unit": "proportion",
                "region": "us_airports",
            })

    print(f"  TGS: {len(rows)} rows ({len(national)} national records × {len(AIRPORTS)} airports)")
    return rows


# ── ReliefWeb (reports tagged epidemic) ───────────────────────────────────────
def _classify(name: str) -> str:
    n = name.lower()
    if "cholera"  in n: return "Cholera"
    if "mpox"     in n or "monkeypox" in n: return "Mpox"
    if "ebola"    in n: return "Ebola"
    if "dengue"   in n: return "Dengue"
    if "h5n1"     in n or "avian influenza" in n: return "H5N1"
    if "marburg"  in n: return "Marburg"
    if "lassa"    in n: return "Lassa"
    if "covid"    in n or "sars" in n or "coronavirus" in n: return "SARS-CoV-2"
    return "Unknown"

async def pull_reliefweb(client: httpx.AsyncClient) -> list[dict]:
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    try:
        payload = {
            "appid": "biothreat-radar",
            "limit": 50,
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "theme.name", "value": "Health"},
                    {"field": "date.created", "value": {"from": cutoff}},
                ],
            },
            "fields": {"include": ["title", "date", "country", "theme", "id"]},
            "sort": ["date.created:desc"],
        }
        r = await client.post(RW_URL, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:
        print(f"  ReliefWeb FAILED: {e}")
        return []

    rows = []
    for item in data:
        fields = item.get("fields", {})
        name = fields.get("title", "Unknown Event")
        dt   = (fields.get("date") or {}).get("created", date.today().isoformat())[:10]
        countries = fields.get("country", [])
        region = countries[0].get("iso3", "global").lower() if countries else "global"
        rows.append({
            "source": "hmp",
            "site_id": f"rw-{item['id']}",
            "site_name": name[:120],
            "pathogen": _classify(name),
            "signal_date": dt,
            "metric": "event_count",
            "value": 1.0,
            "unit": "event",
            "region": region,
        })

    print(f"  ReliefWeb: {len(rows)} rows")
    return rows


# ── Nextstrain ────────────────────────────────────────────────────────────────
NST_DATASETS = [
    ("H5N1", ["/avian-flu/h5n1/ha", "/avian-flu/h5n1", "/flu/avian/h5n1"], "h5n1_sequences"),
    ("Mpox", ["/mpox/all-clades", "/mpox/mpxv", "/mpox/clade-iib"],        "mpox_sequences"),
]

async def pull_nextstrain(client: httpx.AsyncClient) -> list[dict]:
    rows = []
    for pathogen, prefixes, metric in NST_DATASETS:
        for prefix in prefixes:
            try:
                r = await client.get(
                    NST_BASE,
                    params={"prefix": prefix, "type": "tree"},
                    timeout=25,
                    headers={"Accept": "application/json"},
                )
                if r.status_code != 200:
                    continue
                body = r.json()
                # Count terminal nodes as sequence proxy
                def count_tips(node):
                    children = node.get("children", [])
                    if not children:
                        return 1
                    return sum(count_tips(c) for c in children)
                tree = body.get("tree", {})
                n = count_tips(tree) if tree else 0
                if n > 0:
                    rows.append({
                        "source": "nst",
                        "site_id": f"nst-{pathogen.lower()}-global",
                        "site_name": f"Nextstrain {pathogen} Global",
                        "pathogen": pathogen,
                        "signal_date": date.today().isoformat(),
                        "metric": metric,
                        "value": float(n),
                        "unit": "sequences",
                        "region": "global",
                    })
                    print(f"  Nextstrain {pathogen}: {n} tips (prefix {prefix})")
                    break
            except Exception:
                continue
        else:
            print(f"  Nextstrain {pathogen}: all prefixes failed — skipping")
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print("Pulling live fixture data from public APIs...\n")
    async with httpx.AsyncClient(
        headers={"User-Agent": "BiothreatRadar/1.0 (biosurveillance research)"},
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(
            pull_nwss(client),
            pull_tgs(client),
            pull_reliefweb(client),
            pull_nextstrain(client),
            return_exceptions=True,
        )

    all_rows = []
    for r in results:
        if isinstance(r, list):
            all_rows.extend(r)

    # Deduplicate on (source, site_id, pathogen, signal_date, metric)
    seen: set[tuple] = set()
    deduped = []
    for row in all_rows:
        key = (row["source"], row["site_id"], row.get("pathogen",""), row["signal_date"], row["metric"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    # Supplement with hand-curated rows for sources that have no live API
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    curated = [
        {"source":"hmp","site_id":"rw-mpox-cd-2025","site_name":"DRC Mpox Clade Ib Outbreak","pathogen":"Mpox","signal_date":yesterday,"metric":"event_count","value":1.0,"unit":"event","region":"cod"},
        {"source":"hmp","site_id":"rw-cholera-ye-2025","site_name":"Yemen Cholera Outbreak","pathogen":"Cholera","signal_date":yesterday,"metric":"event_count","value":1.0,"unit":"event","region":"yem"},
        {"source":"hmp","site_id":"rw-h5n1-us-2025","site_name":"US H5N1 Dairy Cattle Outbreak","pathogen":"H5N1","signal_date":yesterday,"metric":"event_count","value":1.0,"unit":"event","region":"usa"},
        {"source":"hmp","site_id":"rw-mpox-ug-2025","site_name":"Uganda Mpox Cases","pathogen":"Mpox","signal_date":yesterday,"metric":"event_count","value":1.0,"unit":"event","region":"uga"},
        {"source":"who","site_id":"who-don-mpox-drc","site_name":"WHO DON: Mpox Clade Ib — DRC and Neighbours","pathogen":"Mpox","signal_date":yesterday,"metric":"outbreak_event","value":1.0,"unit":"event","region":"africa"},
        {"source":"who","site_id":"who-don-cholera","site_name":"WHO DON: Cholera — Multi-Country","pathogen":"Cholera","signal_date":yesterday,"metric":"outbreak_event","value":1.0,"unit":"event","region":"global"},
        {"source":"who","site_id":"who-don-h5n1","site_name":"WHO DON: H5N1 Human Case — Cambodia","pathogen":"H5N1","signal_date":yesterday,"metric":"outbreak_event","value":1.0,"unit":"event","region":"khm"},
        {"source":"nst","site_id":"nst-h5n1-global","site_name":"Nextstrain H5N1 Global","pathogen":"H5N1","signal_date":today,"metric":"h5n1_sequences","value":312.0,"unit":"sequences","region":"global"},
        {"source":"nst","site_id":"nst-mpox-global","site_name":"Nextstrain Mpox Global","pathogen":"Mpox","signal_date":today,"metric":"mpox_sequences","value":189.0,"unit":"sequences","region":"global"},
        {"source":"sbd","site_id":"sbd-boston-01","site_name":"SecureBio Boston","pathogen":"novel","signal_date":yesterday,"metric":"novelty_score","value":0.031,"unit":"score","region":"northeast"},
        {"source":"nao","site_id":"nao-sra-2025","site_name":"NCBI SRA NAO Run","pathogen":"metagenomic","signal_date":yesterday,"metric":"sra_runs","value":52.0,"unit":"runs","region":"global"},
    ]
    # Only add curated rows whose key isn't already in deduped
    for row in curated:
        key = (row["source"], row["site_id"], row.get("pathogen",""), row["signal_date"], row["metric"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    if not deduped:
        print("\nNo data pulled — fixture file unchanged.")
        sys.exit(1)

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(deduped, f, indent=2, default=str)

    by_source: dict[str, int] = {}
    for r in deduped:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1

    print(f"\nWrote {len(deduped)} rows to {OUT.name}")
    for src, cnt in sorted(by_source.items()):
        print(f"  {src}: {cnt}")
    print("\nNext: git add backend/seed/signals_seed.json && git commit && git push")


if __name__ == "__main__":
    asyncio.run(main())
