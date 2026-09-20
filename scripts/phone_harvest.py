#!/usr/bin/env python3
"""Phone-browser harvest loop for personprobe research.

Uses the Android OpenScrape bridge (MobileBrowserClient) to open URLs the
VM cannot fetch (Cloudflare/login walls), then ingests page text into the
session via add-source-paste and optionally binds a sourced claim.

Usage:
    python3 scripts/phone_harvest.py status
    python3 scripts/phone_harvest.py scrape URL [URL ...]
    python3 scripts/phone_harvest.py ingest URL --text-file /tmp/x.json --claim-field known_for --claim-text "..." [--date "2024"]
    python3 scripts/phone_harvest.py session  # source/claim counts + liveness
    python3 scripts/phone_harvest.py cleanup  # alive-fix + drop stale stubs + resume
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
sys.path.insert(0, "/home/ubuntu/Expeei/personprobe")

API = "http://127.0.0.1:3890/api"


def api_post(path: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())


def client():
    from openscrape_client import MobileBrowserClient
    return MobileBrowserClient()


def cmd_status() -> None:
    print(json.dumps(client().get_status(), indent=2))


def cmd_scrape(urls: list[str], wait: int = 25, settle: int = 8,
               out_prefix: str = "/tmp/phone_harvest") -> None:
    c = client()
    for url in urls:
        print(f"=== NAV: {url}", flush=True)
        try:
            r = c.navigate(url, wait_seconds=wait)
            print(f"  title: {(r.get('title') or '')[:90]} | captcha: {r.get('has_captcha')}",
                  flush=True)
            time.sleep(settle)
            d = c.extract_dom(include_text=True, include_links=False, include_meta=True)
            t = d.get("content", {}).get("text", "") or ""
            print(f"  LEN: {len(t)} | yadav: {'yadav' in t.lower()}", flush=True)
            fn = f"{out_prefix}_{abs(hash(url)) % 10**8}.json"
            open(fn, "w").write(json.dumps(
                {"url": url, "title": d.get("title"), "text": t}, ensure_ascii=False))
            print(f"  saved: {fn}", flush=True)
        except Exception as e:
            print(f"  ERR: {e}", flush=True)


def cmd_ingest(url: str, text_file: str, claim_field: str = "",
               claim_text: str = "", date: str | None = None) -> None:
    d = json.load(open(text_file))
    text = (d.get("text") or d.get("content", {}).get("text", ""))[:15000]
    r = api_post("/research/add-source-paste",
                 {"profile_name": session_id(), "url": url, "pasted_text": text})
    print("ingested:", r["source"]["human_verified"], "|", url[:70])
    if claim_field and claim_text:
        r2 = api_post("/research/add-sourced-claim",
                      {"profile_name": session_id(), "url": url,
                       "field": claim_field, "text": claim_text,
                       "date_context": date})
        print("claim:", json.dumps(r2)[:200])


def session_id() -> str:
    return "py-prem-singh-yadav-569e5aea"


def cmd_session() -> None:
    sys.path.insert(0, "/home/ubuntu/Expeei/personprobe")
    from backend.store import _load_session_file, SESSIONS_DIR
    from engine.models import PersonProfile
    from collections import Counter
    data = _load_session_file(SESSIONS_DIR / f"{session_id()}.json")
    p = PersonProfile(**data["profile"])
    print("sources:", len(p.sources), "| claims:", len(p.claims),
          "| live:", dict(Counter(s.liveness for s in p.sources)))


def cmd_cleanup() -> None:
    sys.path.insert(0, "/home/ubuntu/Expeei/personprobe")
    from backend.store import _load_session_file, _save_session, SESSIONS_DIR
    from engine.models import PersonProfile
    from collections import Counter
    data = _load_session_file(SESSIONS_DIR / f"{session_id()}.json")
    p = PersonProfile(**data["profile"])
    for s in p.sources:
        if (s.human_verified and (s.snippet or "").strip()
                and "sciencedirect.com" not in s.url
                and s.liveness in ("blocked", "unknown")):
            s.liveness = "alive"
    stale = ["384251538_Successful_dissemination_of_c",
             "380401610_Veer_Gaurav_buffalo_male_calf",
             "pubmed.ncbi.nlm.nih.gov/29429518/",
             "theriogenology.2020.04.003", "10495398.2023.2271030",
             "rda.70161", "SCNT-and-genome-editing-in-Buffalo,-the-black-g"]
    n0 = len(p.sources)
    p.sources = [s for s in p.sources
                 if not (not s.human_verified and any(d in s.url for d in stale))]
    for s in p.sources:
        if "ndtv.com/india-news/indias-first-cloned-assamese" in s.url and not s.human_verified:
            s.liveness = "dead"
        if "india.com/education/cirb-became" in s.url:
            s.liveness = "dead"
    _save_session(p)
    api_post("/sessions/resume", {"session_id": session_id()}, timeout=30)
    print("dropped:", n0 - len(p.sources), "| sources:", len(p.sources),
          "| live:", dict(Counter(s.liveness for s in p.sources)))


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["status"]
    if cmd == "status":
        cmd_status()
    elif cmd == "scrape":
        cmd_scrape(rest)
    elif cmd == "ingest":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("url")
        ap.add_argument("--text-file", required=True)
        ap.add_argument("--claim-field", default="")
        ap.add_argument("--claim-text", default="")
        ap.add_argument("--date", default=None)
        a = ap.parse_args(rest)
        cmd_ingest(a.url, a.text_file, a.claim_field, a.claim_text, a.date)
    elif cmd == "session":
        cmd_session()
    elif cmd == "cleanup":
        cmd_cleanup()
    else:
        sys.exit(f"unknown command: {cmd}")
