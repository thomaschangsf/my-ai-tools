# 1 Pattern to Organize Techniques

- IMOW: These techniques improves the signal to noise ratio, making our instructions easier for the agent to align to.

- We generally categorize these into two dimensions: ==**Granularity** (how detailed the memory is)== and ==**Mechanism** (how the data is retrieved).==

---

## 1.1 The "Memory Hierarchy" Framework

Dilution is a mathematical function of the signal-to-noise ratio.
-  The following methods work on how to decrease noise and increase signal

Think of these strategies like the human brain or a computer’s storage layers. The pattern moves from **immediate focus** to **deep storage**.

### 1. The "Temporal Compression" Layer (Summarization with Time) (Granularity) (Temporal)
- This is also referred to as ==recursive context management==
- **The Pattern:** Reducing resolution to save space.   
- **Analogy:** Taking notes during a lecture instead of recording the whole audio.
- **Logic:** As the conversation grows, you trade detail for "gist." It prevents the model from getting lost in the weeds of old dialogue.
- Summarize reduce dilution because we, hopefully, are keeping the key info, and reducing the irrelevant info, ie noise. 
- Examples
	- ==Recursive summarization==: Once a conversation hits a certain token limit, a "Summarizer" agent takes the oldest 20% of the chat, turns it into a bulleted summary, and replaces those 20% with that single summary block.
	- We apply different level of summary for different time slots

| **Time Slot**                      | **Resolution**          | **Storage Format**         | **Why?**                                                               |
| ---------------------------------- | ----------------------- | -------------------------- | ---------------------------------------------------------------------- |
| **The "Now"** (Last 5-10 turns)    | **High (Raw)**          | Full Transcript            | To maintain the "vibe," tone, and immediate context.                   |
| **The "Recent"** (10-30 turns ago) | **Medium (Summarized)** | Bulleted "State of Play"   | To remember what was decided without the back-and-forth.               |
| **The "Past"** (30+ turns ago)     | **Low (Extracted)**     | Key-Value Pairs / Entities | To remember _facts_ (e.g., "User's name is Alex") but forget the chat. |

### 2. The "Library" Layer (Vector RAG) (Retrieval Mechanism)
- **The Pattern:** On-demand retrieval based on relevance. 
- **Analogy:** A library where you only pull the book you need when a specific question arises.
- **Logic:** Instead of keeping everything in "active thought" (context window), you store it in "long-term storage" (database) and only bring it back when it's semantically relevant.   

### 3. The "Structural" Layer (Graph-Based)
- **The Pattern:** Organizing by relationship, not by time.
- **Analogy:** A mind map. increase the SNR by increasing the information density.
- **Logic:** It solves dilution by linking ideas together. If you mention "Project X" at the beginning and again at the end, a Graph architecture links those two points directly, bypassing the "middle" where the dilution usually happens.
- This is both granularity (SNR) and structural
	- Granularity: allows agents to store atomic facts; instead of remebering 500 words, we remember key info/tntoplogy, why they are on web site.
	- It is Retreival because we are fetching atomic facts via node traversal.dd
    
### 4. The "Managerial" Layer (Hierarchical) (Aka Multi-Agent System)
- **The Pattern:** Distributing the cognitive load.
- **Analogy:** A CEO who knows the big picture delegating specific tasks to specialized employees.
- **Logic:** By limiting the "Worker" agent's context to _only_ what is needed for the current task, you mathematically eliminate the possibility of dilution because the context window is never full enough to get "muddy."
- Example: ==Router framework==; the router agent maps the user's intent to an agent
    
- Side: MemGPT combines mulyiple axises

| **Bucket**      | **MemGPT's Role**                                                              |
| --------------- | ------------------------------------------------------------------------------ |
| **Managerial**  | **Primary.** The agent acts as its own memory manager using tool calls.        |
| **Temporal**    | **Secondary.** It manages the flow of time by "paging" old events to disk.     |
| **Structural**  | **Optional.** It can use a graph to organize the "archived" data it retrieves. |
| **Compression** | **Utility.** It uses recursive summarization to shrink data before archiving.  |

---

## Summary Table: Which Pattern to Use?

| **Strategy**      | **Pattern Category** | **Solves Dilution By...**                          |
| ----------------- | -------------------- | -------------------------------------------------- |
| **Summarization** | **Temporal**         | Shrinking the past.                                |
| **Vector RAG**    | **Associative**      | Fetching only what's "like" the current topic.     |
| **Graph-Based**   | **Relational**       | Connecting dots regardless of when they were said. |
| **Hierarchical**  | **Operational**      | Keeping the "workspace" small and clean.           |



# 3 Summary

The fundamental philosophy is that memory management is not just about data storage; it is about solving **Context Dilution** by improving the **Signal-to-Noise Ratio (SNR)**. While agent execution frameworks (like ReAct) inherently increase "noise" by filling the context window with logs and reasoning steps, memory patterns are designed to increase the "signal" by cleaning up that process.

### 1. The "Memory Hierarchy" Framework

We organize memory techniques across two main dimensions: **Granularity** (how detailed the memory is) and **Mechanism** (how the data is retrieved). This creates a four-layer framework:

- **Temporal Compression (Summarization with Time):** This layer shrinks the past to save space by trading detail for the "gist". It manages context resolution based on time:
    
    - **The "Now" (Last 5-10 turns):** Kept at high resolution (raw transcript) to maintain immediate context and tone.
        
    - **The "Recent" (10-30 turns ago):** Kept at medium resolution (bulleted summaries) to remember decisions without the back-and-forth noise.
        
    - **The "Past" (30+ turns ago):** Kept at low resolution (extracted key-value pairs) to remember atomic facts but forget the chat history entirely.
        
- **The "Library" Layer (Vector RAG):** This is an associative retrieval mechanism. Instead of keeping data in "active thought," it stores it in a database and fetches it only when semantically relevant to the current prompt.
    
- **The "Structural" Layer (Graph-Based):** This organizes memory by relationship rather than time, acting like a mind map. It increases information density by linking atomic facts (e.g., "Project X -> managed by -> Sarah") so the agent can bypass the diluted "middle" of a conversation.
    
- **The "Managerial" Layer (Hierarchical):** This is an operational pattern that distributes cognitive load. By using a multi-agent or router system, you limit a specific "Worker" agent's context to only what is needed for its current task, mathematically preventing the context window from getting muddy.
    

### 2. Implementation Infrastructure (LangGraph)

To actually build these memory layers, we discussed using LangGraph as the state machine and orchestration layer.

- **State Objects (TypedDict):** LangGraph's State acts as the "Manager" by separating different types of memory (e.g., short-term messages vs. long-term user profiles) so you only pass the high-signal fields to the LLM.
    
- **Summarizer Nodes:** You can program conditional edges to actively monitor token counts and trigger a summarization node to squash the "middle" of a conversation into a high-signal summary.
    
- **Checkpoints and Persistence:** By using Checkpointers (like SQLite or Postgres) and thread IDs, the system saves snapshots of the "lean" state at every node. This allows the agent to pause for human verification or resume days later without needing to re-read bloated chat logs.
    