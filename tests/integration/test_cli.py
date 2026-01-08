"""Basic CLI tests."""
from pathlib import Path
from click.testing import CliRunner
from log_sculptor.cli import main

def test_auto_basic(simple_log: Path, tmp_path: Path):
    runner = CliRunner()
    output = tmp_path / "out.jsonl"
    result = runner.invoke(main, ["auto", str(simple_log), "-f", "jsonl", "-o", str(output)])
    assert result.exit_code == 0
    assert output.exists()
