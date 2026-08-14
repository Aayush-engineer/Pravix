# FAQ

## Why not just use PR-Agent, CodeRabbit, or GitHub's own Agentic Workflows?

Those tools have an LLM read the diff and form an opinion on code quality. That's a genuinely different job, done at a different time:

| | PR-Agent / CodeRabbit / Agentic Workflows | Pravix |
|---|---|---|
| **What it judges** | Code quality, correctness, style | Likelihood of merge / review-effort risk |
| **When** | After the diff exists, on request or per push | The moment the PR is opened |
| **How** | LLM reads the code | Structural metadata only (size, timing, history) |
| **Cost per PR** | An LLM API call | None for the core score |
| **Explainability** | A generated opinion | Named contributing factors from a fixed feature set |

Pravix is meant to sit **before** those tools, not replace them — a free, instant triage signal that helps a maintainer decide how much attention a PR deserves before anyone (human or LLM) spends time reading it.

## Isn't this just... an AI-generated-code detector?

No. Pravix doesn't try to determine whether a human or an agent wrote the code, and it doesn't judge the code itself at all. It only uses metadata about PRs that are *already known* to be agent-authored (via the author account), to predict an outcome (merge / ghost / high-effort review) based on patterns in that specific population.

## Does this replace human code review?

No, and it's designed not to. See the [Design principles](../README.md#design-principles) in the README — it's explicitly quiet by default (one label or comment, no auto-closing) and positions itself as a triage signal, not a gatekeeper.

## Why no LLM call for the core score? Wouldn't that be more accurate?

Possibly, on some dimensions — but it would also mean per-PR cost, latency, and a harder-to-audit prediction. The research Pravix is built on ([see Research basis](../README.md#research-basis)) specifically found that cheap structural signals alone reach a strong AUC on this particular prediction task (merge/ghost outcome, not code quality). Optional LLM-assisted features may be added later as an opt-in layer for the highest-risk subset, but the core score will always work without one.

## What happens to PRs that get flagged as high-risk?

Nothing automatic. Pravix's default behavior (once the GitHub Action ships in Phase 3) is to post a single label or collapsed comment — the maintainer decides what to do with that information. Pravix never closes, comments repeatedly, or blocks a PR on its own.

## Is my repo's data sent anywhere?

The CLI (Phase 2) and self-hosted GitHub Action (Phase 3) run entirely against the GitHub API using your own token/permissions — no data is sent to a Pravix-run server for the core scoring. The public leaderboard (Phase 4) will only include repos and PRs that are already public on GitHub, and will document its methodology and opt-out process before launch.

## How do I know the accuracy claims are real and not marketing?

You don't have to take them on faith — every number Pravix publishes comes with the code and (where licensing/size allows) the data to reproduce it, in `benchmarks/eval.py` and `docs/methodology.md`. If you can't reproduce a claimed number, please open an issue — that's a bug in our documentation or methodology, not something to just take on faith.

## Is this project affiliated with GitHub, Anthropic, OpenAI, or any coding agent vendor?

No. Pravix is an independent project. Any coding agent or tool named in this documentation (Copilot, Devin, Cursor, Codex, Claude, PR-Agent, CodeRabbit, etc.) is referenced only to describe the ecosystem it operates in, not as an endorsement or partnership.

## Contributions aren't open yet — when will they be?

Once Phase 0 (model validation) is complete and honestly documented in `research/findings.md`. See [CONTRIBUTING.md](../CONTRIBUTING.md) and the [Roadmap](../README.md#roadmap) for current status.