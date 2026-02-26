# Prompt: Convert Learning Material to RemNote Flashcards

**id:** `learn-convert-to-remnote`  
**tags:** learning, remnote, flashcards, cloze, spaced-repetition  
**asks_for:** source (markdown file or directory), save_path (where to save the remnote), bloom_distribution (optional)  
**outputs:** One RemNote-compatible Markdown file with Concept→Definition, Cloze, Comparison, and Why/How cards, aligned to Bloom's taxonomy (Remember through Create), with `## Bloom::<Level>` metadata on each card

---

## How to trigger

- **In Cursor:** @ this file. Provide the source (one markdown file or a directory of markdown files) and the full path where the remnote should be saved. Optionally add a Bloom distribution (e.g. "Apply/Analyze/Evaluate: 50%").
- **From vault:** `prompt show learn-convert-to-remnote` then fill source, save_path, and optionally bloom_distribution.

---

## Prompt

Convert the given learning material into high-quality RemNote flashcards.

**Enter the following (required: 1–2; optional: 3):**

1. **Source (markdown file or directory):**  
   _e.g. `docs/Agent - Execution - Logic And Tool.md` or `docs/`_

2. **Save path (where to save the remnote):**  
   _e.g. `docs/remnotes/Agent-Execution-remnote.md`_

3. **Bloom distribution (optional):** Target percentages by level. If omitted, aim for natural variety.  
   _e.g. `Remember: 20, Understand: 25, Apply: 25, Analyze: 20, Evaluate: 10` or `Apply/Analyze/Evaluate: 50%`_

---

### 1) Input (from user above)

- **Source:** User-provided path.
  - If a **file:** use that single markdown as the source.
  - If a **directory:** use all markdown (`.md`) files under it as the source; merge content for one coherent remnote or one file per doc (your choice; state it).
- **Save path:** User-provided path. Create the parent directory if it does not exist.
- **Bloom distribution (optional):** If provided, treat as target percentages or ratios. Aim for this distribution when designing cards. Quality over strict adherence—the source material may not support all levels equally (e.g. a glossary may be mostly Remember); if so, note it in the output.

### 2) Bloom's taxonomy (cognitive levels)

Aim for variety across these levels when designing cards:

1. **Remember** — Recall facts (definitions, terms, lists).
2. **Understand** — Explain concepts in your own words, summarize, give examples.
3. **Apply** — Use knowledge in new situations (e.g. "Given X, what would you do?").
4. **Analyze** — Break apart, identify relationships, compare/contrast, infer causes.
5. **Evaluate** — Judge, prioritize, justify, assess pros/cons or trade-offs.
6. **Create** — Generate novel solutions, design approaches, combine ideas.

Map card types to levels where natural: e.g. Cloze → Remember; Concept→Definition → Remember/Understand; Comparison → Analyze; Why/How → Understand/Apply/Analyze/Evaluate.

**When a Bloom distribution is requested:** Reframe content to hit higher levels. For more Apply: use scenario-based questions ("Given an agent with 80k tokens and a 50-turn history, which time-slot resolution would you use for turns 1–20?"). For more Analyze: add comparison cards ("How does Vector RAG differ from Graph-Based for retrieval?"). For more Evaluate: add trade-off and prioritization questions ("When would you choose Hierarchical over Temporal? What are the trade-offs?"). The source provides the concepts; you choose how to test them.

### 3) Card types to generate

Produce RemNote-compatible Markdown with:

1. **Concept → Definition** — Clear concept name or question, then a concise definition or answer. Use `Question >> Answer` for forward cards.
2. **Cloze deletions** — Use `{{text to hide}}` for the part the user should recall. Prefer one idea per cloze; use multiple `{{c1::…}}`-style only if RemNote is known to support it, otherwise plain `{{…}}`.
3. **Comparison cards** — Side-by-side or Q/A comparing two concepts (e.g. "How does X differ from Y?" >> "…").
4. **Why / How cards** — Questions that ask for reasoning or process: "Why …?", "How does …?", "What is the trade-off …?" with short, precise answers.

### 4) RemNote format

- **Forward cards:** `Question >> Answer` (or `Concept >> Definition`).
- **Cloze cards:** `{{text to hide}}` inside a sentence or bullet.
- Preserve hierarchy with `##` and `-` so structure imports cleanly.
- At the end, add a one-line *Source:* reference (file or directory path).

**Bloom metadata:** Tag each card with its Bloom level so users can filter or analyze. Add `## Bloom::<Level>` at the end of each card line (e.g. `Question >> Answer ## Bloom::Remember`). Use exactly: `Remember`, `Understand`, `Apply`, `Analyze`, `Evaluate`, or `Create`. If RemNote's importer does not parse inline `##` as tags, the metadata will still be visible; users can add tags manually or use section headers to group cards by Bloom level.

### 5) Quality

- Extract testable facts, definitions, and relationships from the source; avoid filler.
- Keep answers concise (one to a few sentences) so cards are quick to review.
- For technical docs: include key terms, flows (e.g. step sequences), pros/cons, and tensions or trade-offs as separate cards.
- Span Bloom's levels: include Remember/Understand cards for foundations, plus Apply/Analyze/Evaluate where the material supports deeper questions.

### 6) Output

- Write the remnote content to the **exact save path** given.
- If the parent directory does not exist, create it.
- Reply with: source used, save path, a short summary of card counts by type (Concept/Definition, Cloze, Comparison, Why/How), and counts by Bloom level (Remember, Understand, Apply, etc.). If a Bloom distribution was requested, also report target vs actual percentages and any constraints from the source material.
