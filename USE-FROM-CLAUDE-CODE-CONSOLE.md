# Using log-sculptor from Claude Code Console

A step-by-step guide to pulling Kubernetes logs and analyzing them with log-sculptor, all from within a Claude Code session.

## Prerequisites

- `kubectl` configured with cluster access
- `pip3` available
- A running K8s deployment to pull logs from

## Step 1: Install log-sculptor

```bash
pip3 install log-sculptor
```

## Step 2: Dump logs from your K8s deployment

Pull the last 24 hours of logs from a specific deployment:

```bash
kubectl --context="<your-context>" -n <namespace> logs deployment/<name> --since=24h > /tmp/app.log
```

Real example:

```bash
DO_CTX="do-nyc3-k8s-1-33-6-do-2-nyc3-1768482431649"
kubectl --context="$DO_CTX" -n airf-studio logs deployment/airf-studio-backend --since=24h > /tmp/backend.log
kubectl --context="$DO_CTX" -n airf-studio logs deployment/airf-studio-frontend --since=24h > /tmp/frontend.log
```

## Step 3: Learn patterns and see what's in the logs

Quick overview of what log patterns exist:

```bash
log-sculptor learn /tmp/backend.log -o /tmp/backend-patterns.json
log-sculptor show /tmp/backend-patterns.json
```

This outputs something like:

```
Patterns: 7

Pattern 1: 125cbe10b693
  Frequency: 7969, Confidence: 1.00
  Example: INFO:     10.108.32.72:51534 - "GET /health HTTP/1.1" 200 OK...

Pattern 2: 34f967b39614
  Frequency: 1, Confidence: 1.00
  Example: Defaulted container "backend" out of: backend, seed-knowledge (init)...
```

This immediately tells you the shape of your logs — what's noise (health checks) and what's signal.

## Step 4: Parse into structured data

For deeper analysis, parse into JSON Lines:

```bash
log-sculptor auto /tmp/backend.log -f jsonl -o /tmp/backend-parsed.jsonl
```

Or into SQLite for SQL queries:

```bash
log-sculptor auto /tmp/backend.log -f sqlite -o /tmp/backend.db
```

## Step 5: Filter and investigate

Use standard tools alongside log-sculptor to dig in:

```bash
# Filter out noisy health checks
grep -v 'GET /health' /tmp/backend.log

# Count errors
grep -c 'Error' /tmp/frontend.log

# See unique patterns of errors
grep 'Error' /tmp/frontend.log | log-sculptor auto - -f jsonl -o /tmp/errors.jsonl
```

## Tips for Claude Code sessions

- **Dump first, analyze second** — Pull logs to `/tmp/` so you can re-analyze without hitting the cluster repeatedly
- **Use `learn` + `show` for a quick triage** — Pattern frequency tells you what's normal vs. unusual immediately
- **Combine with grep for filtering** — log-sculptor finds the patterns, grep filters the noise
- **Use `--since` flag** — Keep log volume manageable. `--since=1h`, `--since=24h`, `--since=7d`
- **Multiple deployments** — Pull backend, frontend, and DB logs separately for cleaner analysis
- **SQLite output for complex queries** — When you need to correlate across patterns, parse to SQLite and use SQL

## Real-world workflow

This is what a production log review looks like in Claude Code:

```
You: "Pull the logs since go-live and see what's going on"

1. kubectl logs → /tmp/backend.log
2. log-sculptor learn → 7 patterns found
3. Pattern 1 is 99.9% health checks → filter out
4. Remaining 30 lines: clean startup + auth flows + admin actions
5. Zero errors → deployment is healthy

You: "Check frontend too"

1. kubectl logs → /tmp/frontend.log
2. cat the file (only 95 lines)
3. Found: Server Action cache mismatch (stale browser cache, not a bug)
4. Found: metadataBase warning (one-line fix)
```

Total time: under 2 minutes for a full production log review.
