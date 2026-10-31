#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay.py - RAHAT ke labelled messages ko backend me daalta hai.

Teen mode:
  demo   - 2 second gap. Judge ke saamne dikhane ke liye.
  story  - sirf wo ~25 messages jo demo ki kahani banate hain. 4-minute pitch ke liye.
  burst  - sab ek saath, bina ruke. Latency measure karne ke liye.

Chalane ka tareeka:
  python replay.py --mode story
  python replay.py --mode burst --file ../data/test_150.json
  python replay.py --mode demo --delay 1.5
  python replay.py --mode burst --dry-run        # backend ke bina test

urllib use kiya hai, requests nahi - taaki venue pe pip install na karna pade.
"""

import argparse, json, time, sys, os
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

DEFAULT_API = "http://localhost:8000"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(HERE, "..", "data", "messages.json")

# Demo ki kahani: ye incidents hi story mode me chalte hain.
# Har ek ek pitch point dikhata hai.
STORY = {
    "INC-01": "Akeli dadi - 5 message merge honge",
    "INC-02": "Usi jagah alag ghatna - merge NAHI hona chahiye (near-miss)",
    "FAKE-01": "Copy-paste spam - 6 numbers, same text",
    "INC-31": "Akela buzurg - ek hi message, priority girni nahi chahiye",
    "INC-14": "Rispana Pul - sabse zyada hazard",
    "INC-17": "GEHU campus shelter - khana chahiye (low priority, wait karega)",
}
STORY_NOISE = 2   # kitne noise messages beech me daalne hain


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def post(api, msg, timeout=10):
    """Ek message backend ko bhejta hai. (ok, status_or_error, seconds) return karta hai."""
    body = {
        "channel": msg["channel"],
        "received_at": msg["timestamp"],
        "sender_hash": msg["sender_id"],
        "audio_url": None,
        "raw_text": msg["raw_text"],
    }
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(api.rstrip("/") + "/messages", data=data,
                             headers={"Content-Type": "application/json"},
                             method="POST")
    t0 = time.time()
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return True, r.status, time.time() - t0
    except HTTPError as e:
        return False, "HTTP %s" % e.code, time.time() - t0
    except URLError as e:
        return False, "no connection (%s)" % e.reason, time.time() - t0
    except Exception as e:
        return False, str(e), time.time() - t0


def pick_story(msgs):
    """Story mode: sirf kahani wale messages, time ke hisaab se."""
    out = [m for m in msgs if m["true_incident_id"] in STORY]
    noise = [m for m in msgs if m["true_incident_id"] is None][:STORY_NOISE]
    return sorted(out + noise, key=lambda m: m["timestamp"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["demo", "story", "burst"], default="story")
    p.add_argument("--file", default=DEFAULT_FILE)
    p.add_argument("--api", default=DEFAULT_API)
    p.add_argument("--delay", type=float, default=2.0, help="demo mode ka gap (seconds)")
    p.add_argument("--dry-run", action="store_true", help="bhejo mat, sirf dikhao")
    args = p.parse_args()

    msgs = load(args.file)
    if args.mode == "story":
        msgs = pick_story(msgs)
        delay = args.delay
    elif args.mode == "demo":
        delay = args.delay
    else:
        delay = 0.0

    print("=" * 60)
    print("mode   :", args.mode)
    print("file   :", os.path.basename(args.file))
    print("count  :", len(msgs))
    print("api    :", args.api, "(DRY RUN)" if args.dry_run else "")
    if args.mode == "story":
        print("\nkahani:")
        for inc, why in STORY.items():
            print("  %-9s %s" % (inc, why))
    print("=" * 60 + "\n")

    sent = failed = 0
    latencies = []
    t_start = time.time()

    for i, m in enumerate(msgs, 1):
        tag = m["true_incident_id"] or "NOISE"
        preview = m["raw_text"][:52].replace("\n", " ")

        if args.dry_run:
            print("[%3d/%d] %-9s %s" % (i, len(msgs), tag, preview))
            ok = True
        else:
            ok, status, secs = post(args.api, m)
            latencies.append(secs)
            mark = "OK " if ok else "ERR"
            print("[%3d/%d] %s %-9s %5.2fs  %s" % (i, len(msgs), mark, tag, secs, preview))
            if not ok:
                print("        -> %s" % status)

        sent += 1 if ok else 0
        failed += 0 if ok else 1
        if delay and i < len(msgs):
            time.sleep(delay)

    total = time.time() - t_start
    print("\n" + "=" * 60)
    print("bheje   : %d" % sent)
    print("fail    : %d" % failed)
    print("kul time: %.1f s" % total)
    if latencies:
        latencies.sort()
        n = len(latencies)
        print("latency : avg %.2fs | p50 %.2fs | p95 %.2fs | max %.2fs" % (
            sum(latencies) / n, latencies[n // 2],
            latencies[int(n * 0.95) - 1], latencies[-1]))
    if args.mode == "burst" and not args.dry_run:
        print("\nthroughput: %.1f messages/sec" % (sent / total if total else 0))
        print("NOTE: agar Gemini free tier hai to rate limit yahan dikhega.")
    print("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
