"""
Pravix — Phase 0 data pull script.

Pulls agent-authored pull requests from a list of target GitHub repos,
extracts structural features (diff size, file count, plan presence, etc.),
and saves them to a CSV for model validation.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx   # personal access token, no special scopes needed for public repos
    python pull_pr_data.py

Requires: requests, pandas, python-dotenv, tqdm  (see requirements.txt)
"""

import os
import time
import re
import pandas as pd
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise SystemExit("Set GITHUB_TOKEN in your environment or a .env file before running.")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Known agent/bot author logins to search for. Extend this as you find more.
AGENT_AUTHORS = [
    "app/copilot-swe-agent",
    "app/devin-ai-integration",
    "app/cursor",
    "app/codex-connector",
    "app/claude",
]

# Repos known to receive agent-authored PR traffic. Extend with your own findings.
TARGET_REPOS = [
    "facebook/react",
    "microsoft/vscode",
    "vercel/next.js",
    "langchain-ai/langchain",
    "vuejs/core",
]

OUTPUT_PATH = "../data/training/pr_dataset_raw.csv"
PAGE_SIZE = 100


def search_prs(repo: str, author: str):
    """Search for PRs by a given author (bot) in a given repo via the Search API."""
    prs = []
    page = 1
    while True:
        query = f"repo:{repo} is:pr author:{author}"
        url = "https://api.github.com/search/issues"
        params = {"q": query, "per_page": PAGE_SIZE, "page": page}
        resp = requests.get(url, headers=HEADERS, params=params)

        if resp.status_code == 403:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 1)
            print(f"Rate limited. Sleeping {wait:.0f}s...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        prs.extend(items)
        if len(items) < PAGE_SIZE:
            break
        page += 1

    return prs


def get_pr_detail(repo: str, number: int):
    """Fetch full PR details (additions, deletions, changed_files, merged, etc.)."""
    url = f"https://api.github.com/repos/{repo}/pulls/{number}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 403:
        reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
        wait = max(reset - time.time(), 1)
        print(f"Rate limited. Sleeping {wait:.0f}s...")
        time.sleep(wait)
        return get_pr_detail(repo, number)
    resp.raise_for_status()
    return resp.json()


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
        r"^\s*\d+\.\s",  # numbered list steps
        r"^\s*-\s\[[ x]\]",  # checklist items
    ]
    return any(re.search(p, body, re.IGNORECASE | re.MULTILINE) for p in plan_markers)


def extract_features(pr_detail: dict, repo: str) -> dict:
    additions = pr_detail.get("additions", 0)
    deletions = pr_detail.get("deletions", 0)
    changed_files = pr_detail.get("changed_files", 0)
    commits = pr_detail.get("commits", 0)
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
        "changed_files": changed_files,
        "commits": commits,
        "comments": pr_detail.get("comments", 0),
        "review_comments": pr_detail.get("review_comments", 0),
        "has_plan": has_stated_plan(body),
        "body_length": len(body),
        "title": pr_detail.get("title"),
    }


def main():
    all_rows = []

    for repo in TARGET_REPOS:
        for author in AGENT_AUTHORS:
            print(f"Searching {repo} for author={author}...")
            try:
                results = search_prs(repo, author)
            except requests.HTTPError as e:
                print(f"  Skipping {repo}/{author}: {e}")
                continue

            print(f"  Found {len(results)} PRs")

            for item in tqdm(results, desc=f"{repo} / {author}"):
                number = item["number"]
                try:
                    detail = get_pr_detail(repo, number)
                except requests.HTTPError as e:
                    print(f"    Failed to fetch PR #{number}: {e}")
                    continue

                row = extract_features(detail, repo)
                all_rows.append(row)
                time.sleep(0.1)  # be polite to the API even with a token

    if not all_rows:
        print("No PRs collected. Check AGENT_AUTHORS / TARGET_REPOS and your token permissions.")
        return

    df = pd.DataFrame(all_rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(df)} PRs to {OUTPUT_PATH}")
    print(df["merged"].value_counts())


if __name__ == "__main__":
    main()