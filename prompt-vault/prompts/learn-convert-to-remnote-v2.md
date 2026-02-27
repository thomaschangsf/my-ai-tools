# Prompt: Flashcard Distillery — Convert Markdown to RemNote

**id:** `learn-convert-to-remnote-v2`  
**tags:** learning, remnote, flashcards, cloze, spaced-repetition, atomic  
**asks_for:** source (markdown file or directory), save_path (where to save the remnote)  
**outputs:** One RemNote-compatible Markdown file with atomic `Concept :: Definition` cards, nested sub-detail cards, and `{{cloze}}` deletions

---

## How to trigger

- **In Cursor:** @ this file. Provide the source (one markdown file or a directory of markdown files) and the full path where the remnote should be saved.
- **From vault:** `prompt show learn-convert-to-remnote-v2` then fill source and save_path.

---

## Prompt

Act as a specialized RemNote formatter. Read the provided markdown source, identify key concepts, and rewrite them into a high-density, atomic RemNote import format.

**Enter the following:**

1. **Source (markdown file or directory):**  
   _e.g. `docs/Agent - Execution - Logic And Tool.md` or `docs/`_

2. **Save path (where to save the remnote):**  
   _e.g. `docs/remnotes/Agent-Execution-remnote.md`_

---

### 1) Input

- **Source:** User-provided path.
  - If a **file:** use that single markdown as the source.
  - If a **directory:** use all `.md` files under it; merge into one coherent remnote.
- **Save path:** User-provided path. Create parent directories if they do not exist.

### 2) RemNote syntax

Use only valid RemNote import syntax:

- **Concept cards:** `Concept :: Definition` — creates a two-sided flashcard automatically.
- **Sub-detail cards:** Nested indented bullets with `::` when the sub-detail should also be a flashcard.
- **Cloze deletions:** `{{key term}}` inside a sentence to hide important terms.
- **Hierarchy:** Use tab indentation to preserve parent-child relationships. Maximum **3 levels** deep.
- **Section headers:** Use `#` headers to group cards by topic. These organize but do not create cards.
- **Self-contained concept names:** The left side of `::` is what the learner sees as the flashcard prompt during review — it must be understandable **without any parent context**. Never use bare labels like `When`, `How`, `The Problem`, `Component`, or `Analogy` alone. Instead, fold the parent concept into the name:
  - Bad: `When :: During the "Thinking Mode"...` (when what?)
  - Good: `Atomic Reasoning — When :: During the "Thinking Mode"...`
  - Bad: `Component :: LangGraph` (component of what?)
  - Good: `Orchestration Layer — Component :: LangGraph`
  - For table-derived cards, see the Table strategy section below.

### 3) Extraction heuristics — what to look for

Scan the source for three categories and organize output under these headers:

- **Facts** — Definitions, data points, formulas, named entities, constants, syntax rules.
- **Questions** — Cause/effect, how/why, contrasts between similar things, edge cases, common gotchas.
- **Concepts** — Abstractions, relationships between ideas, sequences and processes, mental models.

Not every source will have all three in equal measure. Extract what is there; do not fabricate content.

If the source already organizes content under its own headers (e.g., "Facts," "Questions," "Concepts"), respect that structure. Do not invent questions the author did not ask or synthesize answers from unrelated sections. If the author left a question unanswered or incomplete, preserve it as-is.

### 4) Fidelity — preserve the author's language

- **Use the author's original words** for definitions and explanations. Compress by removing filler words and redundant clauses, but do not rephrase the core meaning in your own words.
- **Do not synthesize.** Every card must trace back to a specific passage in the source. If a claim doesn't appear in the source, do not create a card for it.
- **Preserve attributions.** If the source cites a paper, person, or framework (e.g., "Anthropic, 2025a"), keep the citation in the card.
- **Preserve analogies and examples** from the source — they aid recall and are deliberate choices by the author.

### 5) Brevity — Minimum Effective Information

- **One fact per card.** If a definition has multiple clauses, split into separate `Concept :: Definition` entries.
- **Definitions: 1–2 sentences max.** Trim filler but keep the author's phrasing intact.
- **No filler.** Strip hedging ("it is worth noting that"), conversational padding ("as we saw earlier"), and redundant qualifiers. Do not strip substantive clauses.
- **Concrete over abstract.** Include a single short example only when it genuinely clarifies the definition.
- **Tables — contrast-pair cloze (text-based table occlusion):** Use different strategies depending on the table type:
  - **Side-by-side comparisons** (e.g., "LangGraph vs Harbor"): Create one card per row using contrast-pair cloze. Put both sides in the answer with `{{cloze}}` on both values. The learner sees the dimension name and must recall both sides.
    - Example: `LangGraph vs Harbor — Philosophy :: LangGraph: {{Graph}} (Nodes/Edges); Harbor: {{Harness}} (Sandbox/Skills).`
  - **NxM feature matrices** (e.g., comparing 4 techniques across 4 features): Create one card per row as a question that highlights what is distinctive. Use `{{cloze}}` on the key differentiator.
    - Example: `Which augmentation techniques provide procedural guidance? :: Only {{Skills}} (Prompts: limited; RAG and Tools: none).`
  - **Multi-column attribute tables** (e.g., Layer / Component / Analogy / Example): Keep as self-contained concept-per-cell cards. These describe, not compare.
    - Example: `Orchestration Layer — Analogy :: The {{Project Manager}} (e.g., "Ensure this PR is safe to merge.").`
  - In all cases, preserve all columns and prioritize analogies and examples.

### 6) Example

**Example 1 — Prose + attribute table:**

```markdown
## Gradient Descent

Gradient descent is an optimization algorithm used to minimize a loss function.
It works by computing the gradient of the loss and updating parameters in the
opposite direction (Ruder, 2016). The learning rate controls the step size.
It's like turning the steering wheel — a small rate means gentle turns.

| Variant          | Update Rule       | Trade-off              |
| ---------------- | ----------------- | ---------------------- |
| Batch            | Uses full dataset | Stable but slow        |
| Stochastic (SGD) | Uses one sample   | Fast but noisy         |
| Mini-batch       | Uses a subset     | Balances speed & noise |
```

Output:

```markdown
- Gradient Descent :: An optimization algorithm used to minimize a {{loss function}} by computing the gradient and updating parameters in the opposite direction (Ruder, 2016).
	- Gradient Descent — Learning Rate :: Controls the {{step size}} of parameter updates — like turning the steering wheel; a small rate means gentle turns.
	- Gradient Descent — Variants
		- Batch :: Update rule: uses the {{full dataset}}. Trade-off: stable but {{slow}}.
		- SGD :: Update rule: uses {{one sample}}. Trade-off: fast but {{noisy}}.
		- Mini-batch :: Update rule: uses a {{subset}}. Trade-off: balances {{speed}} and noise.
```

**Example 2 — Side-by-side comparison table (contrast-pair cloze):**

```markdown
| Feature      | LangGraph                        | Harbor                              |
|--------------|----------------------------------|-------------------------------------|
| Primary Goal | Orchestration: logic and flow    | Evaluation & Skills: procedural knowledge |
| Philosophy   | Agent is a Graph (Nodes/Edges)   | Agent is a Harness (Sandbox/Skills) |
| Analogy      | The Script of a play             | The Stage and the Manuals           |
```

Output:

```markdown
- LangGraph vs Harbor — Primary Goal :: LangGraph: {{Orchestration}} (logic and flow); Harbor: {{Evaluation & Skills}} (procedural knowledge).
- LangGraph vs Harbor — Philosophy :: LangGraph: agent is a {{Graph}} (Nodes/Edges); Harbor: agent is a {{Harness}} (Sandbox/Skills).
- LangGraph vs Harbor — Analogy :: LangGraph: the {{Script}} of a play; Harbor: the {{Stage}} and the Manuals.
```

**Example 3 — NxM feature matrix (distinctive-feature question):**

```markdown
|                      | Prompts | RAG | Tools | Skills |
|----------------------|---------|-----|-------|--------|
| Procedural guidance  | Limited | ×   | ×     | ✓      |
| Executable resources | ×       | ×   | ✓     | ✓      |
```

Output:

```markdown
- Which augmentation techniques provide procedural guidance? :: Only {{Skills}} (Prompts: limited; RAG and Tools: none).
- Which augmentation techniques have executable resources? :: {{Tools}} and {{Skills}} (not Prompts or RAG).
```

### 7) Deduplication

After generating cards, scan for duplicates before writing the file. Apply these five rules in order:

1. **Summary vs detail.** When the same fact appears in a summary table and a detailed prose section, keep only the detailed version (it is a superset). Merge any unique information from the summary (e.g., an analogy) into the detailed card.
2. **Inverse pairs.** When two cards are logical inverses of each other (card A's question is card B's answer and vice versa), keep the one with richer context in its answer. Delete the other.
3. **First-occurrence ownership.** When the same atomic fact appears across multiple sections, create a card only where the fact is **first introduced** in the source. Later sections that reference it use the fact as supporting context within other cards, not as a new standalone card.
4. **Non-discriminating table rows.** Skip table rows where all values are identical (e.g., all four techniques share the same property). There is nothing distinctive to recall.
5. **Complementary pair merge.** When two cards are "When X?" and "When not X?" (or "Use A" and "Use B" for the same decision), merge into a single card that tests the distinction boundary.

Report dedup results in the verification: number of cards removed and which rule applied.

### 8) Fidelity verification

After deduplication, re-read both the source and the output. Perform the following checks:

1. **Traceability.** For each card, identify the source passage it came from. If a card cannot be traced to a specific sentence, bullet, or table cell in the source, **delete it**.
2. **Completeness.** Check for substantive content in the source that was not converted into any card (excluding content removed by dedup rules). List any omissions.
3. **Accuracy.** Compare the wording of each card against its source passage. Flag any card where the meaning shifted during compression — a dropped clause, a softened claim, or a generalized specific.
4. **Tables.** Verify every column from every source table appears in the output (unless the entire row was removed by dedup rule 4). If a column was dropped, add it back.
5. **Citations.** Verify all source attributions (author, year, framework name) appear in the output.

Report the verification results in the reply:
- Number of cards that passed traceability
- Any cards deleted for lacking a source passage
- Any omissions from the source (content that should have been a card but wasn't)
- Any accuracy flags (cards where wording diverged from the source)
- Dedup summary: cards removed and which rule applied to each

If issues are found, fix the remnote file before reporting.

### 9) Output

- Write the remnote content to the **exact save path** given.
- If the parent directory does not exist, create it.
- Reply with: source used, save path, total card count, and the fidelity verification report (including dedup summary).
