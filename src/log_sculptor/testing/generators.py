"""Log data generators for testing and demos."""

import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Iterator
from pathlib import Path


@dataclass
class LogGenerator:
    """Configurable log data generator."""

    seed: int | None = None
    start_time: datetime = field(default_factory=datetime.now)
    time_increment: timedelta = field(default_factory=lambda: timedelta(milliseconds=100))

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)
        self._current_time = self.start_time

    def _next_time(self) -> datetime:
        """Get next timestamp."""
        ts = self._current_time
        self._current_time += self.time_increment + timedelta(
            milliseconds=random.randint(0, 500)
        )
        return ts

    def _random_ip(self) -> str:
        """Generate random IP address."""
        return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    def _random_user(self) -> str:
        """Generate random username."""
        users = ["admin", "user", "guest", "root", "www-data", "nginx", "app", "service"]
        return random.choice(users)

    def _random_path(self) -> str:
        """Generate random URL path."""
        paths = [
            "/", "/api/users", "/api/orders", "/api/products",
            "/health", "/metrics", "/login", "/logout",
            "/api/v1/data", "/api/v2/items", "/static/app.js",
            "/images/logo.png", "/css/style.css"
        ]
        return random.choice(paths)

    def _random_method(self) -> str:
        """Generate random HTTP method."""
        methods = ["GET", "GET", "GET", "POST", "PUT", "DELETE", "PATCH"]
        return random.choice(methods)

    def _random_status(self) -> int:
        """Generate random HTTP status code."""
        statuses = [200, 200, 200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503]
        return random.choice(statuses)

    def _random_level(self) -> str:
        """Generate random log level."""
        levels = ["DEBUG", "INFO", "INFO", "INFO", "WARN", "ERROR"]
        return random.choice(levels)

    def _random_message(self) -> str:
        """Generate random log message."""
        messages = [
            "Request processed successfully",
            "Connection established",
            "Cache hit for key",
            "Database query completed",
            "User authenticated",
            "Session created",
            "File uploaded",
            "Email sent",
            "Task scheduled",
            "Configuration loaded",
            "Service started",
            "Health check passed",
            "Metrics collected",
            "Backup completed",
            "Connection timeout",
            "Rate limit exceeded",
            "Invalid input received",
            "Authentication failed",
            "Resource not found",
            "Internal error occurred",
        ]
        return random.choice(messages)

    def _random_uuid(self) -> str:
        """Generate random UUID."""
        return "-".join([
            "".join(random.choices("0123456789abcdef", k=8)),
            "".join(random.choices("0123456789abcdef", k=4)),
            "".join(random.choices("0123456789abcdef", k=4)),
            "".join(random.choices("0123456789abcdef", k=4)),
            "".join(random.choices("0123456789abcdef", k=12)),
        ])

    def _random_duration(self) -> int:
        """Generate random duration in ms."""
        return random.randint(1, 5000)

    def _random_bytes(self) -> int:
        """Generate random byte count."""
        return random.randint(100, 100000)


def generate_apache_logs(
    count: int = 100,
    seed: int | None = None,
    start_time: datetime | None = None,
) -> Iterator[str]:
    """
    Generate Apache Combined Log Format entries.

    Format: %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"

    Args:
        count: Number of log lines to generate.
        seed: Random seed for reproducibility.
        start_time: Starting timestamp.

    Yields:
        Apache log lines.
    """
    gen = LogGenerator(seed=seed, start_time=start_time or datetime.now())

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Chrome/91.0.4472.124",
        "curl/7.68.0",
        "python-requests/2.28.0",
    ]

    referers = ["-", "https://google.com", "https://example.com", "-", "-"]

    for _ in range(count):
        ts = gen._next_time()
        ts_str = ts.strftime("%d/%b/%Y:%H:%M:%S +0000")
        method = gen._random_method()
        path = gen._random_path()
        status = gen._random_status()
        bytes_sent = gen._random_bytes()
        user_agent = random.choice(user_agents)
        referer = random.choice(referers)

        yield f'{gen._random_ip()} - {gen._random_user()} [{ts_str}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "{referer}" "{user_agent}"'


def generate_syslog(
    count: int = 100,
    seed: int | None = None,
    start_time: datetime | None = None,
    hostname: str = "server01",
) -> Iterator[str]:
    """
    Generate syslog format entries.

    Format: <priority>timestamp hostname program[pid]: message

    Args:
        count: Number of log lines to generate.
        seed: Random seed for reproducibility.
        start_time: Starting timestamp.
        hostname: Server hostname.

    Yields:
        Syslog lines.
    """
    gen = LogGenerator(seed=seed, start_time=start_time or datetime.now())

    programs = ["sshd", "nginx", "systemd", "kernel", "cron", "postfix", "dovecot"]
    priorities = list(range(0, 24))

    for _ in range(count):
        ts = gen._next_time()
        ts_str = ts.strftime("%b %d %H:%M:%S")
        program = random.choice(programs)
        pid = random.randint(1000, 65535)
        priority = random.choice(priorities)
        message = gen._random_message()

        yield f"<{priority}>{ts_str} {hostname} {program}[{pid}]: {message}"


def generate_json_logs(
    count: int = 100,
    seed: int | None = None,
    start_time: datetime | None = None,
) -> Iterator[str]:
    """
    Generate JSON structured log entries.

    Args:
        count: Number of log lines to generate.
        seed: Random seed for reproducibility.
        start_time: Starting timestamp.

    Yields:
        JSON log lines.
    """
    import json

    gen = LogGenerator(seed=seed, start_time=start_time or datetime.now())

    for _ in range(count):
        ts = gen._next_time()
        level = gen._random_level()
        entry = {
            "timestamp": ts.isoformat(),
            "level": level,
            "message": gen._random_message(),
            "request_id": gen._random_uuid(),
            "user": gen._random_user(),
            "ip": gen._random_ip(),
            "duration_ms": gen._random_duration(),
        }

        if level == "ERROR":
            entry["error"] = random.choice([
                "NullPointerException",
                "ConnectionTimeout",
                "ValidationError",
                "PermissionDenied",
            ])
            entry["stack_trace"] = "at com.example.Service.process(Service.java:42)"

        yield json.dumps(entry)


def generate_app_logs(
    count: int = 100,
    seed: int | None = None,
    start_time: datetime | None = None,
    app_name: str = "myapp",
) -> Iterator[str]:
    """
    Generate typical application log entries.

    Format: timestamp [level] [app] message key=value ...

    Args:
        count: Number of log lines to generate.
        seed: Random seed for reproducibility.
        start_time: Starting timestamp.
        app_name: Application name.

    Yields:
        Application log lines.
    """
    gen = LogGenerator(seed=seed, start_time=start_time or datetime.now())

    for _ in range(count):
        ts = gen._next_time()
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = gen._random_level()
        message = gen._random_message()

        # Add key-value pairs
        kvs = []
        if random.random() > 0.3:
            kvs.append(f"request_id={gen._random_uuid()}")
        if random.random() > 0.5:
            kvs.append(f"user={gen._random_user()}")
        if random.random() > 0.5:
            kvs.append(f"duration={gen._random_duration()}ms")
        if random.random() > 0.7:
            kvs.append(f"ip={gen._random_ip()}")

        kv_str = " ".join(kvs)
        if kv_str:
            yield f"{ts_str} [{level}] [{app_name}] {message} {kv_str}"
        else:
            yield f"{ts_str} [{level}] [{app_name}] {message}"


def generate_mixed_logs(
    count: int = 100,
    seed: int | None = None,
    start_time: datetime | None = None,
    change_format_at: list[int] | None = None,
) -> Iterator[str]:
    """
    Generate logs with mixed formats (for drift testing).

    Args:
        count: Number of log lines to generate.
        seed: Random seed for reproducibility.
        start_time: Starting timestamp.
        change_format_at: Line numbers where format changes.

    Yields:
        Mixed format log lines.
    """
    if seed is not None:
        random.seed(seed)

    change_points = set(change_format_at or [count // 2])
    current_format = 0
    formats = [generate_app_logs, generate_apache_logs, generate_json_logs]

    gen_kwargs = {"count": 1, "seed": None, "start_time": start_time or datetime.now()}

    for i in range(count):
        if i in change_points:
            current_format = (current_format + 1) % len(formats)

        yield next(formats[current_format](**gen_kwargs))


def write_sample_logs(
    path: Path,
    generator: str = "app",
    count: int = 1000,
    seed: int | None = None,
) -> Path:
    """
    Write sample logs to a file.

    Args:
        path: Output file path.
        generator: Generator type ('app', 'apache', 'syslog', 'json', 'mixed').
        count: Number of lines to generate.
        seed: Random seed for reproducibility.

    Returns:
        Path to created file.
    """
    generators = {
        "app": generate_app_logs,
        "apache": generate_apache_logs,
        "syslog": generate_syslog,
        "json": generate_json_logs,
        "mixed": generate_mixed_logs,
    }

    if generator not in generators:
        raise ValueError(f"Unknown generator: {generator}. Use one of: {list(generators.keys())}")

    gen_func = generators[generator]

    with open(path, "w") as f:
        for line in gen_func(count=count, seed=seed):
            f.write(line + "\n")

    return path
