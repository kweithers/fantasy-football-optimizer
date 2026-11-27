"""Unit tests for the ESPN API client adapter using fake espn-api objects."""

from types import SimpleNamespace

import pytest

from ff_optimizer.config import OptimizerConfig
from ff_optimizer.espn_client import ESPNClient


def _fake_box_player(
    pid,
    name,
    pos,
    pro_team,
    proj,
    slot="BE",
    injury="ACTIVE",
    bye=False,
    owned=50.0,
):
    return SimpleNamespace(
        playerId=pid,
        name=name,
        position=pos,
        proTeam=pro_team,
        projected_points=proj,
        slot_position=slot,
        eligibleSlots=[pos],
        injuryStatus=injury,
        on_bye_week=bye,
        percent_owned=owned,
    )


def _fake_fa(pid, name, pos, pro_team, week, proj, injury="ACTIVE", owned=40.0):
    return SimpleNamespace(
        playerId=pid,
        name=name,
        position=pos,
        proTeam=pro_team,
        stats={week: {"projected_points": proj}},
        lineupSlot="FA",
        eligibleSlots=[pos],
        injuryStatus=injury,
        on_bye_week=False,
        percent_owned=owned,
    )


def test_espn_client_fetches_box_lineup_and_free_agents():
    team_1 = SimpleNamespace(team_id=1, team_name="Touchdown Makers", roster=[])
    matchup = SimpleNamespace(
        home_team=team_1,
        away_team=SimpleNamespace(team_id=2, team_name="Rivals"),
        home_lineup=[
            _fake_box_player(1, "Patrick Mahomes", "QB", "KC", 21.5, slot="QB"),
            _fake_box_player(2, "Derrick Henry", "RB", "BAL", 17.8, slot="RB/WR/TE"),
            _fake_box_player(3, "Bye Guy", "WR", "BUF", 15.0, slot="WR", bye=True),
        ],
        away_lineup=[],
    )

    class FakeLeague:
        current_week = 9
        teams = [team_1]

        def box_scores(self, week=None):
            assert week == 9
            return [matchup]

        def free_agents(self, week=None, size=25, position=None):
            if position == "K":
                return [_fake_fa(500, "Stream Kicker", "K", "DAL", 9, 10.2)]
            return []

    cfg = OptimizerConfig(league_id=12345, year=2026, team_id=1)
    client = ESPNClient(cfg, league=FakeLeague())

    team_name, week, roster, free_agents = client.fetch_team_data()

    assert team_name == "Touchdown Makers"
    assert week == 9
    assert len(roster) == 3
    assert roster[0].projected_points == 21.5
    assert roster[1].lineup_slot == "FLEX"
    assert roster[2].on_bye_week is True
    assert len(free_agents["K"]) == 1
    assert free_agents["K"][0].projected_points == 10.2


def test_espn_client_resolves_team_by_name_case_insensitive():
    team = SimpleNamespace(team_id=7, team_name="Sunday Legends", roster=[])

    class FakeLeague:
        current_week = 4
        teams = [team]

        def free_agents(self, week=None, size=25, position=None):
            return []

    cfg = OptimizerConfig(league_id=12345, year=2026, team_name="sunday legends")
    client = ESPNClient(cfg, league=FakeLeague())
    assert client.resolve_team().team_id == 7


def test_espn_client_raises_when_team_not_found():
    class FakeLeague:
        current_week = 4
        teams = [SimpleNamespace(team_id=1, team_name="Other Team", roster=[])]

    cfg = OptimizerConfig(league_id=12345, year=2026, team_id=99)
    client = ESPNClient(cfg, league=FakeLeague())
    with pytest.raises(ValueError, match="Team ID 99 not found"):
        client.resolve_team()
