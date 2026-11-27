"""End-to-end tests for the CLI entry point."""

from ff_optimizer.cli import main


def test_cli_mock_mode_writes_report_and_prints_stdout(tmp_path, capsys):
    out_file = tmp_path / "weekly-report.md"
    exit_code = main(["--mock", "--week", "11", "--output", str(out_file)])

    assert exit_code == 0
    assert out_file.exists()

    written = out_file.read_text(encoding="utf-8")
    captured = capsys.readouterr().out
    assert written == captured.strip() + "\n" or written.strip() == captured.strip()
    assert "# Week 11 Fantasy Football Lineup Report — Demo Squad" in written
    assert "Josh Allen" in written
    assert "Baker Mayfield" in written
    assert "Jonnu Smith" in written
    assert "Broncos D/ST" in written
    assert "Chris Boswell" in written
