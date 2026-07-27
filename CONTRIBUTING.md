# Contributing to Pravix

Thanks for your interest in Pravix.

## Current status: contributions not yet open

Pravix is in **Phase 0 — Model Validation** (see the [Roadmap](README.md#roadmap)
in the README for where this fits). Before accepting contributions to the
codebase, we're independently verifying that the core prediction model
actually holds signal on real, self-collected data. Building infrastructure
or features on top of an unproven model would waste contributor time, so
we're deliberately holding off.

## What you can do right now

- **Watch/star the repo** to be notified when Phase 1 opens.
- **Open an issue** using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
  if you have relevant research, datasets, or prior art we should be aware
  of — this is genuinely useful at this stage. Use the
  [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) if something
  in the research scripts (`research/pull_pr_data.py`) doesn't run correctly
  for you.
- **Read `research/findings.md`** (once published) and challenge our
  methodology if you think it's flawed. Honest, specific pushback — "your
  sample is too small," "this feature leaks the label," "your baseline is
  weak" — is more valuable right now than code.
- **Point out prior art.** If you know of an existing tool or paper doing
  this exact thing, please open an issue — we'd rather find out now than
  after launch.

## When contributions open (Phase 1+)

Once the core model is validated, we'll open contributions to:

- `packages/core` — feature extraction, model, calibration
- `packages/cli` — the command-line tool
- `packages/github-action` — the GitHub Action wrapper
- `docs/` — methodology, guides, FAQ

We'll publish a full contribution guide at that point covering coding
standards, commit conventions ([Conventional Commits](https://www.conventionalcommits.org/)),
branch/PR workflow, and how to run tests locally. This file will be
updated when that happens — watch the repo to be notified.

## Licensing of contributions

Pravix is licensed under [Apache-2.0](LICENSE). Any contribution you submit
once contributions open will be licensed under the same terms — please
don't submit code you don't have the rights to relicense this way.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating, you agree to abide by its terms.

## Questions?

Open an issue with the `question` label, or check
[`SECURITY.md`](SECURITY.md) if it's a security concern rather than a
general question.