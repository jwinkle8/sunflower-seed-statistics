# Contributing

Two people, one `main` branch. These rules keep `main` reproducible at every commit and make the PR
history something we can point to in the grade.

## Ground rules

1. **Never commit directly to `main`.** All changes go through a pull request and require one approval.
2. **Raw data should be append-only.** Once a collection session ends, `data/raw/` files are not edited by hand. 
   Corrections happen in `src/clean.py`.
3. **Generated files come from scripts.** Never hand-edit anything in `data/interim/`, `data/processed/`, or `data/final/`.
   Rerun the script and commit the output in the same PR as the code change that produced it.
4. **Don't move the goalposts.** Changes to the analysis plan after data collection starts
   (α, hypotheses, choice of test, effect size) must be called out in the PR description and in the report's
   Limitations or deviations section.

## Branches

Short-lived branches off `main`, named `<type>/<short-description>`:

| Type | Use for | Example |
|---|---|---|
| `feat/` | new code or functionality | `feat/pilot-effect-size` |
| `data/` | adding collected data | `data/session-1-raw` |
| `analysis/` | running analysis, committing results | `analysis/final-results` |
| `docs/` | report, README, slides | `docs/report-methods` |
| `fix/` | bug fixes | `fix/paired-pivot` |
| `tweak/` | bug fixes | `tweak/modify-environment` |

For example,

```bash
git switch main && git pull
git switch -c docs/report-methods
# ...work, commit...
git push -u origin docs/report-methods
gh pr create --fill        # or open the PR on GitHub
```

## Commits

- Small and focused, with an imperative subject line under ~60 characters: `Add outlier check to cleaning script`.
- Explain *why* in the body when it isn't obvious.
- Don't commit secrets, PII, or `.venv/`.

## Pull requests

The PR template (`.github/pull_request_template.md`) loads automatically. A good PR:

- does one thing, and has a title that says what;
- explains what changed and why, how it was tested, and what the reviewer should look at closely;
- includes regenerated outputs if it changes analysis code.

## Reviewing

Reviewing is part of the grade, so do it for real:

- **Pull the branch and run it**, don't just read the diff: `git switch <branch> && python src/analyze.py`.
- Check the statistics, not just the code. Does the test match the design? Were assumptions checked? Are the
  CI and effect size reported? Is anything p-hacked (α changed, outcome switched, data dropped without a logged reason)?
- Leave specific comments tied to lines. Use **Request changes** for anything blocking and **Comment** for nits
  (prefix with `nit:`).
- The author resolves each comment (fix it or reply with a reason). The reviewer approves, and the author
  squash-merges and deletes the branch.
