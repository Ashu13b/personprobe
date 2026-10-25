---
name: field-review
description: Deterministic-contract code review over a change set. Use when reviewing a diff, a commit, a branch range, or a workspace before commit/merge, especially when findings must be machine-verifiable and coverage-complete rather than impressionistic.
---

# Field Review

Execute the review contract emitted by `ck review --plan`. The engine has already done
the deterministic half — file selection with exclusion reasons, rule routing, batching.
Your half is judgment: find real defects, and only real defects.

Do not modify implementation code during this review.

---

## 1. Load the contract

Run `ck review --plan` (optionally `--from <ref> --to <ref>`, `--commit <sha>`,
`--background "<task>"`). Its `instructions` field is the operational protocol —
coverage mandate, per-file diff commands, the finding shape, the severity policy.
Follow it; this file does not restate it. What it gives you beyond that:

- `mode` — `workspace` | `commit` | `range` (with `merge_base`)
- `reviewable_files` — the only files you review (paths, status, +/- counts)
- `excluded_files` — with `exclude_reason` — never review these, never "rescue" them
- `rule_groups` — the checklist text per file group (source/pattern provenance)
- `batches` — the review order; rule identity groups them, 10 files max each

## 2. Verify your own findings before returning them

`existing_code` must be a **verbatim snippet from the change** — the engine re-anchors
it and drops the finding if it cannot find the snippet where you claim. `0`/`0` means
unanchored (whole-file or conceptual claims) — never invent line numbers.

Run the deterministic reflection over your findings first:

```bash
ck review --findings my_findings.json [--commit <sha> | --from <ref> --to <ref>]
```

Pass the same ref scope you reviewed with — the reflection checks scope against that
change set, not the workspace. Fix the dropped ones that were *your* error (wrong line
number, paraphrased snippet); leave unanchored-but-correct claims as `start_line: 0`
rather than guessing.

## 3. Judgment bias — approve unless proven wrong

When you are unsure a claim is a real defect, **do not report it**. Keeping a wrong
comment costs the reader seconds; a false alarm costs more trust than a missed minor
issue. "Suspicious", "can't verify", and "low value" all mean: drop it silently.

Conversely, a claim you *can* prove from the diff deserves to be stated plainly — do
not hedge a proven defect into a question.

## 4. Return

1. Findings JSON (the `comments` shape), each one anchored and enum-valid.
2. The coverage summary (`total_files`, `reviewed_files`, `skipped_files`, `coverage_rate`).
3. A one-line verdict: `PASS`, `PASS with N findings`, or `BLOCK` (only when a
   critical/high security or correctness finding is proven).
