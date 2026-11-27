"""Unit tests for the core lineup optimizer and free-agent analyzer."""

from ff_optimizer.models import Player
from ff_optimizer.optimizer import (
    find_starter_alerts,
    optimize_team,
    solve_optimal_lineup,
)


def _p(
    pid: int,
    name: str,
    pos: str,
    pts: float,
    slot: str = "BE",
    injury: str = "ACTIVE",
    bye: bool = False,
    team: str = "NFL",
    owned: float = 50.0,
) -> Player:
    return Player(
        player_id=pid,
        name=name,
        position=pos,
        pro_team=team,
        projected_points=pts,
        lineup_slot=slot,
        injury_status=injury,
        on_bye_week=bye,
        percent_owned=owned,
    )


def _baseline_roster():
    return [
        _p(1, "Starter QB", "QB", 20.0, slot="QB"),
        _p(2, "Starter RB1", "RB", 16.0, slot="RB"),
        _p(3, "Starter RB2", "RB", 13.0, slot="RB"),
        _p(4, "Starter WR1", "WR", 17.0, slot="WR"),
        _p(5, "Starter WR2", "WR", 14.0, slot="WR"),
        _p(6, "Starter TE", "TE", 10.0, slot="TE"),
        _p(7, "Starter FLEX", "WR", 12.0, slot="FLEX"),
        _p(8, "Starter DST", "D/ST", 8.0, slot="D/ST"),
        _p(9, "Starter K", "K", 8.0, slot="K"),
        _p(10, "Bench QB", "QB", 16.0, slot="BE"),
        _p(11, "Bench RB", "RB", 11.0, slot="BE"),
        _p(12, "Bench WR", "WR", 9.0, slot="BE"),
    ]


def test_bye_week_starter_flagged_and_replaced():
    roster = _baseline_roster()
    # Put Starter QB on bye
    roster[0] = _p(1, "Starter QB", "QB", 22.0, slot="QB", bye=True)

    result = optimize_team("Test Team", week=8, roster=roster, free_agents_by_pos={})

    assert any(a.reason == "BYE" and a.player.name == "Starter QB" for a in result.alerts)
    qb_slot = next(a for a in result.optimal_starters if a.slot == "QB")
    assert qb_slot.player is not None
    assert qb_slot.player.name == "Bench QB"
    assert len(result.swaps) == 1
    assert result.swaps[0].start_player.name == "Bench QB"
    assert result.swaps[0].sit_player.name == "Starter QB"
    assert result.swaps[0].point_gain == 16.0


def test_injured_out_starter_flagged_and_replaced():
    roster = _baseline_roster()
    roster[1] = _p(2, "Starter RB1", "RB", 18.0, slot="RB", injury="OUT")

    result = optimize_team("Test Team", week=8, roster=roster, free_agents_by_pos={})

    assert any(
        a.reason == "INJURED_OUT" and a.severity == "CRITICAL" and a.player.name == "Starter RB1"
        for a in result.alerts
    )
    rb_names = {a.player.name for a in result.optimal_starters if a.slot == "RB" and a.player}
    assert "Bench RB" in rb_names
    assert "Starter RB1" not in rb_names


def test_questionable_starter_gets_warning_but_stays_eligible():
    roster = _baseline_roster()
    roster[3] = _p(4, "Starter WR1", "WR", 17.5, slot="WR", injury="QUESTIONABLE")

    alerts = find_starter_alerts(roster)
    assert len(alerts) == 1
    assert alerts[0].reason == "QUESTIONABLE"
    assert alerts[0].severity == "WARNING"

    optimal, _ = solve_optimal_lineup(roster)
    starter_names = {a.player.name for a in optimal if a.player}
    assert "Starter WR1" in starter_names


def test_flex_slot_picks_highest_remaining_rb_wr_te():
    roster = _baseline_roster()
    # Both TEs outscore Starter FLEX (12.0), so the second TE should start in FLEX
    roster[5] = _p(6, "Starter TE", "TE", 13.5, slot="TE")
    roster.append(_p(13, "Bench TE", "TE", 15.5, slot="BE"))

    result = optimize_team("Test Team", week=8, roster=roster, free_agents_by_pos={})

    te_slot = next(a for a in result.optimal_starters if a.slot == "TE")
    flex_slot = next(a for a in result.optimal_starters if a.slot == "FLEX")
    assert {te_slot.player.name, flex_slot.player.name} == {"Starter TE", "Bench TE"}
    assert result.optimal_projected_total > result.current_projected_total


def test_free_agent_upgrades_respect_threshold_and_filter_unavailable():
    roster = _baseline_roster()
    free_agents = {
        "K": [
            _p(101, "Injured FA K", "K", 12.0, slot="FA", injury="OUT"),
            _p(102, "Bye FA K", "K", 11.5, slot="FA", bye=True),
            _p(103, "Healthy FA K", "K", 10.5, slot="FA"),
        ],
        "QB": [
            # Only +0.2 gain, below min_point_gain=0.5
            _p(104, "Marginal FA QB", "QB", 20.2, slot="FA"),
        ],
        "D/ST": [
            _p(105, "Hot FA DST", "D/ST", 11.0, slot="FA"),
        ],
    }

    result = optimize_team(
        "Test Team",
        week=8,
        roster=roster,
        free_agents_by_pos=free_agents,
        min_point_gain=0.5,
    )

    fa_names = [u.free_agent.name for u in result.free_agent_upgrades]
    assert "Healthy FA K" in fa_names
    assert "Hot FA DST" in fa_names
    assert "Injured FA K" not in fa_names
    assert "Bye FA K" not in fa_names
    assert "Marginal FA QB" not in fa_names

    k_upgrade = next(u for u in result.free_agent_upgrades if u.slot == "K")
    assert k_upgrade.point_gain == 2.5
    assert k_upgrade.suggested_drop is not None
    assert k_upgrade.suggested_drop.name == "Starter K"
    assert result.with_fa_projected_total == round(result.optimal_projected_total + 2.5 + 3.0, 2)


def test_empty_slot_filled_by_free_agent_when_no_bench_backup():
    roster = [p for p in _baseline_roster() if p.position != "K"]
    roster.append(_p(9, "Bye K", "K", 9.0, slot="K", bye=True))

    free_agents = {
        "K": [_p(201, "Stream K", "K", 8.5, slot="FA")],
    }
    result = optimize_team(
        "Test Team", week=8, roster=roster, free_agents_by_pos=free_agents
    )

    k_slot = next(a for a in result.optimal_starters if a.slot == "K")
    assert k_slot.player is None
    assert len(result.free_agent_upgrades) == 1
    assert result.free_agent_upgrades[0].free_agent.name == "Stream K"
    assert result.free_agent_upgrades[0].point_gain == 8.5
