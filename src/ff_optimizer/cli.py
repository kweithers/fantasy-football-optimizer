"""Command-line interface for the ESPN Fantasy Football Lineup Optimizer."""

import argparse
from pathlib import Path
import sys
from typing import Optional, Sequence

from ff_optimizer.config import OptimizerConfig
from ff_optimizer.espn_client import ESPNClient
from ff_optimizer.mock_data import get_mock_team_data
from ff_optimizer.optimizer import optimize_team
from ff_optimizer.reporter import format_markdown_report


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ff-optimizer",
        description="Optimize your ESPN Fantasy Football lineup for the week.",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Target NFL week number (defaults to the league's current week).",
    )
    parser.add_argument(
        "--min-gain",
        type=float,
        default=None,
        help="Minimum projected point gain to recommend a free agent (default: 0.5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path to write the Markdown report.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with built-in sample data instead of calling the ESPN API.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    _load_dotenv_if_available()
    parser = build_parser()
    args = parser.parse_args(argv)

    config = OptimizerConfig.from_env(
        week=args.week,
        min_point_gain=args.min_gain,
    )

    if args.mock:
        team_name, week, roster, free_agents = get_mock_team_data(
            week=args.week if args.week is not None else 12
        )
    else:
        client = ESPNClient(config)
        team_name, week, roster, free_agents = client.fetch_team_data()

    result = optimize_team(
        team_name=team_name,
        week=week,
        roster=roster,
        free_agents_by_pos=free_agents,
        min_point_gain=config.min_point_gain,
    )
    report = format_markdown_report(result)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
