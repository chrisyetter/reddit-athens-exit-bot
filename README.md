# Athens Loop Exit Bot

A Reddit bot that monitors [r/Athens](https://www.reddit.com/r/Athens/) for new
posts and comments that mention a specific exit on the **Athens Loop
(GA 10 Loop / US 78)** — by exit number or by a destination road name — and
replies with a clarification of the exit number and its destinations.

Exit data comes from [Wikipedia: Georgia State Route 10 Loop (Athens)](https://en.wikipedia.org/wiki/Georgia_State_Route_10_Loop_(Athens)#Exit_list).

## What it matches

To avoid spamming the subreddit (and getting banned), the bot is **precise** by design:

- ✅ Named destination roads — *Prince Avenue, College Station Rd, Milledge Ave,
  Oconee Connector, Chase Street*, etc. (abbreviations like `Rd`/`Ave`/`St` work)
- ✅ Explicit exit numbers — *"exit 7"*, *"exit 10B"*
- ✅ Highway numbers (*US 78, SR 10*) **only** when loop/exit context is nearby
- ❌ Bare *"loop"* / *"exit"* (e.g. "out of the loop", "exit the building")
- ❌ Generic place names (Atlanta, Monroe, Madison)

It replies **once per post/comment** and remembers what it has answered in
`replied.json` so restarts don't double-post.

## Setup

1. **Create a Reddit account for the bot** (don't use your personal account).

2. **Register a "script" app** at <https://www.reddit.com/prefs/apps>:
   - Click *"create another app..."*
   - Type: **script**
   - Name: anything (e.g. `athens-loop-bot`)
   - Redirect URI: `http://localhost:8080` (required but unused)
   - After creating, note the **client ID** (under the app name) and the
     **client secret**.

3. **Install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure credentials:**
   ```bash
   cp .env.example .env
   # then edit .env and fill in your values
   ```

## Running

**Dry run first** (default) — logs every match and the reply it *would* post,
but posts nothing:

```bash
python bot.py
```

Watch the log for a while to confirm it's matching sensibly. When you're happy,
set `DRY_RUN=false` in `.env` and run again to go live.

Stop with `Ctrl-C`.

## Testing the matcher

No credentials needed:

```bash
python test_matcher.py
```

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Main bot — streams r/Athens submissions + comments, posts replies |
| `exits.py` | Exit list data + matching logic + reply formatting |
| `test_matcher.py` | Offline sanity checks for the matcher |
| `.env.example` | Template for credentials/config |
| `replied.json` | Auto-created; tracks already-answered items |

## Notes & etiquette

- **Read [r/Athens rules](https://www.reddit.com/r/Athens/about/rules/) first**
  and consider messaging the mods — many subreddits require bots to be approved.
- New Reddit accounts have low rate limits and may be auto-flagged as spam;
  let the account age and build a little karma before going live.
- Tune the trigger words in `exits.py` (`_LOOP_CONTEXT`) and the `roads` lists
  if you see false positives/negatives in the dry-run logs.
- To run it continuously, use `nohup`, `tmux`, a `systemd` service, or a small
  always-on host.
