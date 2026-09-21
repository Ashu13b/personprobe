# Yadav — Archive & Hindi 2025–26 pass (2026-09-21)

## Wayback / Internet Archive — BLOCKED
- `web.archive.org` root answers 200, but the CDX/availability services still return
  "Internet Archive services are temporarily offline" (checked via phone bridge and
  VM). `timetravel.mementoweb.org` is unreachable from both (returns nothing) — the
  Memento aggregator is down/dead, so it cannot substitute.
- ACTION: re-check later using the telemetry cooldown schedule; do not hammer.

## Hindi / regional press 2025–26 — NEW FIND
December-2025 cluster on the birth of cloned calf **"हिसार गौरव 2.0"** at ICAR-CIRB.
All copies carry the same team line: **"डॉ. पीएस यादव**, डॉ. धर्मेंद्र कुमार, डॉ. मीति
पुनेठा, डॉ. राकेश शर्मा, डॉ. प्रिया दहिया, मनु मांगल और डॉ. प्रदीप कुमार" — i.e.
he is named in the developing team **after his April-2025 retirement**.

| Outlet | URL | Date |
|---|---|---|
| Amar Ujala (origin) | amarujala.com/haryana/hisar/after-10-years-cloned-calf-hisar-gaurav-20-was-born-at-cirb-hisar-news-c-21-hsr1005-772851-2025-12-19 | 19 Dec 2025 |
| VartaHR | vartahr.com/hisar-gaurav-2-0-the-birth-of-the-hisar-gaurav-2-0-cloned-calf-at-the-buffalo-institute/ | Dec 2025 |
| Hindusthan Samachar | hindusthansamachar.in/Encyc/2025/12/18/Big-success-of-Hisar-scientis.php | 18 Dec 2025 |
| Live News Day (blog) | livenewsday01.blogspot.com/2025/12/20-cirb-25000.html | 20 Dec 2025 |

- Editorial origin grouped as "CIRB Hisar Gaurav 2.0 birth wire (Hindi syndication, Dec 2025)"
  so notability counts it as one origin.
- Dead in this pass: dainikstatesamachar.com (empty), pinewz.com (empty), bhaskar.com
  Gaurav-2.0 URL (404 page), Bing (anti-bot "one last step" → logged as throttle).

## Telemetry observations (engine/fetch_telemetry)
- Bing: bot challenge → host parked by `wait_time()` (15 min cooldown), `suggest_delay`
  honoured on subsequent calls.
- Google: empty renders/aborted loads occasionally; DDG-lite was the reliable engine.
- Internet Archive: not a throttle but a service outage — logged; recheck scheduled
  manually rather than retried.
