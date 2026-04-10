# PR review prompt

PR review using **`@pr-review-agent.md`** and **`@pr-review-bar.md`**.

- Apply the **review bar** (depth, themes, style, severity, 7 recommendations): **`@pr-review-bar.md`**
- Apply **everything below** for Git scope, what to review, how to point at changes on GitHub, and the **exact fields** each recommendation must include.

---

## Diff scope (dynamic — do not assume a fixed base branch)

- I will state the PR **base ref** explicitly (e.g. `origin/main`, `origin/causal-training`, or a branch name). If I don’t, infer the base from the GitHub/GitLab PR **into** branch and use `origin/<that-branch>` when it exists locally.
- Compute: `MERGE_BASE=$(git merge-base HEAD <BASE_REF>)`
- Review only what’s in: `git diff "$MERGE_BASE"..HEAD`
- **Do not assume `master`/`main`.** Stacked or feature PRs often target another branch (e.g. `causal-training`). Using the wrong `<BASE_REF>` includes every commit that is already merged into the real base but not into `master`, which **bloats** the diff, **inflates** the file count, and **misaligns** all hunk anchors with GitHub.

**Reconcile file count with GitHub (sanity check):**

- Run: `git fetch origin` (stale refs cause silent mismatch).
- Then: `echo $(git diff --name-only "$(git merge-base HEAD <BASE_REF>)"..HEAD | wc -l)`  
  This number **must** match the PR’s **Files changed** count when `<BASE_REF>` is the PR’s **into** / target branch (e.g. `origin/causal-training`).
- If it does not match, fix `<BASE_REF>` to `origin/<into-branch>` from the PR page and recompute `MERGE_BASE`. Do **not** ship review stats that disagree with GitHub without calling this out.

**One-line base instruction (prepend when needed):**  
PR base ref for this run: `<BASE_REF>`

---

## What to review

- **Python only** (`.py`).
- **Ignore tests**: exclude paths matching `**/tests/**`, `**/*_test.py`, `**/test_*.py`, and pytest-style test modules.
- **Files in scope**: only `.py` paths that appear in `git diff --name-only "$MERGE_BASE"..HEAD` and are not excluded as tests above.
- **Lines in scope**: prioritize findings on **changed lines only**—lines that appear as **`+` or `-`** in the unified diff for those files. Treat **new `+` lines** as the primary review surface; **`−` removals** are in scope when the risk is “this deletion breaks …”.
- **Unchanged code**: do **not** use unchanged lines as the main anchor for a finding. You may reference unchanged code **only** when it is strictly necessary to explain behavior caused by a PR change (label that snippet **“Unchanged context (not part of PR diff)”** and keep it minimal).

**Why:** Findings must be verifiable from GitHub **Files changed**; anchoring to unchanged lines caused mismatches with the PR UI.

---

## How to cite location (must match GitHub “Files changed”)

**Vocabulary (use plain language in the write-up; Git terms are optional hints):**

- In GitHub’s **Files changed** view, a PR shows **one file at a time**. Each file is made of one or more **change blocks**: a run of removed lines (red) and/or added lines (green), sometimes with a few gray context lines. In Git this is often called a **hunk**; you do **not** need to use the word *hunk* in the review—say **“the change in `<file>` where …”** and describe it (e.g. “the mapping dict loses PC/GES entries”).

**Location — use all that apply:**

- **A — Diff hunk header (required):** Paste the exact hunk header from  
  `git diff "$MERGE_BASE"..HEAD -- <file>`  
  for that change block, e.g. `@@ -120,7 +120,15 @@`. That string is searchable in the local diff and matches Git’s idea of the block; GitHub’s **Files changed** uses the same patch (same `+start` for the green side when the PR base matches `MERGE_BASE`).
- **B — New-side start line:** The **`+N`** from that header is the first line number of the green (post-PR) side for that block—same numbering GitHub shows on the right for added lines in that block.
- **C — Post-PR file line (optional):** Absolute line in the **full file on the PR branch** for one **added** line, only if it helps; must still match a `+` line in the diff.

Do **not** cite post-PR line numbers for code that did **not** change unless labeled **Unchanged context** per above.

**Verify PR parity:** Your `MERGE_BASE` must be the same merge base GitHub uses for the PR (the **into** branch tip when the PR was opened/rebased, or re-fetch and recompute). If local `git diff "$MERGE_BASE"..HEAD -- <file>` does not match **Files changed** for that file, fix **`<BASE_REF>`** / update the branch before writing line anchors.

**Why:** Reviewers reconcile comments with the PR diff; the hunk header ties the note to one concrete block and reduces off-by-N line drift.

---

## Output

- Always print: (a) `git diff --name-only "$MERGE_BASE"..HEAD | wc -l` as **PR total files**, and (b) the count of **scoped non-test `.py` paths** actually reviewed, so I can verify against GitHub.
- Exactly **7** recommendations, meeting the bar in **`@pr-review-bar.md`** (themes, style, severity).
- **Order by severity (required):** Number recommendations **1–7 in descending order of risk** — **recommendation 1 = highest severity** (the issue authors should address first). Use **high → medium → low** as the primary sort. When two items share the same severity, order by: **definite** before **needs verification**, then by **blast radius** (e.g. export/training correctness and contract breaks before observability or style). If the scoped diff cannot support seven distinct items, state that explicitly and give as many substantive recommendations as the diff supports—**do not** inflate severity to fill slots; keep labels honest per **`@pr-review-bar.md`**.
- **Author-oriented code blocks:** Each recommendation’s two fences are **Current (PR branch)** — what reviewers see on the PR — and **Recommended** — what to implement if they accept the finding. Do **not** label them “Before/After” in the sense of merge-base vs. PR unless you are explicitly auditing the raw patch for parity.

### For each recommendation — include **all** of the following, in this order

- **Title** — one short line describing the recommendation (Recommended action).

- **File path** and **where in the PR** — repo-relative path, then **plain-language** pointer: *which* change block (see vocabulary above). Include the **diff hunk header** (`@@ … @@`) for that block per location **A** above.

- **Context** — before “why it matters,” orient the reader in **three short parts** (bullets or labeled sentences):
  1. **What this code is for** — e.g. “Runs during Spark model export,” “Defines the public training API,” “Builds the pipeline plan for causal jobs.”
  2. **What the PR changed here** — one sentence, neutral: e.g. “This PR removes PC/GES/FCI from the algorithm map.”
  3. **What connects them** — one sentence: why that change interacts with that responsibility (the logical link the reader needs).

- **Why it matters** — 2–4 sentences **after** Context: concrete failure or cost (what breaks, when, for whom), production or scale angle, and **who/what** is affected (training job, export JSON, inference service, config authors, downstream consumers).

- **Severity / confidence** — e.g. high/medium/low and **definite** vs. **needs verification** (say what you would check). Align with **`@pr-review-bar.md`**.

- **Code: Current vs. Recommended (norm)** — use **two separate fenced code blocks** so authors see **what the PR does now** and **what to implement** if they accept the finding. This is **not** “base branch vs. PR branch” (that mirrors GitHub’s red/green and confuses readers who want actionable fixes).

  - **Current (PR branch)** — put the code **as it exists on the PR under review** (`HEAD`) in its **own** fence (language `python` if applicable). Use, in order of preference:
    1. The **green / `+` side** of the unified diff for that change block (`git diff "$MERGE_BASE"..HEAD -- <file>`), or an equivalent minimal snippet from **`git show HEAD:<path>`**—this is what reviewers see on the right in **Files changed**.
    2. If the PR **only removes** lines in that block and nothing replaces them: a one-line placeholder is fine, e.g. `— (behavior or symbol removed on PR branch; see hunk header) —`, optionally plus a **minimal** red-side snippet in prose *outside* the “Current” fence if needed to name what disappeared.
    3. If the path is **new on the branch**: show the **new file content** (or the relevant excerpt) as Current—that *is* the PR state.
    4. If Current would be misleading without one line of context, add a single labeled sentence above the fence (not a second normative block).

    Keep each **Current** block short.

  - **Recommended** — put the **suggested end state after applying this recommendation** in a **separate** fence. **This fence must contain real, paste-ready code changes**—not advice disguised as comments (e.g. do **not** use only `# TODO:` or `# Prefer …` lines without an actual implementation).

    **Required shape for code fixes (default for all 7 items):**
    - Show **concrete Python** (or the relevant language) that authors could apply: a full replacement function/class, a minimal patched block, or a **unified-diff-style** snippet with `+`/`-` lines if that is clearer.
    - Match the project’s imports, naming, and types; keep the snippet **minimal** but **complete enough to implement** the fix (e.g. include `initializer=` / `initargs=` if recommending a pool change, include the full `if` guard if recommending validation).
    - **Forbidden in Recommended:** comment-only placeholders, pseudo-code without real syntax, or vague bullets that do not map to specific symbols/lines.

    **Non-code exception (rare):** Use at most **one** of the seven recommendations for pure process/docs/release notes. In that case the **Recommended** fence must be explicit prose (e.g. “Add to CHANGELOG: …” or “Open ticket: …”) and the **Title** must say **(non-code)**. All other recommendations **must** include real code.

  This must **not** be the same fence as **Current (PR branch)**.

- **Optional tradeoff** — when the fix has a cost (API churn, perf, stricter validation), 1–2 sentences.

- **PR tie-in** — one sentence: how this recommendation maps to the **specific** lines changed (added/removed) in that file’s diff.

**Learnings captured here:** (1) **Two separate code fences**: **Current (PR branch)** then **Recommended**—**Recommended must be implementable code** (see rules above), not a replay of “old vs. new” from Git’s perspective. (2) **Context** (what/why link) before impact. (3) **Plain-language “change block”** plus mandatory **`@@` hunk header** so anchors match the PR patch. (4) **Diff-first** findings; **Current** reflects **HEAD** for that block (green side or post-deletion state), not the merge-base snapshot. (5) **Recommendations sorted by severity**—#1 is the highest-risk item; do not order by file path or discovery order.

---

## Process

1. List the scoped changed `.py` files (non-test) from `git diff --name-only "$MERGE_BASE"..HEAD`.
2. For each file, review **only** the output of `git diff "$MERGE_BASE"..HEAD -- <file>` (each **change block** in that diff). Do not full-file review except to resolve ambiguity needed for a finding that is still tied to a specific PR change.
3. Draft findings, assign **severity / confidence** per **`@pr-review-bar.md`**, then **sort into final order** (highest severity first, then tie-breakers per **Output** above) before numbering **1–7** in the written review.
