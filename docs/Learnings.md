# 1 Understanding
### 1.1 TLDR
- LangGraph provides a structured state-machine workflow (nodes, edges, shared state) around LLM calls, but you still need explicit schemas/validation/parsing to make the model outputs reliably structured.

- From Cursor, you can run code that invokes a LangGraph graph (e.g., a CLI/script/test); the process may block until completion, or it can stream events and pause for human/tool input depending on how the graph is built.

- A LangGraph workflow can run directly inside your project codebase, or it can run inside a separate service and be exposed as an MCP tool—so clients call the tool without needing to know a LangGraph graph is executing underneath.

- ==Cursor skills vs MCP==:
	- MCP is tooling that can implement workflows; skills are how Cursor decide/structure what to do / say/ how to think.
		- MCP plan auto : workflow consists of state transitions, perfect for langgraph. workflow to generate 3 levels of markdown: design, programming interface. I need to tell cursor to run mcp my-ai-tools
		- ~/.cursor/skills/principal-ml-planning is a way to align cursor to certain thinking pattern, ie tradeoffs. Triggered by cursor agent mode, instruction relevance to skill purpose, etc.. You can also explicitly tell cursor to apply skill principal-ml-planning
	- Cursor rules implements policy + preference + constraints that shape behavior across chat
	- MCP enables integration to broaden context (ie jira), actions, persistence
### 1.2 Details
- Langgraph enforces structure workflow (node, edges, state) around LLM unstructured probabilitic returns
	- Schemas, validators, and parsers are still needed in the node to parse llm rsults
	- Key: langgraph enables control flow + state management + checkpointing/retries/human-in-loop
- Cursor can invoke langgraph graphs programatically.  In our case, cursor waits for the result.
	- langraph can be streaming, iterative, and human in loop
	- A graph can yield intermediate events, pause for input, or be served behind an API.
- Langgraph logic can be in a project, or hide behind a mcp server, like my-ai-tools.plan_iterative
	- An MCP tool can wrap LangGraph (or any orchestration), so clients call the tool without knowing the internal graph

# 2 Example: EDC Data Science Agent
### Flow
```
+--> edc_schema_discovery_agent.langgraph_flow.build_graph
	- GraphState (use_case, salesforce_dmos, open_dataset_dmo, ...)
	      - nodes: select_dmos -> review_dmo_selection -> emit_contract
+--> edc_schema_discovery_agent.ollama.rank_dmos_top_k (LLM ranker)
+--> edc_schema_discovery_agent.matching.string_match (fallback matcher)
+--> edc_schema_discovery_agent.evals.dmo_ranking.review.interactive_dmo_reviewer (human-in-loop)
```
### Langgraph Code
```python
from dataclasses import dataclass
from langgraph.graph import StateGraph, END

# 1) State shared across nodes
@dataclass
class GraphState:
    use_case: str
    candidate_dmos: list[dict] | None = None
    ranked_dmos: list[str] | None = None

# 2) Node: load candidates (via DB tool exposed by an MCP server)
def load_candidates(state: GraphState, tools) -> GraphState:
    # tools.db_query is assumed to come from an MCP server Cursor is connected to
    rows = tools.db_query(
        "SELECT name, description FROM dmo_catalog WHERE active = true LIMIT 200"
    )
    state.candidate_dmos = rows
    return state

# 3) Node: rank with GPT‑5.2
def rank_with_llm(state: GraphState, llm) -> GraphState:
    prompt = f"""Use case: {state.use_case}
Candidates: {state.candidate_dmos}
Return a JSON list of the best 10 DMO names."""
    ranked = llm.invoke(prompt)  # GPT‑5.2 call (implementation depends on your LLM wrapper)
    state.ranked_dmos = ranked
    return state

# 4) Node: persist output back to DB (again via MCP tool)
def persist_result(state: GraphState, tools) -> GraphState:
    tools.db_execute(
        "INSERT INTO dmo_rank_runs(use_case, ranked_dmos_json) VALUES (?, ?)",
        [state.use_case, state.ranked_dmos],
    )
    return state

# 5) Wire the graph
g = StateGraph(GraphState)
g.add_node("load_candidates", load_candidates)
g.add_node("rank_with_llm", rank_with_llm)
g.add_node("persist_result", persist_result)

g.set_entry_point("load_candidates")
g.add_edge("load_candidates", "rank_with_llm")
g.add_edge("rank_with_llm", "persist_result")
g.add_edge("persist_result", END)

app = g.compile()

# 6) Run inside Cursor (with your configured MCP tools + GPT‑5.2 client)
# final_state = app.invoke(GraphState(use_case="Predict churn drivers"), config={"tools": tools, "llm": gpt52})
```
