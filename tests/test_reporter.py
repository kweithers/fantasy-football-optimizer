"""Unit tests for the Markdown report formatter."""

from ff_optimizer.models import Player
from ff_optimizer.optimizer import optimize_team
from ff_optimizer.reporter import format_markdown_report


def test_markdown_report_contains_all_sections_and_recommendations():
    roster = [
        Player(1, "Josh Allen", "QB", "BUF", 23.4, lineup_slot="QB", on_bye_week=True),
        Player(2, "Bijan Robinson", "RB", "ATL", 18.2, lineup_slot="RB"),
        Player(3, "James Cook", "RB", "BUF", 14.0, lineup_slot="RB", injury_status="OUT"),
        Player(4, "CeeDee Lamb", "WR", "DAL", 19.5, lineup_slot="WR", injury_status="QUESTIONABLE"),
        Player(5, "Garrett Wilson", "WR", "NYJ", 15.1, lineup_slot="WR"),
        Player(6, "Travis Kelce", "TE", "KC", 11.2, lineup_slot="TE"),
        Player(7, "Chris Olave", "WR", "NO", 12.0, lineup_slot="FLEX"),
        Player(8, "Jets D/ST", "D/ST", "NYJ", 7.0, lineup_slot="D/ST"),
        Player(9, "Jake Elliott", "K", "PHI", 7.5, lineup_slot="K"),
        Player(10, "Baker Mayfield", "QB", "TB", 18.8, lineup_slot="BE"),
        Player(11, "Chuba Hubbard", "RB", "CAR", 13.4, lineup_slot="BE"),
    ]
    free_agents = {
        "K": [Player(201, "Brandon Aubrey", "K", "DAL", 10.5, lineup_slot="FA")],
    }

    result = optimize_team("Gridiron Gurus", week=10, roster=roster, free_agents_by_pos=free_agents)
    md = format_markdown_report(result)

    assert "# Week 10 Fantasy Football Lineup Report — Gridiron Gurus" in md
    assert "## Bye Week & Injury Alerts" in md
    assert "**[CRITICAL]** Josh Allen" in md
    assert "**[CRITICAL]** James Cook" in md
    assert "**[WARNING]** CeeDee Lamb" in md
    assert "## Recommended Roster Swaps (Start / Sit)" in md
    assert "Baker Mayfield" in md
    assert "Chuba Hubbard" in md
    assert "## Recommended Free Agent Upgrades" in md
    assert "Brandon Aubrey" in md
    assert "## Optimal Starting Lineup (Current Roster)" in md
    assert "## Bench" in md


def test_markdown_report_clean_state_when_no_changes_needed():
    roster = [
        Player(1, "Starter QB", "QB", "KC", 22.0, lineup_slot="QB"),
        Player(2, "Starter RB1", "RB", "SF", 18.0, lineup_slot="RB"),
        Player(3, "Starter RB2", "RB", "DET", 16.0, lineup_slot="RB"),
        Player(4, "Starter WR1", "WR", "MIN", 19.0, lineup_slot="WR"),
        Player(5, "Starter WR2", "WR", "CIN", 17.0, lineup_slot="WR"),
        Player(6, "Starter TE", "TE", "SF", 12.0, lineup_slot="TE"),
        Player(7, "Starter FLEX", "WR", "MIA", 14.0, lineup_slot="FLEX"),
        Player(8, "Starter DST", "D/ST", "BAL", 9.0, lineup_slot="D/ST"),
        Player(9, "Starter K", "K", "BAL", 9.5, lineup_slot="K"),
    ]
    result = optimize_team("Clean Team", week=5, roster=roster, free_agents_by_pos={})
    md = format_markdown_report(result)

    assert "All current starters are healthy and active this week." in md
    assert "Your current starting lineup is already optimal for your roster." in md
    assert "No available free agents are projected to outscore your optimal starters." in md
