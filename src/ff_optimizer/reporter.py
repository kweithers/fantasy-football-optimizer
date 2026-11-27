"""GitHub-Flavored Markdown report generator for weekly lineup recommendations."""

from typing import List

from ff_optimizer.models import OptimizationResult, Player


def _fmt_player(player: Player) -> str:
    return f"**{player.name}** ({player.position}, {player.pro_team})"


def format_markdown_report(result: OptimizationResult) -> str:
    """Render an OptimizationResult as a clean, actionable Markdown report."""
    lines: List[str] = []

    lines.append(f"# Week {result.week} Fantasy Football Lineup Report — {result.team_name}")
    lines.append("")

    # Summary metrics
    roster_gain = round(result.optimal_projected_total - result.current_projected_total, 2)
    total_gain = round(result.with_fa_projected_total - result.current_projected_total, 2)

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Projected Points | Change vs. Current |")
    lines.append("| --- | ---: | ---: |")
    lines.append(f"| Current Starters | {result.current_projected_total:.1f} | — |")
    lines.append(
        f"| Optimized Roster | {result.optimal_projected_total:.1f} | {roster_gain:+.1f} |"
    )
    lines.append(
        f"| With Top Free Agents | {result.with_fa_projected_total:.1f} | {total_gain:+.1f} |"
    )
    lines.append("")

    # Bye & Injury Alerts
    lines.append("## Bye Week & Injury Alerts")
    lines.append("")
    if not result.alerts:
        lines.append("All current starters are healthy and active this week.")
    else:
        for alert in result.alerts:
            badge = "CRITICAL" if alert.severity == "CRITICAL" else "WARNING"
            lines.append(f"- **[{badge}]** {alert.message}")
    lines.append("")

    # Roster Swaps
    lines.append("## Recommended Roster Swaps (Start / Sit)")
    lines.append("")
    if not result.swaps:
        lines.append("Your current starting lineup is already optimal for your roster.")
    else:
        lines.append("| Slot | Start | Proj | Sit | Proj | Gain | Reason |")
        lines.append("| --- | --- | ---: | --- | ---: | ---: | --- |")
        for swap in result.swaps:
            sit_label = _fmt_player(swap.sit_player) if swap.sit_player else "_Empty Slot_"
            sit_pts = (
                f"{swap.sit_player.effective_projected_points:.1f}"
                if swap.sit_player
                else "0.0"
            )
            lines.append(
                f"| {swap.slot} | {_fmt_player(swap.start_player)} | "
                f"{swap.start_player.effective_projected_points:.1f} | "
                f"{sit_label} | {sit_pts} | {swap.point_gain:+.1f} | {swap.reason} |"
            )
    lines.append("")

    # Free Agent Upgrades (Starters)
    lines.append("## Recommended Free Agent Upgrades (Starters)")
    lines.append("")
    if not result.free_agent_upgrades:
        lines.append("No available free agents are projected to outscore your optimal starters.")
    else:
        lines.append(
            "| Slot | Add Free Agent | Proj | Replaces | Proj | Gain | Suggested Drop |"
        )
        lines.append("| --- | --- | ---: | --- | ---: | ---: | --- |")
        for up in result.free_agent_upgrades:
            curr_label = _fmt_player(up.current_player) if up.current_player else "_Empty Slot_"
            curr_pts = (
                f"{up.current_player.effective_projected_points:.1f}"
                if up.current_player
                else "0.0"
            )
            drop_label = _fmt_player(up.suggested_drop) if up.suggested_drop else "—"
            lines.append(
                f"| {up.slot} | {_fmt_player(up.free_agent)} | "
                f"{up.free_agent.effective_projected_points:.1f} | "
                f"{curr_label} | {curr_pts} | {up.point_gain:+.1f} | {drop_label} |"
            )
    lines.append("")

    # Free Agent Upgrades (Bench)
    lines.append("## Recommended Bench Upgrades")
    lines.append("")
    if not result.bench_upgrades:
        lines.append("No same-position free agents are projected to upgrade your healthy bench.")
    else:
        lines.append(
            "| Pos | Add Free Agent | Proj | Drop Bench Player | Proj | Gain |"
        )
        lines.append("| --- | --- | ---: | --- | ---: | ---: |")
        for up in result.bench_upgrades:
            bench_label = _fmt_player(up.current_player) if up.current_player else "—"
            bench_pts = (
                f"{up.current_player.effective_projected_points:.1f}"
                if up.current_player
                else "0.0"
            )
            lines.append(
                f"| {up.position} | {_fmt_player(up.free_agent)} | "
                f"{up.free_agent.effective_projected_points:.1f} | "
                f"{bench_label} | {bench_pts} | {up.point_gain:+.1f} |"
            )
    lines.append("")

    # High-Value Free Agents Spotlight (All Positions, RB/WR Priority)
    lines.append("## High-Value Free Agents (All Positions — RB/WR Priority)")
    lines.append("")
    if not result.high_value_free_agents:
        lines.append("No notable healthy free agents found.")
    else:
        lines.append("| Category | Pos | Player | Team | Proj | Rostered % | Note |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | --- |")
        for item in result.high_value_free_agents:
            p = item.player
            lines.append(
                f"| {item.category} | {p.position} | **{p.name}** | {p.pro_team} | "
                f"{p.effective_projected_points:.1f} | {p.percent_owned:.0f}% | {item.note} |"
            )
    lines.append("")

    # Optimal Starting Lineup
    lines.append("## Optimal Starting Lineup (Current Roster)")
    lines.append("")
    lines.append("| Slot | Player | Team | Status | Projected Pts |")
    lines.append("| --- | --- | --- | --- | ---: |")
    for assignment in result.optimal_starters:
        if assignment.player is None:
            lines.append(f"| {assignment.slot} | _Empty — pickup needed_ | — | — | 0.0 |")
        else:
            p = assignment.player
            lines.append(
                f"| {assignment.slot} | {p.name} ({p.position}) | {p.pro_team} | "
                f"{p.status_label} | {p.effective_projected_points:.1f} |"
            )
    lines.append("")

    # Bench
    lines.append("## Bench")
    lines.append("")
    if not result.bench:
        lines.append("_No bench players._")
    else:
        lines.append("| Player | Pos | Team | Status | Projected Pts |")
        lines.append("| --- | --- | --- | --- | ---: |")
        for p in result.bench:
            lines.append(
                f"| {p.name} | {p.position} | {p.pro_team} | "
                f"{p.status_label} | {p.effective_projected_points:.1f} |"
            )
    lines.append("")

    return "\n".join(lines)
