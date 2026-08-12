# Pravix

**Predict whether an agent-authored pull request will get merged, ghosted, or dragged into a costly review spiral — before a human ever reads the diff.**

**Who it's for:** open-source maintainers and teams receiving pull requests opened by AI coding agents (Copilot's coding agent, Devin, Cursor, Codex, and similar), who need a fast, free, transparent way to triage them before spending review time.

![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Status](https://img.shields.io/badge/status-Phase%200%20%E2%80%94%20research-orange)
![Contributions](https://img.shields.io/badge/contributions-not%20yet%20open-lightgrey)

> **Status: early research phase.** The core prediction model has not yet been validated against real data. Nothing here is production-ready. See [Roadmap](#roadmap) for the current stage and what's next.

If the idea sounds useful to you, **star/watch the repo** — Phase 0 findings and the first working CLI will be announced there first.

---

## Contents

- [The problem](#the-problem)
- [What Pravix does](#what-pravix-does)
- [Why not just use PR-Agent / CodeRabbit / GitHub's Agentic Workflows?](#why-not-just-use-pr-agent--coderabbit--githubs-agentic-workflows)
- [Research basis](#research-basis)
- [Current stage](#current-stage-phase-0--validating-the-model)
- [Tech stack](#tech-stack)
- [Roadmap](#roadmap)
- [Design principles](#design-principles)
- [Contributing](#contributing)
- [License](#license)

---

## The problem

AI coding agents are opening pull requests on open-source repositories at massive scale. Maintainers are drowning: a large share of agent-authored PRs stall, get abandoned mid-review, or consume disproportionate reviewer time relative to their value. ("**Ghosting**" — a PR where the agent goes quiet after initial reviewer feedback, leaving a maintainer's comments unanswered — is common enough that the research below tracks it as its own outcome category.) GitHub has had to introduce restrictions on automated PR volume. Existing tools try to help by having an LLM read the diff and render an opinion — which costs money per PR, adds latency, and gives maintainers a black-box judgment rather than a reason.

Recent research (cited below) shows this is largely *predictable in advance*, using only cheap, **structural signals** — metadata about the PR itself (its size, timing, and history), not the code's actual logic — available the moment a PR is opened, no LLM call required.

## What Pravix does

Pravix scores an agent-authored PR **at creation time** using structural metadata:

- Diff size and file-change entropy
- Force-push activity during review
- Whether the PR description states an implementation plan
- Which agent authored it, and that agent's historical merge/ghost rate
- Reviewer engagement patterns from similar past PRs

It outputs a risk score and the top contributing factors — in plain language, not a black box — with **no LLM call required for the core score**, so it costs nothing to run at scale.

**What this will look like once the GitHub Action ships** (Phase 3 — not built yet, shown here so the end goal is concrete):

```
Pravix risk check
──────────────────
Risk: HIGH (predicted low merge probability)

Top contributing factors:
  • Diff size: 2,340 lines (top 5% largest in this repo's agent-PR history)
  • No implementation plan stated in PR description
  • Author (devin-ai-integration) merge rate on this repo: 31%

This is a structural prediction, not a code review — nothing here has
read your diff. Full breakdown: [link]
```

## Why not just use PR-Agent / CodeRabbit / GitHub's Agentic Workflows?

Those tools have an LLM read the code and give an opinion on quality. That's a genuinely different job: it happens *after* the diff exists, costs money per call, and doesn't explain itself in reproducible terms.

Pravix instead answers a narrower, provable question — *is this PR statistically heading toward abandonment or a costly review spiral, based on patterns from thousands of real agent PRs* — using structural signals alone. It's meant to sit **before** those tools, as a free triage layer, not compete with them on code quality judgment.

## Research basis

Pravix's model is not designed from scratch — it operationalizes findings from recent empirical studies of agent-authored PRs at scale:

1. A large-scale study of 33,596 agent-authored PRs across 2,807 repositories (the "AIDev" dataset) found reviewer engagement — not code correctness — is the strongest predictor of merge outcome; force-pushes and oversized diffs are the strongest negative predictors. Overall merge rate was 71.5%, ranging from 43.0% to 82.6% depending on the authoring agent.
2. A companion study built a structural, creation-time classifier ("Circuit Breaker") using only cheap metadata features and reported an AUC of 0.96 predicting which PRs would become high-effort review sinks — without reading the code itself.
3. Related work reports agent PR "ghosting" rates of roughly 1–10% following initial reviewer feedback.

Full citations, exact dataset sources, and methodology will be published in [`docs/methodology.md`](docs/methodology.md) once Phase 0 validation is complete — including our own reproduction numbers alongside the originals, not just the published claims.

## Current stage: Phase 0 — validating the model

Before any tool ships, we're independently verifying the published findings hold on a real, self-collected dataset of agent-authored PRs. This stage produces:

- A labeled dataset of agent-authored PRs (`data/training/`)
- A minimal feature-extraction pipeline
- A simple baseline classifier (logistic regression) with honestly reported accuracy/AUC
- Write-up in `research/findings.md`

**No tool, CLI, or GitHub Action exists yet.** They come after the model proves out — see Roadmap.

## Tech stack

- **Phase 0 (now) — research/**: Python, pandas, scikit-learn. This is where the model is validated before anything is built on top of it. See `research/pull_pr_data.py` for the data-collection script.
- **Phase 1+ — packages/core, cli, github-action**: TypeScript. Once the model is proven, its inference logic is ported to a dependency-light TypeScript package so the CLI and GitHub Action can run with zero Python runtime requirement — important for adoption, since most GitHub Action/npm tooling users expect a `npx`-installable, zero-setup experience.

## Roadmap

- [ ] **Phase 0 — Validate**: collect labeled agent-PR data, prove predictive signal exists, publish honest metrics
- [ ] **Phase 1 — Core engine**: standalone, dependency-light scoring package (`packages/core`)
- [ ] **Phase 2 — CLI**: `npx pravix scan owner/repo` for local, offline use
- [ ] **Phase 3 — GitHub Action**: opt-in, quiet-by-default risk labeling on PR open
- [ ] **Phase 4 — Public leaderboard**: aggregate, reproducible stats on merge/ghost rates by coding agent across well-known OSS repos
- [ ] **Phase 5 — Launch**

## Design principles

- **No LLM required for the core score.** Structural signals only — free to run, explainable, reproducible.
- **Quiet by default.** Pravix never auto-closes or auto-comments repeatedly. One label or one collapsed comment, maintainer stays in control.
- **Reproducible claims only.** Every accuracy/AUC number we publish comes with the code and data to re-run it (`benchmarks/eval.py`).
- **Transparent methodology.** Every prediction shows its top contributing factors — never a bare score.

## Contributing

Not yet open for code contributions — the model is being validated first so early contributors aren't building on an unproven foundation. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for what you *can* do right now (research pointers, prior art, honest pushback on methodology are all welcome).

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). For security concerns, see [`SECURITY.md`](SECURITY.md).

## License

[Apache License 2.0](LICENSE) — chosen to keep the core engine and dataset fully open, with an explicit patent grant, while leaving room for an optional hosted/commercial layer later without relicensing the open core.

---

*Pravix is an independent, research-grounded project. It is not affiliated with GitHub, Anthropic, OpenAI, or any coding agent vendor named above.*