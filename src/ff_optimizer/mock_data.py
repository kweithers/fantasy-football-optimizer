"""Realistic mock league data for offline demo runs and integration tests."""

from typing import Dict, List, Tuple

from ff_optimizer.models import Player


def get_mock_team_data(week: int = 12) -> Tuple[str, int, List[Player], Dict[str, List[Player]]]:
    """Return a realistic sample roster and free agent pool showcasing all optimizer features."""
    roster = [
        # Starters (includes a BYE QB, an OUT RB, and a QUESTIONABLE WR)
        Player(1, "Josh Allen", "QB", "BUF", 23.5, lineup_slot="QB", on_bye_week=True, percent_owned=99.8),
        Player(2, "Saquon Barkley", "RB", "PHI", 20.4, lineup_slot="RB", percent_owned=99.9),
        Player(3, "Kenneth Walker III", "RB", "SEA", 15.8, lineup_slot="RB", injury_status="OUT", percent_owned=96.5),
        Player(4, "Amon-Ra St. Brown", "WR", "DET", 18.9, lineup_slot="WR", injury_status="QUESTIONABLE", percent_owned=99.7),
        Player(5, "DeVonta Smith", "WR", "PHI", 12.1, lineup_slot="WR", percent_owned=92.0),
        Player(6, "Dalton Kincaid", "TE", "BUF", 9.8, lineup_slot="TE", on_bye_week=True, percent_owned=84.2),
        Player(7, "Rachaad White", "RB", "TB", 10.6, lineup_slot="FLEX", percent_owned=86.1),
        Player(8, "Jets D/ST", "D/ST", "NYJ", 6.2, lineup_slot="D/ST", percent_owned=72.0),
        Player(9, "Jake Elliott", "K", "PHI", 7.4, lineup_slot="K", percent_owned=79.5),
        # Bench
        Player(10, "Baker Mayfield", "QB", "TB", 19.2, lineup_slot="BE", percent_owned=81.3),
        Player(11, "Chuba Hubbard", "RB", "CAR", 14.7, lineup_slot="BE", percent_owned=88.4),
        Player(12, "Tee Higgins", "WR", "CIN", 15.3, lineup_slot="BE", percent_owned=91.2),
        Player(13, "Jaxon Smith-Njigba", "WR", "SEA", 13.8, lineup_slot="BE", percent_owned=76.5),
        Player(14, "Trey Benson", "RB", "ARI", 4.1, lineup_slot="BE", percent_owned=24.0),
        Player(15, "Tyler Lockett", "WR", "SEA", 6.5, lineup_slot="BE", percent_owned=48.0),
    ]

    free_agents_by_pos: Dict[str, List[Player]] = {
        "QB": [
            Player(101, "Bo Nix", "QB", "DEN", 18.4, lineup_slot="FA", percent_owned=58.2),
            Player(102, "Geno Smith", "QB", "SEA", 16.9, lineup_slot="FA", percent_owned=45.0),
        ],
        "RB": [
            Player(103, "Rico Dowdle", "RB", "DAL", 11.8, lineup_slot="FA", percent_owned=62.1),
            Player(104, "Gus Edwards", "RB", "LAC", 7.2, lineup_slot="FA", percent_owned=28.0),
        ],
        "WR": [
            Player(105, "Jauan Jennings", "WR", "SF", 13.2, lineup_slot="FA", percent_owned=61.0),
            Player(106, "Cedric Tillman", "WR", "CLE", 10.4, lineup_slot="FA", injury_status="OUT", percent_owned=39.5),
        ],
        "TE": [
            Player(107, "Jonnu Smith", "TE", "MIA", 11.4, lineup_slot="FA", percent_owned=54.0),
            Player(108, "Hunter Henry", "TE", "NE", 9.6, lineup_slot="FA", percent_owned=49.3),
        ],
        "D/ST": [
            Player(109, "Broncos D/ST", "D/ST", "DEN", 10.1, lineup_slot="FA", percent_owned=64.0),
            Player(110, "Commanders D/ST", "D/ST", "WSH", 8.4, lineup_slot="FA", percent_owned=41.0),
        ],
        "K": [
            Player(111, "Chris Boswell", "K", "PIT", 9.8, lineup_slot="FA", percent_owned=74.0),
            Player(112, "Will Reichard", "K", "MIN", 8.5, lineup_slot="FA", injury_status="IR", percent_owned=32.0),
        ],
    }

    return "Demo Squad", week, roster, free_agents_by_pos
