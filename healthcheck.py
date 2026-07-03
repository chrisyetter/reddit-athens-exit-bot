#!/usr/bin/env python3
"""
Container health probe. Exits 0 if the bot's heartbeat file was updated
recently, 1 otherwise. Wired up via HEALTHCHECK in the Dockerfile so Portainer
shows the container as healthy/unhealthy.

The watchdog thread in bot.py writes HEARTBEAT_FILE; here we just check its age.
"""
import os
import sys
import time

HEARTBEAT_FILE = os.getenv("HEARTBEAT_FILE", "/data/heartbeat")
STALE = float(os.getenv("HEALTH_STALE_SECONDS", "300"))

try:
    with open(HEARTBEAT_FILE) as f:
        last = float(f.read().strip())
except (OSError, ValueError):
    print("no valid heartbeat yet", file=sys.stderr)
    sys.exit(1)

age = time.time() - last
if age > STALE:
    print(f"heartbeat stale ({age:.0f}s > {STALE:.0f}s)", file=sys.stderr)
    sys.exit(1)

print(f"ok (heartbeat {age:.0f}s old)")
sys.exit(0)
