# Prompt: Bloom's Taxonomy Algorithm Study Guide

**id:** `study-algo-notebook`  
**tags:** learning, algorithms, bloom-taxonomy, interview-prep, study-guide  
**asks_for:** source (Jupyter notebook file)  
**outputs:** One Markdown study guide with insights organized by Bloom's Taxonomy levels 3-6, cross-problem patterns, gaps, and interview follow-ups

---

## How to trigger

- **In Cursor:** `Apply @study-algo-notebook.md to @<notebook>.ipynb`
- **From vault:** `prompt show study-algo-notebook` then provide the notebook path.

---

## Prompt

Act as a principal ML engineer preparing a personal algorithm interview study guide. Read the provided Jupyter notebook carefully — every cell, every comment, every complexity analysis. Produce a dense Markdown study guide that applies Bloom's Taxonomy levels 3, 4, 5, and 6 to every problem in the notebook.

**Enter the following:**

1. **Source (Jupyter notebook):**  
   _e.g. `notebooks/algos/Algo-Recursion-BackTracking.ipynb`_

---

### 1) Input

- **Source:** The user-provided `.ipynb` file. Read all cells: markdown, code, and comments.
- **Output path:** Same directory as the source, same base name with `.md` extension.  
  _e.g. `notebooks/algos/Algo-Recursion-BackTracking.ipynb` → `notebooks/algos/Algo-Recursion-BackTracking.md`_

### 2) Bloom's Taxonomy Levels

Apply these four levels of cognitive depth to the problems in the notebook:

- **Level 3 (Apply):** Execute the algorithm on concrete inputs. Trace through code step-by-step, predict outputs, and identify the exact sequence of operations the algorithm performs.
- **Level 4 (Analyze):** Decompose *why* approaches work, not just how. Compare structural differences between problems.
- **Level 5 (Evaluate):** Critique trade-offs, judge when an approach is wrong, defend or attack design choices.
- **Level 6 (Create):** Synthesize reusable frameworks, transfer patterns to novel problems, design new variants.

### 3) Document Structure

Generate these sections in order:

#### Section 1: Level 3 — Apply ("Use It")

For each problem in the notebook:

- **Dry-run trace:** Pick a small, concrete input (from the notebook if available, otherwise construct one). Walk through the algorithm step-by-step showing the state at each iteration or recursive call (e.g., stack/queue contents, variable values, visited set). Keep traces compact — show enough steps to reveal the algorithm's rhythm, then summarize the rest.
- **Template instantiation:** Show how the notebook's code instantiates the general paradigm template for this topic (e.g., BFS queue loop, DFS recursion, topological sort setup). Identify the **four key slots**: initialization, expansion/neighbor generation, termination condition, and result extraction.
- **Edge-case inventory:** List 2-3 edge cases (e.g., empty input, single node, disconnected graph, graph with cycles) and predict the algorithm's behavior on each. Note whether the notebook's code handles them correctly.

#### Section 2: Level 4 — Analyze ("Take It Apart")

For each problem in the notebook:

- **Structural decomposition:** Map the solution to the choose → explore → unchoose backtracking template (or the relevant paradigm template for non-backtracking notebooks). Identify what each part of the code corresponds to.
- **Complexity anatomy:** Identify the (branching factor, depth, pruning mechanism) triple. Explain the recurrence relation and walk through the recursion tree argument.
- **Cross-problem comparison:** Compare problems within the notebook on at least two structural dimensions (e.g., static vs shrinking branching factor, memoizable vs non-memoizable, in-place vs auxiliary state).

After per-problem analysis, include one synthesis paragraph identifying the deepest structural insight that connects multiple problems.

#### Section 3: Level 5 — Evaluate ("Judge and Justify")

For each problem in the notebook:

- **When this approach fails:** Identify at least one scenario where the notebook's approach is suboptimal and name the better alternative.
- **Pruning effectiveness:** Quantify or estimate how much the pruning reduces the search space versus brute force.
- **Code critique:** Flag any bugs, naming inconsistencies, correctness pitfalls, or subtle errors in the notebook code. These are valuable because they mirror real interview mistakes.
- **Defend-your-analysis drill:** Write a 2-3 sentence script for defending the runtime complexity as if an interviewer challenged it.

#### Section 4: Level 6 — Create ("Synthesize and Transfer")

- **Meta-template:** Synthesize one pseudocode template that unifies all problems in the notebook. Show how each problem is a parameterization of: `candidates` (choices), `constraint` (pruning), `goal` (completion), `state` (modify/restore).
- **Pattern transfer heuristic:** Build a decision tree or checklist: given a new unseen problem, which pattern from this notebook applies? Use problem characteristics as decision criteria.
- **Compose patterns:** Show one example of combining two patterns from the notebook to solve a harder problem.
- **Design a variant:** Create one novel problem variant by modifying constraints of an existing problem. Describe what changes in the solution.

#### Section 5: Cross-Problem Pattern Summary

For each problem in the notebook, list:

- Pattern family (e.g., subset, permutation, constraint-backtracking, mathematical, greedy)
- Branching factor and depth
- Key pruning mechanism
- Time and space complexity
- One-sentence insight (the single most important thing to remember)

#### Section 6: Gaps — What's Missing

Identify 3-5 related problem types or techniques that the notebook does not cover but that a complete understanding of this topic requires. For each gap, name one canonical LeetCode-style problem.

#### Section 7: Interview Extras

- **Follow-up questions:** For each problem, list 2-3 follow-up questions an interviewer would ask after you solve it.
- **Mistake log template:** Include a blank template section where the user can record their own bugs and misunderstandings during practice.
- **Spaced repetition triggers:** For each problem, write one trigger question suitable for Anki (a question that forces recall of the key structural insight, not surface-level "what's the runtime?").

### 4) Style Rules

- **Minimal pseudocode only.** Illustrate patterns with short pseudocode snippets (5-10 lines max), not full solutions. The notebook already has the full code.
- **Dense and direct.** No filler, no "in this section we will discuss." Every sentence should teach or test.
- **Preserve the notebook's analysis.** When the notebook has a good insight (e.g., a recursion tree walkthrough), reference and build on it rather than replacing it.
- **Flag, don't fix.** When noting code bugs, describe the bug and why it matters. Do not rewrite the corrected code (the user will fix it in the notebook).

### 5) Verification

After generating the guide, perform these checks:

1. **Coverage:** Every problem in the notebook has entries in all seven sections. List any gaps.
2. **Accuracy:** Complexity claims in the guide match the notebook's analysis (or explicitly note where the guide disagrees and why).
3. **No fabrication:** Every insight traces to content in the notebook or to well-known algorithm theory. Do not invent problem properties that aren't there.

Report: total problem count, total insight count per Bloom level, and any verification flags.

### 6) Output

- Write the study guide to the output path (same directory, `.md` extension).
- Reply with: source notebook, output path, problem count, and the verification report.
