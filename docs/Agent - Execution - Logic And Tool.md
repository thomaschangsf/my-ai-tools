# 1 Context
- Use these 3 lenses to compare different agent execution frameworks
	1.  **Linearity vs. Branching:** Does the agent follow one path (ReAct) or explore multiple possibilities simultaneously?
	2. **Autonomy vs. Structure:** Does the agent decide its next move (Autonomous), or is the flow defined by a developer (Orchestrated)?
	3. **Verification:** Does the agent check its own work before moving to the next step?

|**Pattern**|**Linearity vs. Branching**|**Autonomy vs. Structure**|**Verification Style**|
|---|---|---|---|
|**ReAct**|**Linear:** One step at a time in a single chain.|**Autonomous:** Agent decides the next step based on the last observation.|**Reactive:** Verification happens naturally via the next "Observation."|
|**Plan-and-Execute**|**Linear Execution:** Steps are sequential, but the "Plan" is a pre-set list.|**Orchestrated:** A "Planner" sets the path; an "Executor" follows it.|**Checkpoint-based:** The "Re-planner" verifies progress after each step.|
|**Reflexion**|**Cyclic:** Loops back on itself to refine the same task.|**High Autonomy:** Agent critiques its own work and chooses a new approach.|**Self-Correction:** Explicit "Self-Criticism" phase before final output.|
|**Tree of Thoughts**|**Branching:** Explores multiple parallel paths/possibilities.|**Heuristic-Driven:** The system "scores" branches to decide which to keep.|**Comparative:** It verifies by comparing the success likelihood of multiple paths.|
|**CoVe**|**Parallel/Linear:** Generates verification questions for its own claims.|**Structured:** Follows a rigid "verify-then-finalize" workflow.|**Fact-check:** Explicitly cross-references its own statements against "truth" tools.|

### 1.1 How does SNR fit in
- Each of these execution framework creates both signal and noise

| **Framework**              | **Primary Signal Source**  | **Primary Noise Source**             | **Impact on Decision Quality**      |
| -------------------------- | -------------------------- | ------------------------------------ | ----------------------------------- |
| **ReAct**                  | External Grounding (Tools) | Tool-Response Bloat                  | High adaptability, low reliability. |
| **Plan-and-Execute**       | Roadmap Clarity            | "Brittle" Plans (Unforeseen changes) | High efficiency, low flexibility.   |
| **Reflexion**              | Evaluative Feedback        | Redundant Reasoning Loops            | High accuracy, high token cost.     |
| **ToT (Tree of Thoughts)** | Parallel Comparison        | "Branch" Clutter                     | High logic depth, high latency.     |


### 1.2 How This Relates to Agent Context Management, 
- Agent execution framework creates the bloat that [[Agent - Context Management - Memory]] 's techniques address

| **Pattern**         | **Role**                                         | **Impact on Context**                                    |
| ------------------- | ------------------------------------------------ | -------------------------------------------------------- |
| **ReAct**           | **Execution.** Defines _how_ the agent works.    | **Increases Noise.** Rapidly fills context with logs.    |
| **Memory Patterns** | **Maintenance.** Defines _what_ the agent keeps. | **Increases Signal.** Cleans up after the ReAct process. |

# 2 Logic Patterns

|**Pattern**|**Best For...**|**Context Impact**|**Complexity**|
|---|---|---|---|
|**ReAct**|Simple Tool Use|**High Bloat** (Lots of logs)|Low|
|**Plan-and-Execute**|Long-running tasks|**Moderate** (Focused steps)|Medium|
|**Reflexion**|Coding/Accuracy|**High** (Keeps "failures" in view)|High|
|**Tree of Thoughts**|Hard Math/Logic|**Extreme** (Multiple paths)|Very High|
|**CoVe**|Fact-checking|**Low** (Self-contained)|Medium|

## 2.1 ReAct: Reason and Act
- This is a architectural pattern than mitigates hallucination by gathering real world evidence
- The architecture follows a strictly repeating cycle of four stages:
	1. **Thought:** The agent writes down what it is currently thinking about the user's request and what it needs to do next.  
	2. **Action:** The agent selects a "Tool" to use (like a Google Search, a Database query, or a Calculator) and provides the input for that tool.  
	3. **Observation:** The system runs the tool and feeds the raw results back into the agent's context window.
	4. **Repeat:** The agent looks at the Observation and starts a new **Thought** process based on that new information.
### The Pros: Why we use it
- **High Transparency & Explainability:** Because the agent "narrates" its inner monologue, you can see exactly why it chose a certain tool. This makes debugging significantly easier than "black-box" agents. 
- **Reduced Hallucinations:** By forcing a **"Thought"** phase before an **"Action,"** the agent is less likely to guess. It "checks its work" by observing real data from tools (like a search engine or database) rather than relying solely on its internal training data.
- **Real-Time Adaptability:** Unlike rigid scripts, a ReAct agent can pivot. If a tool returns an error or unexpected data, the "Observation" phase allows the agent to think of a new plan on the fly.
- **Ease of Implementation:** It’s a single-agent loop. You don't need a complex multi-agent "orchestra" to get started; you just need a solid system prompt.

### 2. The Cons: Where it fails (The "Dilution" Problem)
- **The "Context Bloat" (Token Cost):** Every loop appends more text. If an agent takes 10 steps to solve a problem, the context window is stuffed with 10 sets of thoughts, 10 tool commands, and 10 (potentially massive) tool outputs. You pay for all those tokens every single time the agent "thinks." 
- **"Lost in the Middle" (Attention Dilution):** As the loop grows, the agent’s original instructions (Primacy) and the most recent findings (Recency) stay sharp, but the crucial evidence it found in Step 3 or 4 gets buried in the "middle," leading the agent to repeat itself or forget key details.
- **Error Propagation:** If a tool provides a "noisy" or incorrect observation, the agent’s next "Thought" will be based on that bad data. Without a separate "Critic" (like in the **Reflexion** pattern), the agent can spiral into a "loop of death" trying to fix an error it doesn't understand.
- **High Latency:** Because it is a sequential, "stop-and-think" loop, it can feel slow. The agent cannot act until it has finished its "Thought," and it cannot think until it has finished its "Observation."
## 2.2 Plan-and-Execute**
Instead of "thinking and acting" one step at a time, the agent creates a full multi-step roadmap first, then executes it piece by piece.
- **How it works:** 1. **Planner:** Generates a list of 5 steps.
    2. **Executor:** Performs Step 1, then Step 2, etc.
    3. **Re-planner:** After each step, it looks at the result and adjusts the remaining 4 steps.
- **Pros:** Much more stable; avoids the "loop of death" where ReAct gets stuck repeating a failed action.
- **Cons:** Less "spontaneous"; if the initial plan is fundamentally flawed, it can be slow to pivot.
    
### **B. Reflexion (Self-Correction)**
This adds a "Critic" loop to the logic. The agent attempts a task, evaluates its own performance, and then tries again with "lessons learned."
- **How it works:** **Action $\rightarrow$ Evaluation $\rightarrow$ Reflection $\rightarrow$ Re-Action.**
- **Pros:** Excellent for coding or creative writing where the first draft is rarely perfect.
- **Cons:** Significantly higher token cost (you're paying for the agent to fail and try again).
### **C. Tree of Thoughts (ToT)**
The agent explores multiple reasoning paths at once, like a chess engine looking 3 moves ahead.
- **How it works:** It generates three different "Thoughts" for the next step, evaluates which one is most likely to succeed, and "branches" out from the winner while discarding the losers.
- **Pros:** Solves extremely complex logic problems that require "look-ahead" capability.
- **Cons:** Very high latency; the user has to wait for multiple "branches" to be simulated.
### **D. Chain-of-Verification (CoVe)**
The agent focuses on fact-checking its own logic before outputting a final answer.
- **How it works:** 
	1. Generate baseline response.
    2. Generate "verification questions" to test the facts in that response.
    3. Answer those questions independently.
    4. Produce a final, verified response.
    
- **Pros:** Dramatically reduces hallucinations.
- **Cons:** Adds "thinking time" to every interaction.


# 3 LangGraph - How Does Langgraph fit in?
- IMOW: LangGraph is the state machine framework one can use to build these 5 patterns.

- LangGraph is the **Orchestration Layer** that brings these together.
	- It is a **State Machine** (Nodes + Edges).  
	- It solves dilution by allowing you to **prune the State** at every node, ensuring only "High Signal" data moves forward.    
	- It can be used to build any of the patterns above (e.g., a **ReAct** loop or a **Tree of Thoughts** branch).
	    


### 3.1. LangGraph vs. Tree of Thoughts: The Axis View
To see where LangGraph sits compared to the logic patterns, let's look at it through your 3 lenses:

| **Feature**      | **Tree of Thoughts (The Pattern)**                                         | **LangGraph (The Framework)**                                                             |
| ---------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Linearity**    | **Branching:** Specifically designed to explore multiple paths at once.    | **Flexible:** Can be Linear, Branching, or Cyclic (loops).                                |
| **Autonomy**     | **Heuristic-Driven:** The "Scorer" tells the agent which path is best.     | **Orchestrated:** You (the developer) define the possible paths and "gates."              |
| **Verification** | **Comparative:** Verifies by checking which "branch" looks most promising. | **Infrastructure:** Provides the "Checkpoints" and "State" to make verification possible. |

### 3.2 LangGraph vs Context Dilution
LangGraph was specifically built to solve the **Context Dilution** issues we've been discussing. Because it uses a **State Object**, it doesn't just pass a giant string of text from one step to the next.
- **State Control:** You can tell LangGraph: "When moving from the Search Node to the Writer Node, _only_ pass the search results, and delete the intermediate reasoning."    
- **Checkpoints:** It "saves" the state at every node. If the agent gets lost in the middle, you can programmatically "reset" it to a previous, clean state.
- **Persistence:** It handles long-term memory out of the box, allowing you to move old conversation slots into a separate database (the "Retrieval" bucket) without clogging the current prompt.

#### 3.2.1 How to implement Context Management patterns
Here is how you would map each pattern into a LangGraph architecture using **Nodes**, **State**, and **Persistence**.

##### 3.2.1.1 ** Temporal Compression (The "Summarizer" Node)**
In LangGraph, you don't just append messages forever. You create a conditional edge that checks your token count.
- **The Node:** Create a `summarize_history` node.
- **The Logic:** If `len(state['messages']) > threshold`, this node calls the LLM to "summarize the above into 3 bullet points," updates a `state['summary']` field, and **deletes** the oldest messages from the `messages` list.
- **Benefit:** Your "middle" is constantly being squashed into a high-signal summary, keeping the context window lean.
    
##### 3.2.1.2 Managerial Pattern (The "State" Object)**
LangGraph's `State` is the "Manager." Instead of a single string, your State is a **Schema** (a TypedDict) that separates different types of memory.
- **The Logic:** You can define a state like:    
    ```python
    class AgentState(TypedDict):
        messages: List[BaseMessage] # Short-term
        summary: str               # Mid-term (Temporal)
        user_profile: dict         # Long-term (Managerial)
        current_plan: List[str]    # Operational
    ```
- **Benefit:** By isolating these fields, you can pass _only_ the `user_profile` and `summary` to the LLM, leaving out 50 messages of "noise."

##### 3.2.1.3 Structural Graph (The "Traversal" Edge)**
You can implement a Knowledge Graph by using a specialized node that interacts with a graph database (like Neo4j).
- **The Node:** A `graph_retrieval` node.
- **The Logic:** When a user asks about a complex relationship, the node queries the graph, finds the "nodes and edges" (e.g., _Project X -> managed by -> Sarah_), and injects that structured fact into the state.
- **Benefit:** It bypasses the "diluted" chat history by pulling facts directly from a logical map.
   
##### 3.2.1.4 *D. RAG Pattern (The "Retriever" Node)**
This is the most common LangGraph pattern.
- **The Node:** A `retrieve_documents` node.
- **The Logic:** Before the agent speaks, this node takes the user's query, searches a Vector DB, and adds the top 3 snippets to the `state['context']`.
- **Benefit:** It keeps the "Hard Drive" data out of the prompt until the exact moment it's needed.    


#### 3.2.2 The Secret Sauce: Persistence & Checkpoints
This is what makes LangGraph "Industrial Grade."
In addition to the logic above, LangGraph uses **Checkpointers** (like SQLite, MongoDB, or Postgres).
- **How it works:** Every time the graph moves from one node to another (e.g., from _Summarize_ to _Act_), LangGraph saves a **Snapshot** of the entire state.
- **Thread IDs:** By using a `thread_id`, you can resume a conversation days later. The agent doesn't have to "re-process" the whole history; it just loads the last saved `State` (which already includes your summary, your graph facts, and your RAG context).

#### 3.2.3  LangGraph Implementation of Context Management

| **Pattern**     | **LangGraph Component** | **How it saves your Context**                                    |
| --------------- | ----------------------- | ---------------------------------------------------------------- |
| **Temporal**    | **Summarizer Node**     | Actively prunes the `messages` list.                             |
| **Managerial**  | **State Schema**        | Separates "Metadata" from "Small Talk."                          |
| **Structural**  | **Graph Tool Node**     | Pulls logical facts instead of text snippets.                    |
| **RAG**         | **Retriever Node**      | Injects only relevant external data.                             |
| **Persistence** | **Checkpointer**        | Saves the "lean" state so you never have to re-read the "bloat." |

---

**Would you like to see a Python code snippet of a "Summarizer Node" that automatically triggers when your conversation gets too long?**