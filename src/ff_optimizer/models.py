"""Domain models for players, alerts, lineup swaps, and optimization results."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ff_optimizer.config import (
    BENCH_SLOTS,
    FLEX_ELIGIBLE_POSITIONS,
    UNAVAILABLE_INJURY_STATUSES,
    WARNING_INJURY_STATUSES,
)


@dataclass(frozen=True)
class Player:
    """Normalized representation of an NFL fantasy player for a target week."""

    player_id: int
    name: str
    position: str
    pro_team: str
    projected_points: float
    lineup_slot: str = "FA"
    eligible_slots: Tuple[str, ...] = ()
    injury_status: str = "ACTIVE"
    on_bye_week: bool = False
    percent_owned: float = 0.0

    @property
    def normalized_injury_status(self) -> str:
        status = (self.injury_status or "ACTIVE").strip().upper()
        return status if status else "ACTIVE"

    @property
    def is_injured_out(self) -> bool:
        return self.normalized_injury_status in UNAVAILABLE_INJURY_STATUSES

    @property
    def is_questionable(self) -> bool:
        return self.normalized_injury_status in WARNING_INJURY_STATUSES

    @property
    def is_unavailable(self) -> bool:
        return self.on_bye_week or self.is_injured_out

    @property
    def effective_projected_points(self) -> float:
        """Return 0.0 if the player is on bye or ruled out, else projected points."""
        if self.is_unavailable:
            return 0.0
        return max(0.0, round(float(self.projected_points), 2))

    @property
    def is_starter(self) -> bool:
        return self.lineup_slot not in BENCH_SLOTS and self.lineup_slot != "FA"

    def can_fill_slot(self, slot: str) -> bool:
        """Check whether this player is eligible to start in the given ESPN slot."""
        if slot == "FLEX":
            return (
                self.position in FLEX_ELIGIBLE_POSITIONS
                or "FLEX" in self.eligible_slots
                or "RB/WR/TE" in self.eligible_slots
            )
        return self.position == slot or slot in self.eligible_slots

    @property
    def status_label(self) -> str:
        """Human-readable status tag for reports."""
        if self.on_bye_week:
            return "BYE"
        status = self.normalized_injury_status
        if status in ("ACTIVE", "NORMAL"):
            return "Healthy"
        return status


@dataclass(frozen=True)
class SlotAssignment:
    """A single starting lineup slot paired with its assigned player (or None)."""

    slot: str
    player: Optional[Player]


@dataclass(frozen=True)
class Alert:
    """Warning or critical alert for a starter on bye or carrying an injury tag."""

    player: Player
    reason: str  # "BYE", "INJURED_OUT", "QUESTIONABLE"
    severity: str  # "CRITICAL", "WARNING"
    message: str


@dataclass(frozen=True)
class LineupSwap:
    """Recommended start/sit swap between current roster players."""

    slot: str
    sit_player: Optional[Player]
    start_player: Player
    point_gain: float
    reason: str


@dataclass(frozen=True)
class FreeAgentUpgrade:
    """Recommended free agent pickup projected to outscore a rostered starter."""

    position: str
    slot: str
    free_agent: Player
    current_player: Optional[Player]
    point_gain: float
    suggested_drop: Optional[Player]
    reason: str


@dataclass
class OptimizationResult:
    """Complete weekly optimization analysis for a fantasy team."""

    team_name: str
    week: int
    current_starters: List[SlotAssignment] = field(default_factory=list)
    optimal_starters: List[SlotAssignment] = field(default_factory=list)
    bench: List[Player] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    swaps: List[LineupSwap] = field(default_factory=list)
    free_agent_upgrades: List[FreeAgentUpgrade] = field(default_factory=list)
    current_projected_total: float = 0.0
    optimal_projected_total: float = 0.0
    with_fa_projected_total: float = 0.0
