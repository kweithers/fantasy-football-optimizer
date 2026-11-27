"""Adapter wrapping the espn-api Python package for ESPN Fantasy Football."""

from typing import Any, Dict, List, Optional, Tuple

from ff_optimizer.config import FREE_AGENT_POSITIONS, OptimizerConfig
from ff_optimizer.models import Player


def _extract_projected_points(raw_player: Any, week: int) -> float:
    """Extract weekly projected points from an espn-api BoxPlayer or Player."""
    # BoxPlayer exposes weekly projected_points directly
    direct_proj = getattr(raw_player, "projected_points", None)
    if direct_proj is not None:
        try:
            return round(float(direct_proj), 2)
        except (TypeError, ValueError):
            pass

    stats = getattr(raw_player, "stats", None) or {}
    week_stats = stats.get(week) or stats.get(str(week)) or {}
    if isinstance(week_stats, dict) and "projected_points" in week_stats:
        try:
            return round(float(week_stats["projected_points"]), 2)
        except (TypeError, ValueError):
            pass

    return 0.0


def _extract_on_bye(raw_player: Any, week: int) -> bool:
    """Detect whether a player is on a bye week from espn-api attributes."""
    if getattr(raw_player, "on_bye_week", False):
        return True
    pro_opponent = getattr(raw_player, "pro_opponent", None)
    if pro_opponent == "None":
        return True
    schedule = getattr(raw_player, "schedule", None)
    if isinstance(schedule, dict) and schedule:
        week_game = schedule.get(week) or schedule.get(str(week))
        if week_game is None:
            return True
    return False


def _normalize_slot_name(slot: Optional[str]) -> str:
    if not slot:
        return "BE"
    if slot == "RB/WR/TE":
        return "FLEX"
    return str(slot)


def _to_player(raw_player: Any, week: int, default_slot: str = "BE") -> Player:
    """Convert an espn-api Player or BoxPlayer into our normalized Player model."""
    slot_raw = (
        getattr(raw_player, "slot_position", None)
        or getattr(raw_player, "lineupSlot", None)
        or default_slot
    )
    eligible = getattr(raw_player, "eligibleSlots", None) or ()
    eligible_tuple = tuple(_normalize_slot_name(str(s)) for s in eligible)

    injury_status = getattr(raw_player, "injuryStatus", None) or "ACTIVE"
    if not injury_status and getattr(raw_player, "injured", False):
        injury_status = "OUT"

    return Player(
        player_id=int(getattr(raw_player, "playerId", 0)),
        name=str(getattr(raw_player, "name", "Unknown")),
        position=str(getattr(raw_player, "position", "")),
        pro_team=str(getattr(raw_player, "proTeam", "NFL")),
        projected_points=_extract_projected_points(raw_player, week),
        lineup_slot=_normalize_slot_name(slot_raw),
        eligible_slots=eligible_tuple,
        injury_status=str(injury_status),
        on_bye_week=_extract_on_bye(raw_player, week),
        percent_owned=float(getattr(raw_player, "percent_owned", 0.0) or 0.0),
    )


class ESPNClient:
    """Fetches team rosters and free agents from an ESPN Fantasy Football league."""

    def __init__(self, config: OptimizerConfig, league: Optional[Any] = None) -> None:
        self.config = config
        self._league = league

    @property
    def league(self) -> Any:
        if self._league is None:
            if self.config.league_id is None:
                raise ValueError(
                    "ESPN_LEAGUE_ID is required to connect to ESPN Fantasy Football."
                )
            try:
                from espn_api.football import League
            except ImportError as exc:
                raise ImportError(
                    "The 'espn-api' package is required. Install with: pip install espn-api"
                ) from exc

            kwargs: Dict[str, Any] = {
                "league_id": self.config.league_id,
                "year": self.config.year,
            }
            if self.config.espn_s2 and self.config.swid:
                kwargs["espn_s2"] = self.config.espn_s2
                kwargs["swid"] = self.config.swid

            self._league = League(**kwargs)
        return self._league

    def resolve_week(self) -> int:
        if self.config.week is not None:
            return self.config.week
        return int(getattr(self.league, "current_week", 1))

    def resolve_team(self) -> Any:
        teams = getattr(self.league, "teams", [])
        if self.config.team_id is not None:
            for team in teams:
                if int(getattr(team, "team_id", -1)) == self.config.team_id:
                    return team
            raise ValueError(f"Team ID {self.config.team_id} not found in league.")

        if self.config.team_name:
            target = self.config.team_name.strip().lower()
            for team in teams:
                if str(getattr(team, "team_name", "")).strip().lower() == target:
                    return team
            raise ValueError(f"Team '{self.config.team_name}' not found in league.")

        raise ValueError("Set either ESPN_TEAM_ID or ESPN_TEAM_NAME to identify your team.")

    def fetch_team_data(self) -> Tuple[str, int, List[Player], Dict[str, List[Player]]]:
        """Fetch (team_name, week, roster, free_agents_by_pos) from ESPN."""
        week = self.resolve_week()
        team = self.resolve_team()
        team_id = int(getattr(team, "team_id"))
        team_name = str(getattr(team, "team_name", f"Team {team_id}"))

        raw_roster = self._fetch_box_lineup(team_id, week)
        if not raw_roster:
            raw_roster = list(getattr(team, "roster", []))

        roster = [_to_player(p, week, default_slot="BE") for p in raw_roster]

        free_agents_by_pos: Dict[str, List[Player]] = {}
        for pos in FREE_AGENT_POSITIONS:
            raw_fas = self.league.free_agents(
                week=week,
                size=self.config.free_agent_pool_size,
                position=pos,
            )
            free_agents_by_pos[pos] = [
                _to_player(fa, week, default_slot="FA") for fa in raw_fas
            ]

        return team_name, week, roster, free_agents_by_pos

    def _fetch_box_lineup(self, team_id: int, week: int) -> List[Any]:
        """Try to load the week's BoxPlayer lineup for accurate weekly projections & byes."""
        box_scores_fn = getattr(self.league, "box_scores", None)
        if not callable(box_scores_fn):
            return []
        try:
            matchups = box_scores_fn(week=week)
        except Exception:
            return []

        for matchup in matchups:
            home = getattr(matchup, "home_team", None)
            away = getattr(matchup, "away_team", None)
            if home is not None and int(getattr(home, "team_id", -1)) == team_id:
                return list(getattr(matchup, "home_lineup", []))
            if away is not None and int(getattr(away, "team_id", -1)) == team_id:
                return list(getattr(matchup, "away_lineup", []))
        return []
