#!/usr/bin/env python3
"""
Athens Loop exit bot.

Monitors r/Athens for new posts and comments that mention a specific exit on
the Athens Loop (GA 10 Loop) and replies with a clarification of the exit
number and destination roads.

Run a dry run first (no replies posted, matches printed to console):
    DRY_RUN=true python bot.py

Go live (actually post replies) by setting DRY_RUN=false in your .env.
"""

import os
import sys
import time
import json
import signal
import threading
import logging

import praw
import prawcore
from dotenv import load_dotenv

from exits import find_matches, build_reply

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("athens-loop-bot")

SUBREDDIT = os.getenv("SUBREDDIT", "Athens")
DRY_RUN = os.getenv("DRY_RUN", "true").strip().lower() not in ("false", "0", "no")
STATE_FILE = os.getenv("STATE_FILE", "replied.json")
# On startup, scan submissions from the last N days before watching live.
# 0 disables backfill. Reddit's API only exposes ~1000 newest posts, so very
# large values are silently capped by what the API will return.
BACKFILL_DAYS = float(os.getenv("BACKFILL_DAYS", "0") or "0")

# Watchdog: if a stream stops updating its heartbeat for this many seconds
# (network wedge, silent hang), exit non-zero so the container's restart policy
# brings us back. 0 disables the watchdog.
WATCHDOG_TIMEOUT = float(os.getenv("WATCHDOG_TIMEOUT", "600") or "0")
# Optional file the watchdog writes the freshest heartbeat to, for an external
# Docker HEALTHCHECK to read. Empty disables it.
HEARTBEAT_FILE = os.getenv("HEARTBEAT_FILE", "")

# Simple persistent record of things we've already replied to, so a restart
# doesn't double-post.
_state_lock = threading.Lock()

# Per-stream last-alive timestamps, updated by the stream loops and watched by
# the watchdog thread.
_heartbeats = {}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_state(replied):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(replied), f)


def build_reddit():
    required = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME",
                "REDDIT_PASSWORD", "REDDIT_USER_AGENT"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        log.error("Copy .env.example to .env and fill it in. See README.md.")
        sys.exit(1)

    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
    # Triggers an auth check early so misconfiguration fails fast.
    me = reddit.user.me()
    log.info("Authenticated as u/%s", me)
    return reddit, str(me)


def handle_item(item, kind, text, replied, bot_username):
    """Check one submission/comment, reply if it mentions an exit."""
    fullname = item.fullname  # e.g. t3_abc / t1_xyz

    with _state_lock:
        if fullname in replied:
            return

    # Don't reply to our own content.
    author = getattr(item, "author", None)
    if author and str(author).lower() == bot_username.lower():
        return

    matches = find_matches(text)
    if not matches:
        return

    reply_body = build_reply(matches)
    exits_hit = ", ".join(m["exit"]["exit"] for m in matches)
    link = f"https://reddit.com{item.permalink}"
    log.info("MATCH on %s %s (exits %s) -> %s", kind, fullname, exits_hit, link)

    if DRY_RUN:
        log.info("[DRY_RUN] Would reply:\n%s\n", reply_body)
    else:
        try:
            item.reply(reply_body)
            log.info("Replied to %s", fullname)
        except prawcore.exceptions.PrawcoreException as e:
            log.error("Failed to reply to %s: %s", fullname, e)
            return
        # Be gentle with rate limits.
        time.sleep(5)

    with _state_lock:
        replied.add(fullname)
        # In a dry run we track in-memory (to avoid duplicate logging within the
        # same run) but never persist, so a dry run doesn't cause the later live
        # run to skip these items.
        if not DRY_RUN:
            save_state(replied)


def backfill_submissions(reddit, replied, bot_username, days):
    """Scan submissions from the last `days` days, oldest-relevant first.

    Reddit's listing API caps out around the 1000 newest posts, so if `days`
    reaches further back than that we simply process as many as the API returns.
    """
    cutoff = time.time() - days * 86400
    sub = reddit.subreddit(SUBREDDIT)
    log.info("Backfilling submissions from the last %.0f day(s)...", days)

    scanned = 0
    hit_cutoff = False
    posts = []
    for post in sub.new(limit=None):
        scanned += 1
        if post.created_utc < cutoff:
            hit_cutoff = True
            break
        posts.append(post)

    # Process oldest -> newest so replies read chronologically.
    for post in reversed(posts):
        text = f"{post.title}\n\n{post.selftext or ''}"
        handle_item(post, "submission", text, replied, bot_username)

    if not hit_cutoff:
        log.warning(
            "Backfill reached the end of what Reddit's API exposes (%d posts) "
            "before hitting the %.0f-day cutoff; older posts are not retrievable.",
            scanned, days,
        )
    log.info("Backfill complete (scanned %d submissions).", scanned)


def stream_submissions(reddit, replied, bot_username):
    sub = reddit.subreddit(SUBREDDIT)
    log.info("Watching submissions in r/%s", SUBREDDIT)
    # pause_after=-1 yields None as soon as we're caught up, so the loop keeps
    # ticking (and updating the heartbeat) even when nothing new is posted.
    for post in sub.stream.submissions(skip_existing=True, pause_after=-1):
        _heartbeats["submissions"] = time.time()
        if post is None:
            continue
        text = f"{post.title}\n\n{post.selftext or ''}"
        handle_item(post, "submission", text, replied, bot_username)


def stream_comments(reddit, replied, bot_username):
    sub = reddit.subreddit(SUBREDDIT)
    log.info("Watching comments in r/%s", SUBREDDIT)
    for comment in sub.stream.comments(skip_existing=True, pause_after=-1):
        _heartbeats["comments"] = time.time()
        if comment is None:
            continue
        handle_item(comment, "comment", comment.body, replied, bot_username)


def watchdog():
    """Force a restart if any stream goes stale, and (optionally) publish a
    heartbeat file for an external Docker HEALTHCHECK."""
    while True:
        time.sleep(30)
        now = time.time()
        if HEARTBEAT_FILE and _heartbeats:
            try:
                with open(HEARTBEAT_FILE, "w") as f:
                    f.write(str(min(_heartbeats.values())))
            except OSError as e:
                log.warning("Could not write heartbeat file: %s", e)
        if WATCHDOG_TIMEOUT <= 0:
            continue
        for name, ts in list(_heartbeats.items()):
            if now - ts > WATCHDOG_TIMEOUT:
                log.error(
                    "Watchdog: '%s' stream stale for %.0fs (> %.0fs); exiting "
                    "for the container to restart.", name, now - ts, WATCHDOG_TIMEOUT,
                )
                os._exit(1)


def run_stream(target, name, *args):
    """Run a stream in a loop, recovering from transient network errors."""
    while True:
        try:
            target(*args)
        except prawcore.exceptions.PrawcoreException as e:
            log.warning("%s stream error: %s; reconnecting in 30s", name, e)
            time.sleep(30)
        except Exception:
            log.exception("%s stream crashed; reconnecting in 30s", name)
            time.sleep(30)


def _handle_sigterm(signum, _frame):
    # Docker/Portainer sends SIGTERM on stop; exit promptly so we don't wait for
    # the 10s SIGKILL grace period.
    log.info("Received signal %s; shutting down.", signum)
    sys.exit(0)


def main():
    log.info("Starting Athens Loop bot (DRY_RUN=%s)", DRY_RUN)
    signal.signal(signal.SIGTERM, _handle_sigterm)
    reddit, bot_username = build_reddit()
    replied = load_state()
    log.info("Loaded %d previously-replied items", len(replied))

    if BACKFILL_DAYS > 0:
        backfill_submissions(reddit, replied, bot_username, BACKFILL_DAYS)

    threads = [
        threading.Thread(
            target=run_stream,
            args=(stream_submissions, "submissions", reddit, replied, bot_username),
            daemon=True,
        ),
        threading.Thread(
            target=run_stream,
            args=(stream_comments, "comments", reddit, replied, bot_username),
            daemon=True,
        ),
        threading.Thread(target=watchdog, daemon=True),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
