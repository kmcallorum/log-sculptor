"""Tests for CLI commands."""
import pytest
from click.testing import CliRunner

from log_sculptor.cli import learn, parse, auto, show, validate, merge, drift, fast_learn, generate
from log_sculptor.testing.generators import write_sample_logs

# Check for optional dependencies
import importlib.util
HAS_DUCKDB = importlib.util.find_spec("duckdb") is not None
HAS_PYARROW = importlib.util.find_spec("pyarrow") is not None


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_log(tmp_path):
    """Create sample log file."""
    log_file = tmp_path / "server.log"
    write_sample_logs(log_file, generator="apache", count=50, seed=42)
    return log_file


@pytest.fixture
def patterns_file(tmp_path, sample_log):
    """Create patterns file from sample log."""
    from log_sculptor.core.patterns import learn_patterns
    patterns = learn_patterns(sample_log)
    patterns_path = tmp_path / "patterns.json"
    patterns.save(patterns_path)
    return patterns_path


class TestLearnCommand:
    """Tests for learn command."""

    def test_learn_basic(self, runner, sample_log, tmp_path):
        """Test basic learn command."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(learn, [str(sample_log), "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()
        assert "Learned" in result.output
        assert "patterns" in result.output

    def test_learn_with_sample_size(self, runner, sample_log, tmp_path):
        """Test learn with sample size limit."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(learn, [str(sample_log), "-o", str(output), "--sample-size", "10"])

        assert result.exit_code == 0
        assert output.exists()

    def test_learn_with_clustering(self, runner, sample_log, tmp_path):
        """Test learn with clustering enabled."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(learn, [str(sample_log), "-o", str(output), "--cluster"])

        assert result.exit_code == 0
        assert output.exists()

    def test_learn_verbose(self, runner, sample_log, tmp_path):
        """Test learn with verbose output."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(learn, [str(sample_log), "-o", str(output), "-v"])

        assert result.exit_code == 0
        assert "Learning patterns from" in result.output


class TestParseCommand:
    """Tests for parse command."""

    def test_parse_jsonl(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse to JSONL format."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "jsonl", "-o", str(output)
        ])

        assert result.exit_code == 0
        assert output.exists()
        assert "Parsed" in result.output

    def test_parse_sqlite(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse to SQLite format."""
        output = tmp_path / "output.db"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "sqlite", "-o", str(output)
        ])

        assert result.exit_code == 0
        assert output.exists()

    def test_parse_with_include_raw(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse with raw line inclusion."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "jsonl", "-o", str(output), "--include-raw"
        ])

        assert result.exit_code == 0


class TestAutoCommand:
    """Tests for auto command."""

    def test_auto_jsonl(self, runner, sample_log, tmp_path):
        """Test auto command with JSONL output."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(auto, [str(sample_log), "-f", "jsonl", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()
        assert "Learned" in result.output
        assert "parsed" in result.output

    def test_auto_sqlite(self, runner, sample_log, tmp_path):
        """Test auto command with SQLite output."""
        output = tmp_path / "output.db"
        result = runner.invoke(auto, [str(sample_log), "-f", "sqlite", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    def test_auto_verbose(self, runner, sample_log, tmp_path):
        """Test auto command with verbose output."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(auto, [str(sample_log), "-f", "jsonl", "-o", str(output), "-v"])

        assert result.exit_code == 0
        assert "Learning patterns" in result.output


class TestShowCommand:
    """Tests for show command."""

    def test_show_patterns(self, runner, patterns_file):
        """Test show patterns command."""
        result = runner.invoke(show, [str(patterns_file)])

        assert result.exit_code == 0
        assert "Patterns:" in result.output
        assert "Pattern" in result.output


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_success(self, runner, sample_log, patterns_file):
        """Test validate with matching patterns."""
        result = runner.invoke(validate, [str(patterns_file), str(sample_log)])

        assert result.exit_code == 0
        assert "Matched:" in result.output

    def test_validate_verbose(self, runner, sample_log, patterns_file):
        """Test validate with verbose output."""
        result = runner.invoke(validate, [str(patterns_file), str(sample_log), "-v"])

        assert "Matched:" in result.output


class TestMergeCommand:
    """Tests for merge command."""

    def test_merge_patterns(self, runner, patterns_file, tmp_path):
        """Test merge patterns command."""
        output = tmp_path / "merged.json"
        result = runner.invoke(merge, [str(patterns_file), "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()
        assert "Merged" in result.output

    def test_merge_with_threshold(self, runner, patterns_file, tmp_path):
        """Test merge with custom threshold."""
        output = tmp_path / "merged.json"
        result = runner.invoke(merge, [str(patterns_file), "-o", str(output), "--threshold", "0.9"])

        assert result.exit_code == 0


class TestDriftCommand:
    """Tests for drift command."""

    def test_drift_detection(self, runner, sample_log, patterns_file):
        """Test drift detection command."""
        result = runner.invoke(drift, [str(sample_log), "-p", str(patterns_file)])

        # Exit code 0 = no drift, 1 = drift detected
        assert result.exit_code in [0, 1]

    def test_drift_with_window(self, runner, sample_log, patterns_file):
        """Test drift with custom window size."""
        result = runner.invoke(drift, [str(sample_log), "-p", str(patterns_file), "--window", "20"])

        assert result.exit_code in [0, 1]


class TestFastLearnCommand:
    """Tests for fast-learn command."""

    def test_fast_learn(self, runner, sample_log, tmp_path):
        """Test fast-learn parallel processing."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(fast_learn, [str(sample_log), "-o", str(output), "--workers", "2"])

        assert result.exit_code == 0
        assert output.exists()
        assert "Learned" in result.output


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_app_logs(self, runner, tmp_path):
        """Test generate app logs."""
        output = tmp_path / "app.log"
        result = runner.invoke(generate, [str(output), "-t", "app", "-n", "100"])

        assert result.exit_code == 0
        assert output.exists()
        assert "Generated" in result.output

    def test_generate_apache_logs(self, runner, tmp_path):
        """Test generate apache logs."""
        output = tmp_path / "apache.log"
        result = runner.invoke(generate, [str(output), "-t", "apache", "-n", "50"])

        assert result.exit_code == 0
        assert output.exists()

    def test_generate_with_seed(self, runner, tmp_path):
        """Test generate with seed produces valid output."""
        output = tmp_path / "log.log"
        result = runner.invoke(generate, [str(output), "-t", "app", "-n", "10", "--seed", "42"])

        assert result.exit_code == 0
        assert output.exists()
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 10

    def test_generate_all_types(self, runner, tmp_path):
        """Test all generator types."""
        for log_type in ["app", "apache", "syslog", "json", "mixed"]:
            output = tmp_path / f"{log_type}.log"
            result = runner.invoke(generate, [str(output), "-t", log_type, "-n", "10"])
            assert result.exit_code == 0
            assert output.exists()


class TestMultilineHandling:
    """Tests for multiline log handling."""

    @pytest.fixture
    def multiline_log(self, tmp_path):
        """Create a log with multiline entries."""
        log_file = tmp_path / "multiline.log"
        log_file.write_text("""2024-01-15 10:00:00 INFO Application started
2024-01-15 10:00:01 ERROR Exception occurred
    at java.lang.Exception
    at com.example.Main.run
2024-01-15 10:00:02 INFO Recovered
""")
        return log_file

    def test_learn_multiline(self, runner, multiline_log, tmp_path):
        """Test learn with multiline option."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(learn, [str(multiline_log), "-o", str(output), "--multiline"])

        assert result.exit_code == 0
        assert output.exists()

    def test_parse_multiline(self, runner, multiline_log, tmp_path):
        """Test parse with multiline option."""
        patterns_file = tmp_path / "patterns.json"
        runner.invoke(learn, [str(multiline_log), "-o", str(patterns_file), "--multiline"])

        output = tmp_path / "output.jsonl"
        result = runner.invoke(parse, [
            str(multiline_log), "-p", str(patterns_file), "-f", "jsonl",
            "-o", str(output), "--multiline"
        ])

        assert result.exit_code == 0
        assert output.exists()

    def test_auto_multiline(self, runner, multiline_log, tmp_path):
        """Test auto with multiline option."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(auto, [str(multiline_log), "-f", "jsonl", "-o", str(output), "--multiline"])

        assert result.exit_code == 0
        assert output.exists()


class TestUpdateMode:
    """Tests for pattern update mode."""

    def test_learn_update(self, runner, sample_log, patterns_file, tmp_path):
        """Test learn with update option."""
        # Create a second log file
        log2 = tmp_path / "server2.log"
        write_sample_logs(log2, generator="syslog", count=20, seed=43)

        output = tmp_path / "updated.json"
        result = runner.invoke(learn, [
            str(log2), "-o", str(output), "--update", str(patterns_file)
        ])

        assert result.exit_code == 0
        assert output.exists()


class TestDuckDBParquetFormats:
    """Tests for DuckDB and Parquet output formats."""

    @pytest.mark.skipif(not HAS_DUCKDB, reason="duckdb not installed")
    def test_parse_duckdb(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse to DuckDB format."""
        output = tmp_path / "output.duckdb"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "duckdb", "-o", str(output)
        ])

        assert result.exit_code == 0
        assert output.exists()

    @pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
    def test_parse_parquet(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse to Parquet format."""
        output = tmp_path / "output.parquet"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "parquet", "-o", str(output)
        ])

        assert result.exit_code == 0
        assert output.exists()

    @pytest.mark.skipif(not HAS_DUCKDB, reason="duckdb not installed")
    def test_auto_duckdb(self, runner, sample_log, tmp_path):
        """Test auto with DuckDB output."""
        output = tmp_path / "output.duckdb"
        result = runner.invoke(auto, [str(sample_log), "-f", "duckdb", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    @pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
    def test_auto_parquet(self, runner, sample_log, tmp_path):
        """Test auto with Parquet output."""
        output = tmp_path / "output.parquet"
        result = runner.invoke(auto, [str(sample_log), "-f", "parquet", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    def test_parse_exclude_unmatched(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse with --no-include-unmatched."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "jsonl",
            "-o", str(output), "--no-include-unmatched"
        ])

        assert result.exit_code == 0

    def test_parse_sqlite_exclude_unmatched(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse to SQLite with --no-include-unmatched."""
        output = tmp_path / "output.db"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "sqlite",
            "-o", str(output), "--no-include-unmatched"
        ])

        assert result.exit_code == 0


class TestVerboseOutput:
    """Tests for verbose output."""

    def test_learn_verbose_update(self, runner, sample_log, patterns_file, tmp_path):
        """Test learn with verbose and update."""
        log2 = tmp_path / "server2.log"
        write_sample_logs(log2, generator="app", count=10, seed=44)

        output = tmp_path / "updated.json"
        result = runner.invoke(learn, [
            str(log2), "-o", str(output), "--update", str(patterns_file), "-v"
        ])

        assert result.exit_code == 0
        assert "Updating" in result.output

    def test_parse_verbose(self, runner, sample_log, patterns_file, tmp_path):
        """Test parse with verbose output."""
        output = tmp_path / "output.jsonl"
        result = runner.invoke(parse, [
            str(sample_log), "-p", str(patterns_file), "-f", "jsonl",
            "-o", str(output), "-v"
        ])

        assert result.exit_code == 0
        assert "Loaded" in result.output

    def test_drift_verbose(self, runner, sample_log, patterns_file):
        """Test drift with verbose output."""
        result = runner.invoke(drift, [str(sample_log), "-p", str(patterns_file), "-v"])

        # Exit code 0 or 1 (no drift or drift detected)
        assert result.exit_code in [0, 1]
        assert "Analyzing" in result.output

    def test_fast_learn_verbose(self, runner, sample_log, tmp_path):
        """Test fast-learn with verbose output."""
        output = tmp_path / "patterns.json"
        result = runner.invoke(fast_learn, [str(sample_log), "-o", str(output), "-v"])

        assert result.exit_code == 0
        assert "workers" in result.output

    def test_merge_verbose(self, runner, patterns_file, tmp_path):
        """Test merge with verbose output."""
        output = tmp_path / "merged.json"
        result = runner.invoke(merge, [str(patterns_file), "-o", str(output), "-v"])

        assert result.exit_code == 0
        assert "Merging" in result.output
