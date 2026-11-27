"""Configuration and default ESPN Fantasy Football rules."""

from dataclasses import dataclass
from datetime import date
import os
from typing import Optional, Sequence, Set

# Default ESPN Fantasy Football starting lineup (9 starters)
DEFAULT_STARTING_SLOTS: Sequence[str] = (
    "QB",
    "RB",
    "RB",
    "WR",
    "WR",
    "TE",
    "FLEX",
    "D/ST",
    "K",
)

# Positions eligible to start in the standard ESPN FLEX (RB/WR/TE) slot
FLEX_ELIGIBLE_POSITIONS: Set[str] = {"RB", "WR", "TE"}

# Positions queried when scanning ESPN free agents
FREE_AGENT_POSITIONS: Sequence[str] = ("QB", "RB", "WR", "TE", "D/ST", "K")

# Primary value-driver positions emphasized in smaller leagues (e.g. 6-team leagues)
VALUE_DRIVER_POSITIONS: Set[str] = {"RB", "WR"}

# Non-starting roster slots in ESPN
BENCH_SLOTS: Set[str] = {"BE", "IR"}

# Injury statuses treated as hard-unavailable (0 effective projected points)
UNAVAILABLE_INJURY_STATUSES: Set[str] = {
    "OUT",
    "IR",
    "INJURY_RESERVE",
    "SUSPENSION",
    "SUSPENDED",
    "DOUBTFUL",
}

# Injury statuses that remain eligible to start but trigger a warning alert
WARNING_INJURY_STATUSES: Set[str] = {"QUESTIONABLE"}


def default_nfl_season_year(today: Optional[date] = None) -> int:
    """Return the active NFL season year (Jan-Mar belong to the prior season)."""
    current = today or date.today()
    return current.year - 1 if current.month <= 3 else current.year


@dataclass(frozen=True)
class OptimizerConfig:
    """Runtime configuration loaded from environment variables and CLI args."""

    league_id: Optional[int] = None
    year: int = 2026
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    espn_s2: Optional[str] = None
    swid: Optional[str] = None
    week: Optional[int] = None
    min_point_gain: float = 0.5
    free_agent_pool_size: int = 25

    @classmethod
    def from_env(
        cls,
        week: Optional[int] = None,
        min_point_gain: Optional[float] = None,
    ) -> "OptimizerConfig":
        """Build configuration from environment variables with optional overrides."""
        raw_league_id = os.getenv("ESPN_LEAGUE_ID", "").strip()
        raw_year = os.getenv("ESPN_YEAR", "").strip()
        raw_team_id = os.getenv("ESPN_TEAM_ID", "").strip()
        raw_team_name = os.getenv("ESPN_TEAM_NAME", "").strip() or None
        raw_espn_s2 = os.getenv("ESPN_S2", "").strip() or None
        raw_swid = os.getenv("ESPN_SWID", "").strip() or None
        raw_min_gain = os.getenv("MIN_POINT_GAIN", "").strip()

        resolved_gain = (
            min_point_gain
            if min_point_gain is not None
            else (float(raw_min_gain) if raw_min_gain else 0.5)
        )

        return cls(
            league_id=int(raw_league_id) if raw_league_id else None,
            year=int(raw_year) if raw_year else default_nfl_season_year(),
            team_id=int(raw_team_id) if raw_team_id else None,
            team_name=raw_team_name,
            espn_s2=raw_espn_s2,
            swid=raw_swid,
            week=week,
            min_point_gain=resolved_gain,
        )
