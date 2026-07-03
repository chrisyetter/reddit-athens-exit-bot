"""
Exit data for the Athens Loop (Georgia State Route 10 Loop) and the matching
logic the bot uses to decide when a Reddit post/comment is talking about a
specific exit.

Source: https://en.wikipedia.org/wiki/Georgia_State_Route_10_Loop_(Athens)#Exit_list

We deliberately match on *named local roads* and *explicit exit numbers* only.
Bare words like "loop" or "exit", and generic place names like "Atlanta" or
"Monroe", are too common in everyday r/Athens conversation and would produce
constant false positives (and get the bot banned). Highway-only destinations
(e.g. "US 78") are kept but require nearby loop/exit context to fire.
"""

import re

# Each exit: the exit label, mile marker, the full Destinations text from the
# table, and the list of *distinctive named roads* that should trigger a match
# on their own. Generic place names are intentionally left out of `roads`.
EXITS = [
    {
        "exit": "1", "mile": 1.6,
        "destinations": "US 29 south / US 78 west / SR 316 west (SR 8 west) – Atlanta, Monroe",
        "roads": [],
        "highways": ["US 29", "US 78", "SR 316", "SR 8"],
    },
    {
        "exit": "4", "mile": 6.15,
        "destinations": "US 129 south / US 441 south / SR 15 south / Timothy Road – Watkinsville, Madison",
        "roads": ["Timothy Road"],
        "highways": ["US 129", "US 441", "SR 15"],
    },
    {
        "exit": "6", "mile": 8.96,
        "destinations": "SR 15 Alt. north (Milledge Avenue)",
        "roads": ["Milledge Avenue"],
        "highways": ["SR 15 Alt"],
    },
    {
        "exit": "7", "mile": 10.75,
        "destinations": "College Station Road – University of Georgia",
        "roads": ["College Station Road"],
        "highways": [],
    },
    {
        "exit": "8", "mile": 12.63,
        "destinations": "US 78 east / US 78 Bus. west / SR 10 (Oconee Street / Lexington Road)",
        "roads": ["Oconee Street", "Lexington Road"],
        "highways": ["US 78", "SR 10"],
    },
    {
        "exit": "9", "mile": 14.84,
        "destinations": "Peter Street / Olympic Drive",
        "roads": ["Peter Street", "Olympic Drive"],
        "highways": [],
    },
    {
        "exit": "10A", "mile": 16.0,
        "destinations": "Old Hull Road",
        "roads": ["Old Hull Road"],
        "highways": [],
    },
    {
        "exit": "10B-D", "mile": 16.4,
        "destinations": "US 29 north (SR 8 east) to SR 72 east – Danielsville, Hartwell, Elberton",
        "roads": [],
        "highways": ["US 29", "SR 8", "SR 72"],
    },
    {
        "exit": "11", "mile": 17.5,
        "destinations": "North Avenue / Danielsville Road",
        "roads": ["North Avenue", "Danielsville Road"],
        "highways": [],
    },
    {
        "exit": "12", "mile": 19.0,
        "destinations": "US 441 north (SR 15) – Commerce",
        "roads": [],
        "highways": ["US 441", "SR 15"],
    },
    {
        "exit": "13", "mile": 20.4,
        "destinations": "Chase Street",
        "roads": ["Chase Street"],
        "highways": [],
    },
    {
        "exit": "14", "mile": 22.4,
        "destinations": "US 129 north (Prince Avenue / SR 15 Alt.) – Jefferson",
        "roads": ["Prince Avenue"],
        "highways": ["US 129", "SR 15 Alt"],
    },
    {
        "exit": "15", "mile": 24.1,
        "destinations": "Tallassee Road / Oglethorpe Avenue",
        "roads": ["Tallassee Road", "Oglethorpe Avenue"],
        "highways": [],
    },
    {
        "exit": "18", "mile": 28.5,
        "destinations": "US 78 Bus. / SR 10 (Atlanta Highway) – Monroe",
        "roads": ["Atlanta Highway"],
        "highways": ["US 78", "SR 10"],
    },
    {
        "exit": "20", "mile": 31.5,
        "destinations": "Oconee Connector",
        "roads": ["Oconee Connector"],
        "highways": [],
    },
]

# Common abbreviations so "College Station Rd" matches "College Station Road".
_SUFFIX_ALIASES = {
    "Road": ["Rd"],
    "Street": ["St"],
    "Avenue": ["Ave", "Av"],
    "Drive": ["Dr"],
    "Highway": ["Hwy"],
    "Connector": ["Connector"],
}

# Words that signal the conversation is actually about the loop/roadway, used
# to gate BOTH named-road and highway-number matches. This keeps genuine
# loop/traffic discussion while ignoring posts that only mention a road as a
# street address (e.g. "Golden Pantry at Oconee Street").
#
# NOTE: deliberately excludes road-type words (highway, hwy, road, street,
# avenue, drive, connector) — those appear inside the road names themselves and
# would let a match satisfy its own context requirement, defeating the gate.
_LOOP_CONTEXT = re.compile(
    r"\b("
    r"loop|exit|ramp|on[- ]?ramp|off[- ]?ramp|ga[- ]?10|sr[- ]?10|the\s+10|"
    r"bypass|perimeter|interchange|overpass|merge|detour|roadwork|construction|"
    r"traffic|gridlock|congestion|wreck|accident|crash|collision|"
    r"backed[- ]?up|back[- ]?up|backup|pileup|stalled|"
    r"closed|shut[- ]?down|blocked|debris|"
    r"eastbound|westbound|northbound|southbound"
    r")\b",
    re.IGNORECASE,
)


def _road_pattern(name):
    """Build a case-insensitive regex that also matches abbreviated suffixes."""
    parts = name.split()
    suffix = parts[-1]
    base = " ".join(parts[:-1])
    forms = [suffix]
    if suffix in _SUFFIX_ALIASES:
        forms.extend(_SUFFIX_ALIASES[suffix])
    # Allow an optional trailing period on abbreviations (Rd.) and flexible space.
    suffix_alt = "|".join(re.escape(f) for f in forms)
    if base:
        body = re.escape(base) + r"\s+(?:" + suffix_alt + r")"
    else:
        body = r"(?:" + suffix_alt + r")"
    return re.compile(r"\b" + body + r"\.?\b", re.IGNORECASE)


def _highway_pattern(name):
    """Match 'US 78', 'US-78', 'SR 15 Alt', etc."""
    # Normalize internal spaces to flexible separators.
    tokens = name.split()
    pat = r"\b" + r"[\s-]*".join(re.escape(t) for t in tokens) + r"\b"
    return re.compile(pat, re.IGNORECASE)


# Pre-compile all patterns once.
for _e in EXITS:
    _e["_road_patterns"] = [(_road_pattern(r), r) for r in _e["roads"]]
    _e["_highway_patterns"] = [(_highway_pattern(h), h) for h in _e["highways"]]

_EXIT_NUM_RE = re.compile(r"\bexit\s*#?\s*(\d+[A-Da-d-]*)\b", re.IGNORECASE)


def find_matches(text):
    """
    Return a list of match dicts for the given text. Each match is:
        {"exit": <exit dict>, "matched": <the string that matched>, "via": <"road"|"highway"|"number">}

    Explicit exit numbers ("exit 7") match unconditionally. Named roads and
    highway numbers (US 78, SR 10) only match when loop/exit context is also
    present, so a road used purely as a street address doesn't trigger.
    """
    if not text:
        return []

    matches = []
    seen_exit_labels = set()
    has_context = bool(_LOOP_CONTEXT.search(text))

    # 1) Explicit "exit N" references.
    for m in _EXIT_NUM_RE.finditer(text):
        num = m.group(1).upper().rstrip("-")
        for e in EXITS:
            if e["exit"].upper() == num and e["exit"] not in seen_exit_labels:
                matches.append({"exit": e, "matched": m.group(0), "via": "number"})
                seen_exit_labels.add(e["exit"])

    # 2) Distinctive named roads (only with loop/exit context, so a road used
    #    merely as a street address doesn't trigger a clarification).
    if has_context:
        for e in EXITS:
            if e["exit"] in seen_exit_labels:
                continue
            for pat, road in e["_road_patterns"]:
                if pat.search(text):
                    matches.append({"exit": e, "matched": road, "via": "road"})
                    seen_exit_labels.add(e["exit"])
                    break

    # 3) Highway numbers (only with loop/exit context).
    if has_context:
        for e in EXITS:
            if e["exit"] in seen_exit_labels:
                continue
            for pat, hwy in e["_highway_patterns"]:
                if pat.search(text):
                    matches.append({"exit": e, "matched": hwy, "via": "highway"})
                    seen_exit_labels.add(e["exit"])
                    break

    return matches


def build_reply(matches):
    """Compose a friendly clarification comment for the matched exits."""
    if not matches:
        return None

    # Sort by exit order as they appear in EXITS.
    order = {e["exit"]: i for i, e in enumerate(EXITS)}
    matches = sorted(matches, key=lambda m: order[m["exit"]["exit"]])

    lines = [
        "Hi! Here's a quick reference for the Athens Loop "
        "(US 78 / GA 10 Loop) exit(s) mentioned above:",
        "",
    ]
    for m in matches:
        e = m["exit"]
        lines.append(f"- **Exit {e['exit']}** (mile {e['mile']}): {e['destinations']}")
    lines += [
        "",
        "---",
        "^(I'm a bot that clarifies Athens Loop exit numbers and destinations. "
        "Source: Wikipedia – Georgia State Route 10 Loop. Reply or DM if I got something wrong.)",
    ]
    return "\n".join(lines)
