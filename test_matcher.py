"""Quick sanity checks for the matcher. Run: python test_matcher.py"""
from exits import find_matches, build_reply

SHOULD_MATCH = [
    "Anyone know if the Prince Avenue exit is backed up right now?",
    "Took the College Station Rd exit off the loop and traffic was awful.",
    "Which exit is Milledge Avenue? I always miss it.",
    "Get off at exit 7 for campus.",
    "Wreck on the loop near the US 78 / SR 10 exit.",
    "Oconee Connector exit was closed this morning.",
    "is the chase street exit open",
]

SHOULD_NOT_MATCH = [
    "I'm totally out of the loop on this, what happened?",
    "Please exit the building through the back door.",
    "Atlanta is about 70 miles away.",  # generic place name, no road/context
    "I love the new coffee shop downtown.",
    "US 78 is a long highway.",  # highway w/o loop context
    "Golden Pantry at the markoff on Oconee Street is great.",  # address, no loop context
    "Best short-term housing near Olympic Drive?",  # address, no loop context
    "The new Tractor Supply on Atlanta Highway has a dog wash.",  # address, no loop context
]

print("=== SHOULD MATCH ===")
ok = True
for t in SHOULD_MATCH:
    m = find_matches(t)
    hit = ", ".join(x["exit"]["exit"] for x in m) or "NONE"
    status = "OK " if m else "FAIL"
    if not m:
        ok = False
    print(f"[{status}] exits={hit:8} | {t}")

print("\n=== SHOULD NOT MATCH ===")
for t in SHOULD_NOT_MATCH:
    m = find_matches(t)
    status = "OK " if not m else "FAIL"
    if m:
        ok = False
    hit = ", ".join(x["exit"]["exit"] for x in m) or "none"
    print(f"[{status}] exits={hit:8} | {t}")

print("\n=== SAMPLE REPLY ===")
print(build_reply(find_matches(SHOULD_MATCH[0])))

print("\nRESULT:", "ALL PASS" if ok else "SOME FAILURES")
