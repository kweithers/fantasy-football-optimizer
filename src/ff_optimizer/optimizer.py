"""Core lineup optimization, bye/injury alerts, and free-agent upgrade logic."""

from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

from ff_optimizer.config import (
    DEFAULT_STARTING_SLOTS,
    FLEX_ELIGIBLE_POSITIONS,
    VALUE_DRIVER_POSITIONS,
)
from ff_optimizer.models import (
    Alert,
    FreeAgentUpgrade,
    HighValueFreeAgent,
    LineupSwap,
    OptimizationResult,
    Player,
    SlotAssignment,
)

STREAMING_POSITIONS: Set[str] = {"K", "D/ST"}


def _normalize_slot(slot: str) -> str:
    if slot in ("RB/WR/TE", "FLEX"):
        return "FLEX"
    return slot


def find_starter_alerts(roster: Sequence[Player]) -> List[Alert]:
    """Identify starting players who are on a bye week or carrying injury tags."""
    alerts: List[Alert] = []
    for player in roster:
        if not player.is_starter:
            continue

        if player.on_bye_week:
            alerts.append(
                Alert(
                    player=player,
                    reason="BYE",
                    severity="CRITICAL",
                    message=(
                        f"{player.name} ({player.position}, {player.pro_team}) "
                        f"is on a BYE week in your {player.lineup_slot} slot."
                    ),
                )
            )
        if player.is_injured_out:
            alerts.append(
                Alert(
                    player=player,
                    reason="INJURED_OUT",
                    severity="CRITICAL",
                    message=(
                        f"{player.name} ({player.position}, {player.pro_team}) "
                        f"is listed as {player.normalized_injury_status} "
                        f"in your {player.lineup_slot} slot."
                    ),
                )
            )
        elif player.is_questionable and not player.on_bye_week:
            alerts.append(
                Alert(
                    player=player,
                    reason="QUESTIONABLE",
                    severity="WARNING",
                    message=(
                        f"{player.name} ({player.position}, {player.pro_team}) "
                        f"is QUESTIONABLE — check status before kickoff."
                    ),
                )
            )

    severity_order = {"CRITICAL": 0, "WARNING": 1}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 2), a.player.name))
    return alerts


def build_current_starters(
    roster: Sequence[Player],
    slots: Sequence[str] = DEFAULT_STARTING_SLOTS,
) -> List[SlotAssignment]:
    """Map the team's current starting players into the ordered starting slots."""
    remaining_starters = [p for p in roster if p.is_starter]
    assignments: List[SlotAssignment] = []

    for slot in slots:
        chosen_idx: Optional[int] = None
        for idx, player in enumerate(remaining_starters):
            if _normalize_slot(player.lineup_slot) == slot:
                chosen_idx = idx
                break

        if chosen_idx is not None:
            assignments.append(
                SlotAssignment(slot=slot, player=remaining_starters.pop(chosen_idx))
            )
        else:
            assignments.append(SlotAssignment(slot=slot, player=None))

    return assignments


def solve_optimal_lineup(
    roster: Sequence[Player],
    slots: Sequence[str] = DEFAULT_STARTING_SLOTS,
) -> Tuple[List[SlotAssignment], List[Player]]:
    """Find the exact maximum-projected-points valid starting lineup from roster."""
    available = [p for p in roster if not p.is_unavailable]
    slot_list = list(slots)
    num_slots = len(slot_list)

    # Precompute candidate lists per slot, capped at num_slots top players per slot
    candidates_per_slot: List[List[Player]] = []
    for slot in slot_list:
        eligible = [p for p in available if p.can_fill_slot(slot)]
        eligible.sort(
            key=lambda p: (
                -p.effective_projected_points,
                0 if p.is_starter else 1,
                p.player_id,
            )
        )
        candidates_per_slot.append(eligible[:num_slots])

    # Precompute optimistic upper bound from each slot index onward for pruning
    max_pts_per_slot = [
        cands[0].effective_projected_points if cands else 0.0
        for cands in candidates_per_slot
    ]
    suffix_upper_bound = [0.0] * (num_slots + 1)
    for idx in range(num_slots - 1, -1, -1):
        suffix_upper_bound[idx] = suffix_upper_bound[idx + 1] + max_pts_per_slot[idx]

    best_score: Tuple[float, int, int] = (-1.0, -1, -1)
    best_assignment: List[Optional[Player]] = [None] * num_slots
    current_assignment: List[Optional[Player]] = [None] * num_slots
    used_ids: Set[int] = set()

    def backtrack(
        idx: int,
        pts_sum: float,
        filled_count: int,
        kept_starters: int,
    ) -> None:
        nonlocal best_score, best_assignment

        if round(pts_sum + suffix_upper_bound[idx], 4) < round(best_score[0], 4):
            return

        if idx == num_slots:
            score = (round(pts_sum, 4), filled_count, kept_starters)
            if score > best_score:
                best_score = score
                best_assignment = list(current_assignment)
            return

        tried_any = False
        for player in candidates_per_slot[idx]:
            if player.player_id in used_ids:
                continue
            tried_any = True
            used_ids.add(player.player_id)
            current_assignment[idx] = player
            backtrack(
                idx + 1,
                pts_sum + player.effective_projected_points,
                filled_count + 1,
                kept_starters + (1 if player.is_starter else 0),
            )
            used_ids.remove(player.player_id)
            current_assignment[idx] = None

        # Allow leaving a slot empty if no eligible player is available (or to free a
        # multi-position player for a higher-value slot).
        if not tried_any or len(candidates_per_slot[idx]) < num_slots:
            current_assignment[idx] = None
            backtrack(idx + 1, pts_sum, filled_count, kept_starters)

    backtrack(0, 0.0, 0, 0)

    optimal_slots = [
        SlotAssignment(slot=slot_list[i], player=best_assignment[i])
        for i in range(num_slots)
    ]
    starter_ids = {a.player.player_id for a in optimal_slots if a.player is not None}
    bench = [p for p in roster if p.player_id not in starter_ids]
    bench.sort(
        key=lambda p: (
            1 if p.is_unavailable else 0,
            -p.effective_projected_points,
            p.name,
        )
    )
    return optimal_slots, bench


def _swap_reason(sit_player: Optional[Player]) -> str:
    if sit_player is None:
        return "Fills open starting slot"
    if sit_player.on_bye_week:
        return f"Replaces {sit_player.name} (BYE)"
    if sit_player.is_injured_out:
        return f"Replaces {sit_player.name} ({sit_player.normalized_injury_status})"
    return "Higher weekly projection"


def compute_lineup_swaps(
    current_starters: Sequence[SlotAssignment],
    optimal_starters: Sequence[SlotAssignment],
) -> List[LineupSwap]:
    """Generate actionable Start/Sit recommendations comparing current vs. optimal."""
    current_by_id = {
        a.player.player_id: a for a in current_starters if a.player is not None
    }
    optimal_by_id = {
        a.player.player_id: a for a in optimal_starters if a.player is not None
    }

    newly_started = [
        a for a in optimal_starters
        if a.player is not None and a.player.player_id not in current_by_id
    ]
    newly_benched = [
        a for a in current_starters
        if a.player is not None and a.player.player_id not in optimal_by_id
    ]

    remaining_benched = list(newly_benched)
    swaps: List[LineupSwap] = []

    for start_assignment in newly_started:
        start_player = start_assignment.player
        assert start_player is not None

        # Prefer pairing with a benched player at the exact same slot or position
        match_idx: Optional[int] = None
        for idx, bench_assignment in enumerate(remaining_benched):
            if bench_assignment.slot == start_assignment.slot:
                match_idx = idx
                break
        if match_idx is None:
            for idx, bench_assignment in enumerate(remaining_benched):
                b_player = bench_assignment.player
                if b_player and b_player.position == start_player.position:
                    match_idx = idx
                    break
        if match_idx is None and remaining_benched:
            match_idx = 0

        sit_player: Optional[Player] = None
        if match_idx is not None:
            sit_player = remaining_benched.pop(match_idx).player

        sit_pts = sit_player.effective_projected_points if sit_player else 0.0
        gain = round(start_player.effective_projected_points - sit_pts, 2)

        swaps.append(
            LineupSwap(
                slot=start_assignment.slot,
                sit_player=sit_player,
                start_player=start_player,
                point_gain=gain,
                reason=_swap_reason(sit_player),
            )
        )

    swaps.sort(key=lambda s: -s.point_gain)
    return swaps


def _choose_suggested_drop(
    slot: str,
    current_starter: Optional[Player],
    bench: Sequence[Player],
    already_dropped_ids: Set[int],
) -> Optional[Player]:
    """Select the lowest-value rostered player to drop for a free-agent pickup."""
    # For single-slot streaming positions (K, D/ST), prefer dropping the current starter
    # or a duplicate bench player at that same position.
    if slot in STREAMING_POSITIONS:
        same_pos_bench = [
            p for p in bench
            if p.position == slot and p.player_id not in already_dropped_ids
        ]
        if same_pos_bench:
            same_pos_bench.sort(key=lambda p: (p.effective_projected_points, p.percent_owned))
            return same_pos_bench[0]
        if current_starter and current_starter.player_id not in already_dropped_ids:
            return current_starter

    # Otherwise, pick the weakest bench player (avoid dropping a healthy star on a 1-week bye)
    candidates = [
        p for p in bench
        if p.player_id not in already_dropped_ids and p.lineup_slot != "IR"
    ]
    if not candidates:
        candidates = [p for p in bench if p.player_id not in already_dropped_ids]
    if not candidates:
        return current_starter if (current_starter and current_starter.player_id not in already_dropped_ids) else None

    candidates.sort(
        key=lambda p: (
            1 if p.on_bye_week and not p.is_injured_out else 0,
            p.projected_points,
            p.percent_owned,
            p.name,
        )
    )
    return candidates[0]


def find_free_agent_upgrades(
    optimal_starters: Sequence[SlotAssignment],
    bench: Sequence[Player],
    free_agents_by_pos: Mapping[str, Sequence[Player]],
    min_point_gain: float = 0.5,
) -> List[FreeAgentUpgrade]:
    """Find healthy, non-bye free agents projected to outscore optimal starters."""
    rostered_ids: Set[int] = {
        a.player.player_id for a in optimal_starters if a.player is not None
    } | {p.player_id for p in bench}

    used_fa_ids: Set[int] = set()
    used_drop_ids: Set[int] = set()
    upgrades: List[FreeAgentUpgrade] = []

    # Evaluate empty slots first, then lowest-projected starters first
    ordered_slots = sorted(
        optimal_starters,
        key=lambda a: (
            0 if a.player is None else 1,
            a.player.effective_projected_points if a.player else -1.0,
        ),
    )

    for assignment in ordered_slots:
        slot = assignment.slot
        if slot == "FLEX":
            pool: List[Player] = []
            for pos in sorted(FLEX_ELIGIBLE_POSITIONS):
                pool.extend(free_agents_by_pos.get(pos, ()))
        else:
            pool = list(free_agents_by_pos.get(slot, ()))

        eligible_fas = [
            fa for fa in pool
            if not fa.is_unavailable
            and fa.player_id not in rostered_ids
            and fa.player_id not in used_fa_ids
            and fa.effective_projected_points > 0
        ]
        if not eligible_fas:
            continue

        eligible_fas.sort(
            key=lambda p: (-p.effective_projected_points, -p.percent_owned, p.name)
        )
        best_fa = eligible_fas[0]

        current_player = assignment.player
        current_pts = current_player.effective_projected_points if current_player else 0.0
        gain = round(best_fa.effective_projected_points - current_pts, 2)

        if current_player is not None and gain < min_point_gain:
            continue

        used_fa_ids.add(best_fa.player_id)
        suggested_drop = _choose_suggested_drop(
            slot=slot,
            current_starter=current_player,
            bench=bench,
            already_dropped_ids=used_drop_ids,
        )
        if suggested_drop is not None:
            used_drop_ids.add(suggested_drop.player_id)

        reason = (
            f"Fills empty {slot} slot (+{gain:.1f} pts)"
            if current_player is None
            else f"Outscores {current_player.name} by +{gain:.1f} pts"
        )

        upgrades.append(
            FreeAgentUpgrade(
                position=best_fa.position,
                slot=slot,
                free_agent=best_fa,
                current_player=current_player,
                point_gain=gain,
                suggested_drop=suggested_drop,
                reason=reason,
            )
        )

    upgrades.sort(key=lambda u: -u.point_gain)
    return upgrades


def find_bench_upgrades(
    bench: Sequence[Player],
    rostered_ids: Set[int],
    free_agents_by_pos: Mapping[str, Sequence[Player]],
    exclude_fa_ids: Optional[Set[int]] = None,
    min_point_gain: float = 0.5,
) -> List[FreeAgentUpgrade]:
    """Compare healthy, non-bye free agents against bench players.

    Allows both same-position upgrades and cross-position upgrades into RB/WR
    value-driver positions. Skips IR players, healthy players on a 1-week bye,
    and widely rostered (>=75%) injured stars so stashed starters are protected.
    """
    used_fa_ids: Set[int] = set(exclude_fa_ids or ())
    upgrades: List[FreeAgentUpgrade] = []

    eligible_bench = [
        p for p in bench
        if p.lineup_slot != "IR"
        and not (p.on_bye_week and not p.is_injured_out)
        and not (p.is_injured_out and p.percent_owned >= 75.0)
    ]
    # Evaluate weakest bench players first so the best FAs pair with the biggest upgrades
    eligible_bench.sort(
        key=lambda p: (p.effective_projected_points, p.percent_owned, p.name)
    )

    for bench_player in eligible_bench:
        candidate_positions = {bench_player.position} | VALUE_DRIVER_POSITIONS
        seen_pool_ids: Set[int] = set()
        eligible_fas: List[Player] = []
        for pos in sorted(candidate_positions):
            for fa in free_agents_by_pos.get(pos, ()):
                if (
                    fa.player_id in seen_pool_ids
                    or fa.is_unavailable
                    or fa.player_id in rostered_ids
                    or fa.player_id in used_fa_ids
                    or fa.effective_projected_points <= 0
                ):
                    continue
                seen_pool_ids.add(fa.player_id)
                eligible_fas.append(fa)

        if not eligible_fas:
            continue

        eligible_fas.sort(
            key=lambda p: (
                -p.effective_projected_points,
                0 if p.position in VALUE_DRIVER_POSITIONS else 1,
                -p.percent_owned,
                p.name,
            )
        )
        best_fa = eligible_fas[0]
        gain = round(
            best_fa.effective_projected_points - bench_player.effective_projected_points,
            2,
        )
        if gain < min_point_gain:
            continue

        used_fa_ids.add(best_fa.player_id)
        if best_fa.position == bench_player.position:
            reason = f"Upgrades bench {bench_player.position} by +{gain:.1f} pts"
        else:
            reason = (
                f"Cross-position upgrade ({bench_player.position} -> {best_fa.position}, "
                f"+{gain:.1f} pts)"
            )
        upgrades.append(
            FreeAgentUpgrade(
                position=best_fa.position,
                slot="BE",
                free_agent=best_fa,
                current_player=bench_player,
                point_gain=gain,
                suggested_drop=bench_player,
                reason=reason,
            )
        )

    upgrades.sort(key=lambda u: -u.point_gain)
    return upgrades


def find_high_value_free_agents(
    rostered_ids: Set[int],
    free_agents_by_pos: Mapping[str, Sequence[Player]],
    per_pos_limits: Optional[Mapping[str, int]] = None,
    max_total: int = 8,
) -> List[HighValueFreeAgent]:
    """Highlight top available free agents across all positions, emphasizing RB/WR."""
    limits = per_pos_limits or {
        "RB": 3,
        "WR": 3,
        "QB": 1,
        "TE": 1,
        "D/ST": 1,
        "K": 1,
    }
    seen_ids: Set[int] = set()
    highlights: List[HighValueFreeAgent] = []

    for pos, limit in limits.items():
        pool = [
            fa for fa in free_agents_by_pos.get(pos, ())
            if not fa.is_unavailable
            and fa.player_id not in rostered_ids
            and fa.player_id not in seen_ids
            and fa.effective_projected_points > 0
        ]
        pool.sort(key=lambda p: (-p.effective_projected_points, -p.percent_owned, p.name))

        for fa in pool[:limit]:
            seen_ids.add(fa.player_id)
            is_driver = fa.position in VALUE_DRIVER_POSITIONS
            category = "Value Driver (RB/WR)" if is_driver else f"Top {fa.position}"
            if fa.percent_owned >= 70.0:
                note = f"Widely rostered ({fa.percent_owned:.0f}% owned)"
            elif is_driver:
                note = "High-upside RB/WR depth"
            else:
                note = f"Top available {fa.position} this week"
            highlights.append(
                HighValueFreeAgent(player=fa, category=category, note=note)
            )

    highlights.sort(
        key=lambda h: (
            0 if h.player.position in VALUE_DRIVER_POSITIONS else 1,
            -h.player.effective_projected_points,
            -h.player.percent_owned,
            h.player.name,
        )
    )
    return highlights[:max_total]


def optimize_team(
    team_name: str,
    week: int,
    roster: Sequence[Player],
    free_agents_by_pos: Mapping[str, Sequence[Player]],
    min_point_gain: float = 0.5,
    slots: Sequence[str] = DEFAULT_STARTING_SLOTS,
) -> OptimizationResult:
    """Run the complete weekly lineup and free-agent optimization pipeline."""
    alerts = find_starter_alerts(roster)
    current_starters = build_current_starters(roster, slots=slots)
    optimal_starters, bench = solve_optimal_lineup(roster, slots=slots)
    swaps = compute_lineup_swaps(current_starters, optimal_starters)
    fa_upgrades = find_free_agent_upgrades(
        optimal_starters=optimal_starters,
        bench=bench,
        free_agents_by_pos=free_agents_by_pos,
        min_point_gain=min_point_gain,
    )

    rostered_ids = {p.player_id for p in roster}
    starter_upgrade_fa_ids = {u.free_agent.player_id for u in fa_upgrades}
    bench_upgrades = find_bench_upgrades(
        bench=bench,
        rostered_ids=rostered_ids,
        free_agents_by_pos=free_agents_by_pos,
        exclude_fa_ids=starter_upgrade_fa_ids,
        min_point_gain=min_point_gain,
    )
    high_value_fas = find_high_value_free_agents(
        rostered_ids=rostered_ids,
        free_agents_by_pos=free_agents_by_pos,
    )

    current_total = round(
        sum(
            a.player.effective_projected_points
            for a in current_starters
            if a.player is not None
        ),
        2,
    )
    optimal_total = round(
        sum(
            a.player.effective_projected_points
            for a in optimal_starters
            if a.player is not None
        ),
        2,
    )
    with_fa_total = round(
        optimal_total + sum(u.point_gain for u in fa_upgrades),
        2,
    )

    return OptimizationResult(
        team_name=team_name,
        week=week,
        current_starters=current_starters,
        optimal_starters=optimal_starters,
        bench=bench,
        alerts=alerts,
        swaps=swaps,
        free_agent_upgrades=fa_upgrades,
        bench_upgrades=bench_upgrades,
        high_value_free_agents=high_value_fas,
        current_projected_total=current_total,
        optimal_projected_total=optimal_total,
        with_fa_projected_total=with_fa_total,
    )
