#!/usr/bin/env python3
"""Harvest co-author network pages for the subject via Vidwan SPA.

Reads co-author names from the subject profile, searches each name on the
Vidwan /profiles SPA (via the phone bridge when requests is bot-walled), then
screens each co-author page with the engine identity gate and attaches the
hits as sources via /api/research/add-source.

Vidwan-specific; replace the discover* mappers for other registries.
"""
import re
import sys
import time
import urllib.parse

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient  # noqa: E402

import requests  # noqa: E402
sys.path.insert(0, "/home/ubuntu/Expeei/wikimaker")
import json  # noqa: E402
from engine.models import PersonProfile  # noqa: E402
from engine.coauthor_network import coauthor_source_batch  # noqa: E402

API = "http://localhost:3890/api"


def harvest_coauthors(session_id: str, coauthor_names: list[str]) -> dict:
    data = requests.get(f"{API}/session/{session_id}", timeout=10).json()
    prof = data.get("profile", data)
    model = PersonProfile.model_validate(prof)
    c = MobileBrowserClient()
    added = dropped = 0
    out_text = []
    for nm in coauthor_names[:40]:
        q = "https://vidwan.inflibnet.ac.in/profiles?q=" + nm.replace(" ", "+")
        try:
            c.navigate(q, wait_seconds=12)
            time.sleep(5)
            r = c.scrape(q, wait_seconds=18)
            tst = (r.get("content") or {}).get("text", "")
        except Exception as e:
            print("  !", nm, str(e)[:40], flush=True)
            continue
        links = [lk for lk in (r.get("content") or {}).get("links", []) if "/profile/" in lk.get("href", "")]
        if not links:
            continue
        # take first matching link (name resolved)
        target = links[0]["href"]
        try:
            c.navigate(f"https://vidwan.inflibnet.ac.in{links[0]['href']}", wait_seconds=12)
        except Exception:
            pass
        try:
            time.sleep(5)
            pr = c.scrape(links[0]["href"], wait_seconds=20)
            body = (pr.get("content") or {})
            got = coauthor_source_batch(model, [(links[0]["href"], (pr.get("content") or {}).get("text", ""))])
            for src in got:
                res = requests.post(f"{API}/research/add-source", json={
                    "profile_name": session_id, "url": payload_url(src.url),
                    "title": src.title, "text": f"{src.snippet}\n\n(identity: {src.identity_status}; {src.identity_note})"}, timeout=15)
                added += 1
                print(f"  + {src.url[:60]} status {res.status_code}", flush=True)
            dropped += 0
        except Exception as e:
            print("  e:", nm[:30], str(e)[:50], flush=True)
    return {"added": added}


def payload_url(u):
    return u


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "py-prem-singh-yadav-569e5aea"
    names = [
        "Bhabani Das", "Prakash Narayan Dwivedi", "Maharaj Singh", "Jai Sunder",
        "A V S R Swamy", "V K Garg", "D V Amla", "S N Singh", "Ranjan Banerji", "B S Dixit",
    ]
    res = coauthor_harvest(sid, names)
    print(res)
