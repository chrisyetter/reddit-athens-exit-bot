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

## Self-hosting with Docker / Portainer

The bot ships as a small container image, published to GitHub Container Registry
by CI (`.github/workflows/docker-publish.yml`) on every push to `main`. It runs
as a background worker — no exposed ports — and restarts itself automatically on
reboot.

**One-time: make the image pullable by your NAS.** After the first CI run
succeeds, the package `ghcr.io/<you>/reddit-athens-exit-bot` exists. Either make
it public (GitHub → your profile → Packages → the package → Package settings →
Change visibility → Public) so no registry login is needed, or keep it private
and add GHCR registry credentials in Portainer.

**Deploy in Portainer:**
1. **Stacks → Add stack → Web editor**, and paste the contents of
   [`docker-compose.yml`](docker-compose.yml).
2. Under **Environment variables**, add your Reddit values: `REDDIT_CLIENT_ID`,
   `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`,
   `REDDIT_USER_AGENT`. Leave `DRY_RUN` at its default (`true`) for the first run.
3. **Deploy the stack.** Check the container logs — you should see
   `Authenticated as u/<bot>` and `Watching submissions/comments`.
4. When the logs look right, set `DRY_RUN=false` in the stack's environment
   variables and redeploy to go live.

Notes:
- `restart: unless-stopped` means Docker starts the bot automatically whenever
  the NAS / Docker / Portainer restarts — no manual intervention.
- **Run exactly one instance.** Two would both reply and double-post.
- Dedup state (`replied.json`) and the heartbeat live on the `athens-loop-bot-data`
  volume, so the bot never re-replies after a restart.
- A `HEALTHCHECK` reports health to Portainer from the bot's heartbeat; if a
  Reddit stream silently wedges, an internal watchdog exits so Docker restarts it.

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Main bot — streams r/Athens submissions + comments, posts replies |
| `exits.py` | Exit list data + matching logic + reply formatting |
| `healthcheck.py` | Container health probe (reads the heartbeat file) |
| `test_matcher.py` | Offline sanity checks for the matcher |
| `Dockerfile` | Builds the container image |
| `docker-compose.yml` | Portainer stack definition (self-hosting) |
| `.github/workflows/docker-publish.yml` | CI: build & publish image to GHCR |
| `.env.example` | Template for credentials/config (local runs) |
| `replied.json` | Auto-created; tracks already-answered items |

## Notes & etiquette

- **Read [r/Athens rules](https://www.reddit.com/r/Athens/about/rules/) first**
  and consider messaging the mods — many subreddits require bots to be approved.
- New Reddit accounts have low rate limits and may be auto-flagged as spam;
  let the account age and build a little karma before going live.
- Tune the trigger words in `exits.py` (`_LOOP_CONTEXT`) and the `roads` lists
  if you see false positives/negatives in the dry-run logs.
- To run it continuously, deploy the container (see *Self-hosting with Docker /
  Portainer* above), or use `nohup` / `tmux` / a `systemd` service on any
  always-on host.
