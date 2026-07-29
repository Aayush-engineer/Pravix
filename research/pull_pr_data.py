"""
Pravix — Phase 0 data pull script.

Pulls agent-authored pull requests from a list of target GitHub repos,
extracts structural features (diff size, file count, plan presence,
force-push activity, etc.), and saves them incrementally to a CSV for
model validation. Safe to interrupt and re-run — already-collected
PRs are skipped on subsequent runs.

Usage:
    cp .env.example .env   # then paste your token into .env
    python pull_pr_data.py
    python pull_pr_data.py --repos facebook/react vuejs/core --limit 50
    python pull_pr_data.py --include-force-push   # costs 1 extra API call per PR

Requires: requests, pandas, python-dotenv, tqdm  (see requirements.txt)
"""

import argparse
import csv
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pravix.pull_pr_data")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    sys.exit("Set GITHUB_TOKEN in your environment or a .env file before running (see .env.example).")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

DEFAULT_AGENT_AUTHORS = [
    "app/copilot-swe-agent",       # GitHub's native coding agent (also used for Claude/Codex via GitHub's shared agent flow)
    "app/devin-ai-integration",    # confirmed working — returned real PRs
    "app/cursor",                  # confirmed working — low volume, Cursor is mostly interactive not autonomous
    "app/chatgpt-codex-connector", # corrected slug — was "codex-connector", which does not exist
    # "app/claude" removed: no distinct, confirmed GitHub App identity for Claude as a PR author.
    # Claude-authored PRs via GitHub's native agent flow currently appear under copilot-swe-agent.
    # Add other agents here as you confirm real slugs, e.g. "app/sweep-ai", "app/blackboxai-cofounder"
]

DEFAULT_TARGET_REPOS = [
    "facebook/react",
    "microsoft/vscode",
    "vercel/next.js",
    "langchain-ai/langchain",
    "vuejs/core",
    # Your first real run only surfaced 33 usable rows across these 5 repos —
    # too small to train on (MIN_ROWS_WARNING = 200). Consider adding more repos
    # known to receive heavy agent-authored PR traffic via --repos, e.g.:
    # "pytorch/pytorch", "huggingface/transformers", "denoland/deno",
    # "supabase/supabase", "n8n-io/n8n"
]

OUTPUT_PATH = "../data/training/pr_dataset_raw.csv"
PAGE_SIZE = 100
MAX_RETRIES = 5

CSV_FIELDS = [
    "repo", "pr_number", "author", "created_at", "closed_at", "merged_at",
    "merged", "state", "additions", "deletions", "diff_size", "changed_files",
    "commits", "comments", "review_comments", "has_plan", "body_length",
    "title", "duration_hours", "force_pushed",
]


def validate_token():
    """Fail fast with a clear message if the token is missing/invalid, instead of
    discovering it deep inside the collection loop."""
    resp = requests.get("https://api.github.com/user", headers=HEADERS)
    if resp.status_code == 401:
        sys.exit("GitHub token is invalid or expired. Generate a new fine-grained "
                  "token (public repo read access) and update your .env file.")
    resp.raise_for_status()
    log.info("Token OK — authenticated as %s", resp.json().get("login"))


def request_with_retry(url: str, params: dict | None = None) -> requests.Response:
    """GET with handling for both primary (5000/hr) and secondary (search: 30/min)
    GitHub rate limits, plus transient network errors. Loops instead of recursing."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except requests.RequestException as e:
            wait = min(2 ** attempt, 60)
            log.warning("Network error (%s), retrying in %ss...", e, wait)
            time.sleep(wait)
            continue

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 1)
            log.warning("Rate limited. Sleeping %.0fs...", wait)
            time.sleep(wait)
            continue

        if resp.status_code == 422:
            log.error("Invalid query (422): %s — skipping", params)
            resp.raise_for_status()

        resp.raise_for_status()
        return resp

    raise RuntimeError(f"Exceeded {MAX_RETRIES} retries for {url}")


def search_prs(repo: str, author: str) -> list[dict]:
    """Search for PRs by a given author (bot) in a given repo via the Search API.

    Two 422 cases to handle differently:
    1. GitHub hard-caps search at 1,000 total results (page 11+ at per_page=100).
       This is expected and NOT an error — return whatever was already collected
       from earlier pages instead of discarding it.
    2. Some very large repos (facebook/react, etc.) occasionally 422 on page 1,
       likely a backend query-complexity/timeout quirk, not a real validation
       error. Retry with backoff a few times before giving up on that combo.
    """
    prs = []
    page = 1
    page1_retries = 0
    max_page1_retries = 3

    while True:
        query = f"repo:{repo} is:pr author:{author}"
        params = {"q": query, "per_page": PAGE_SIZE, "page": page}
        try:
            resp = request_with_retry("https://api.github.com/search/issues", params)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                if page > 1:
                    # Hit the 1,000-result search cap — keep what we already have.
                    log.info("Reached GitHub's search result cap for %s/%s at page %d "
                             "— returning %d PRs already collected.", repo, author, page, len(prs))
                    break
                elif page1_retries < max_page1_retries:
                    page1_retries += 1
                    wait = 5 * page1_retries
                    log.warning("422 on page 1 for %s/%s (likely a large-repo query "
                                "timeout quirk) — retrying in %ds (%d/%d)...",
                                repo, author, wait, page1_retries, max_page1_retries)
                    time.sleep(wait)
                    continue
                else:
                    log.error("%s/%s failed on page 1 after %d retries — skipping this "
                              "combo. May need a different query strategy for this repo.",
                              repo, author, max_page1_retries)
                    break
            raise

        items = resp.json().get("items", [])
        if not items:
            break
        prs.extend(items)
        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(2.5)  # Search API secondary limit is ~30/min even when authenticated

    return prs


def get_pr_detail(repo: str, number: int) -> dict:
    resp = request_with_retry(f"https://api.github.com/repos/{repo}/pulls/{number}")
    return resp.json()


def had_force_push(repo: str, number: int) -> bool:
    """Check the PR's issue timeline for a head_ref_force_pushed event."""
    resp = request_with_retry(
        f"https://api.github.com/repos/{repo}/issues/{number}/timeline",
        params={"per_page": 100},
    )
    events = resp.json()
    return any(e.get("event") == "head_ref_force_pushed" for e in events)


def has_stated_plan(body: str) -> bool:
    """Rough heuristic: does the PR body contain something resembling a stated plan?"""
    if not body:
        return False
    plan_markers = [
        r"##?\s*plan",
        r"##?\s*approach",
        r"##?\s*summary of changes",
        r"##?\s*what.*changed",
        r"##?\s*implementation",
        r"^\s*\d+\.\s",       # numbered list steps
        r"^\s*-\s\[[ x]\]",   # checklist items
    ]
    return any(re.search(p, body, re.IGNORECASE | re.MULTILINE) for p in plan_markers)


def duration_hours(created_at, closed_at):
    if not created_at or not closed_at:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    created = datetime.strptime(created_at, fmt).replace(tzinfo=timezone.utc)
    closed = datetime.strptime(closed_at, fmt).replace(tzinfo=timezone.utc)
    return round((closed - created).total_seconds() / 3600, 2)


def extract_features(pr_detail: dict, repo: str, force_pushed) -> dict:
    additions = pr_detail.get("additions", 0)
    deletions = pr_detail.get("deletions", 0)
    body = pr_detail.get("body") or ""

    return {
        "repo": repo,
        "pr_number": pr_detail.get("number"),
        "author": pr_detail.get("user", {}).get("login"),
        "created_at": pr_detail.get("created_at"),
        "closed_at": pr_detail.get("closed_at"),
        "merged_at": pr_detail.get("merged_at"),
        "merged": bool(pr_detail.get("merged_at")),
        "state": pr_detail.get("state"),
        "additions": additions,
        "deletions": deletions,
        "diff_size": additions + deletions,
        "changed_files": pr_detail.get("changed_files", 0),
        "commits": pr_detail.get("commits", 0),
        "comments": pr_detail.get("comments", 0),
        "review_comments": pr_detail.get("review_comments", 0),
        "has_plan": has_stated_plan(body),
        "body_length": len(body),
        "title": pr_detail.get("title"),
        "duration_hours": duration_hours(pr_detail.get("created_at"), pr_detail.get("closed_at")),
        "force_pushed": force_pushed,  # None if --include-force-push wasn't passed
    }


def load_existing_keys(path: str):
    """(repo, pr_number) pairs already collected, so re-runs skip duplicate work.

    Also validates the existing CSV's header matches the current CSV_FIELDS
    schema — appending rows with a different column count than the header
    silently corrupts the file (this bit us once already: adding
    duration_hours/force_pushed broke a file written by an older schema)."""
    if not os.path.exists(path):
        return set()

    with open(path, "r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")

    if header != CSV_FIELDS:
        sys.exit(
            f"Schema mismatch: {path} has columns {header}\n"
            f"but the script now expects {CSV_FIELDS}.\n\n"
            f"This usually means the script's schema changed since this file was "
            f"created. Back up and remove the old file before re-running:\n"
            f"  mv {path} {path}.bak\n"
            f"Then re-run — data will be recollected from the API."
        )

    df = pd.read_csv(path, usecols=["repo", "pr_number"])
    return set(zip(df["repo"], df["pr_number"]))


def append_row(path: str, row: dict):
    file_exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def parse_args():
    p = argparse.ArgumentParser(description="Pull agent-authored PR data for Pravix Phase 0.")
    p.add_argument("--repos", nargs="+", default=DEFAULT_TARGET_REPOS, help="Repos to scan, e.g. facebook/react")
    p.add_argument("--authors", nargs="+", default=DEFAULT_AGENT_AUTHORS, help="Bot author logins to search for")
    p.add_argument("--output", default=OUTPUT_PATH, help="CSV output path")
    p.add_argument("--limit", type=int, default=None, help="Max PRs to process per repo/author pair (for quick test runs)")
    p.add_argument("--include-force-push", action="store_true",
                   help="Fetch timeline events to detect force-pushes (1 extra API call per PR)")
    return p.parse_args()


def main():
    args = parse_args()
    validate_token()

    existing = load_existing_keys(args.output)
    if existing:
        log.info("Resuming: %d PRs already collected, will be skipped.", len(existing))

    total_new = 0
    for repo in args.repos:
        for author in args.authors:
            log.info("Searching %s for author=%s...", repo, author)
            try:
                results = search_prs(repo, author)
            except requests.HTTPError as e:
                log.error("Skipping %s/%s: %s", repo, author, e)
                continue

            if args.limit:
                results = results[: args.limit]
            log.info("Found %d PRs", len(results))

            for item in tqdm(results, desc=f"{repo} / {author}"):
                number = item["number"]
                if (repo, number) in existing:
                    continue

                try:
                    detail = get_pr_detail(repo, number)
                    force_pushed = had_force_push(repo, number) if args.include_force_push else None
                except requests.HTTPError as e:
                    log.error("Failed to fetch PR #%d: %s", number, e)
                    continue

                row = extract_features(detail, repo, force_pushed)
                append_row(args.output, row)
                existing.add((repo, number))
                total_new += 1
                time.sleep(0.1)  # be polite to the API even with a token

    if total_new == 0:
        log.warning("No new PRs collected this run. Check --repos/--authors, or everything was already cached.")
        return

    df = pd.read_csv(args.output)
    log.info("Total dataset now %d PRs at %s", len(df), args.output)
    log.info("Merge outcome breakdown:\n%s", df["merged"].value_counts().to_string())


if __name__ == "__main__":
    main()