# Fantasy Football Optimizer

Automated weekly ESPN Fantasy Football lineup optimizer that runs every **Wednesday** via GitHub Actions and posts a clean lineup & free-agent upgrade report as a **GitHub Issue**.

## What It Checks (Default ESPN Rules)

Default ESPN starting lineup: `1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 D/ST, 1 K`.

Every Wednesday (after waivers clear), the optimizer:
1. **Flags Bye Weeks & Injuries** — Alerts you if any starter is on a bye week (`BYE`), ruled out (`OUT`, `IR`, `DOUBTFUL`, `SUSPENSION`), or carrying a `QUESTIONABLE` tag.
2. **Solves Your Optimal Starting Lineup** — Computes the highest-projected-points valid lineup from your active roster (including `FLEX` assignment) and outputs Start/Sit swaps with point gains.
3. **Finds Free Agent Upgrades** — Scans healthy, non-bye ESPN free agents at each position and highlights any player projected to outscore your current optimal starter (with a suggested drop candidate).

---

## Quick Start (Local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run a demo right away without ESPN credentials using `--mock`:

```bash
python -m ff_optimizer --mock
```

Run against your live ESPN league:

```bash
cp .env.example .env
# Edit .env with your ESPN_LEAGUE_ID, ESPN_TEAM_ID (or ESPN_TEAM_NAME), ESPN_S2, and ESPN_SWID
python -m ff_optimizer --output report.md
```

### CLI Options

| Flag | Description |
| --- | --- |
| `--week <N>` | Override the target NFL week (defaults to the league's current week) |
| `--min-gain <pts>` | Minimum projected point gain to recommend a free agent (default: `0.5`) |
| `--output <path>` | Write the Markdown report to a file |
| `--mock` | Run with built-in sample data (no ESPN API call) |

---

## GitHub Actions Setup (Weekly Wednesday Automation)

The workflow in `.github/workflows/weekly-optimizer.yml` runs automatically every **Wednesday at 14:00 UTC** (9:00 AM EST / 10:00 AM EDT) and opens a GitHub Issue labeled `weekly-report`.

### 1. Add Repository Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Required | Description |
| --- | --- | --- |
| `ESPN_LEAGUE_ID` | Yes | Numeric league ID from your ESPN league URL (`leagueId=...`) |
| `ESPN_TEAM_ID` | Yes* | Your numeric team ID (or set `ESPN_TEAM_NAME` instead) |
| `ESPN_TEAM_NAME` | Yes* | Exact team name (used if `ESPN_TEAM_ID` is not set) |
| `ESPN_YEAR` | No | NFL season year (defaults to current season) |
| `ESPN_S2` | Private leagues | `espn_s2` browser cookie |
| `ESPN_SWID` | Private leagues | `SWID` browser cookie (including `{...}` braces) |
| `MIN_POINT_GAIN` | No | Minimum point gain for free agent alerts (default: `0.5`) |

### 2. How to Find `espn_s2` and `SWID` (Private Leagues)

1. Log in to [ESPN Fantasy Football](https://fantasy.espn.com) in your browser.
2. Open Developer Tools (`Cmd+Option+I` on macOS or `F12` on Windows/Linux).
3. Go to **Application → Cookies → `https://fantasy.espn.com`** (Firefox: **Storage → Cookies**).
4. Copy the values of `espn_s2` and `SWID` (keep the curly braces `{...}` in `SWID`).

### 3. Test Manually in GitHub Actions

Go to **Actions → Weekly Fantasy Football Lineup Optimizer → Run workflow**. You can check **Run with sample mock data** first to verify Issue creation before adding your ESPN secrets.

---

## Running Tests

```bash
pytest -v
```
