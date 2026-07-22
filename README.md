# Pravix

**Predict whether an agent-authored pull request will get merged, ghosted, or dragged into a costly review spiral — before a human ever reads the diff.**

> Status: early research phase. Core model not yet validated. See [Roadmap](#roadmap) for current stage.

---

## The problem

AI coding agents are opening pull requests on open-source repositories at massive scale. Maintainers are drowning: a large share of agent-authored PRs stall, get abandoned mid-review ("ghosting"), or consume disproportionate reviewer time relative to their value. GitHub has had to introduce restrictions on automated PR volume. Existing tools try to help by having an LLM read the diff and render an opinion — which costs money per PR, adds latency, and gives maintainers a black-box judgment rather than a reason.

Recent research (cited below) shows this is largely *predictable in advance*, using only cheap, structural signals available the moment a PR is opened — no LLM call required.

## What Pravix does

Pravix scores an agent-authored PR **at creation time** using structural metadata:

- Diff size and file-change entropy
- Force-push activity during review
- Whether the PR description states an implementation plan
- Which agent authored it, and that agent's historical merge/ghost rate
- Reviewer engagement patterns from similar past PRs

It outputs a risk score and the top contributing factors — in plain language, not a black box — with **no LLM call required for the core score**, so it costs nothing to run at scale.

## Why not just use PR-Agent / CodeRabbit / GitHub's Agentic Workflows?

Those tools have an LLM read the code and give an opinion on quality. That's a genuinely different job: it happens *after* the diff exists, costs money per call, and doesn't explain itself in reproducible terms.

Pravix instead answers a narrower, provable question — *is this PR statistically heading toward abandonment or a costly review spiral, based on patterns from thousands of real agent PRs* — using structural signals alone. It's meant to sit **before** those tools, as a free triage layer, not compete with them on code quality judgment.

## Research basis

Pravix's model is not designed from scratch — it operationalizes findings from recent empirical studies of agent-authored PRs at scale:

- A study of 33,596 agent-authored PRs across 2,807 repositories found reviewer engagement — not code correctness — is the strongest predictor of merge outcome; force-pushes and oversized diffs are the strongest negative predictors. Overall merge rate was 71.5%, but varied from 43.0% to 82.6% depending on the authoring agent.
- A companion study built a structural, creation-time classifier ("Circuit Breaker") using only cheap metadata features and achieved an AUC of 0.96 predicting which PRs would become high-effort review sinks — without reading the code itself.
- Related work reports agent PR "ghosting" rates of roughly 1–10% following reviewer feedback.

Full citations and methodology will be published in [`docs/methodology.md`](docs/methodology.md) once Phase 0 validation is complete.

## Current stage: Phase 0 — validating the model

Before any tool ships, we're independently verifying the published findings hold on a real, self-collected dataset of agent-authored PRs. This stage produces:

- A labeled dataset of agent-authored PRs (`data/training/`)
- A minimal feature-extraction pipeline
- A simple baseline classifier (logistic regression) with honestly reported accuracy/AUC
- Write-up in `research/findings.md`

**No tool, CLI, or GitHub Action exists yet.** They come after the model proves out — see Roadmap.

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

Not yet open for contributions — the model is being validated first so early contributors aren't building on an unproven foundation. Watch/star to follow progress; a contribution guide will go up alongside Phase 1.

## License

TBD — likely Apache-2.0 or MIT, chosen to keep the core engine and data fully open while leaving room for an optional hosted layer later (see project notes).

---

*Pravix is an independent, research-grounded project. It is not affiliated with GitHub, Anthropic, OpenAI, or any coding agent vendor named above.*