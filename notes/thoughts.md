# AI powered R&D - Notes on System Design & Other General Thoughts

> I'm penning down my thoughts as I think them through. As such, treat this document as a work-in-progress.

I believe that scoping this project out requires a good understanding of Retrieval Augmented Generation.
Wile RAG ain't nothing new, Since it sits at the forefront of the AI hype train, the signal-to-noise ratio around RAG is poor.
Here's my thoughts on a few articles that cover these topics

## [What is Agentic RAG](https://weaviate.io/blog/what-is-agentic-rag, "What is Agentic RAG - Article By Weaviate")

### Vanilla RAG

> [Vanilla RAG](./media/vanilla_rag_flowchart.png, "Vanilla RAG Flowchart")

- Naive RAG considers only one external knowledge source.
- One shot retrieval (based on embedded query against embedded+chunked documents) to provide context to LLM to generate a response
- You could implement re-ranking post retrieval, but once results are finalized, then iteration over the results to ensure goodness-of-fit is tedious.
- Process flow of Vanilla RAG
  - Documents chunked and vectorized using an embedding model, then stored in a vector DB
  - In-coming user queries are embedded with same embedding model, then compared against vectorized documents to get top_k similar
  - Retrieved documents are collected (potentially reranked) and provided to the LLM along with the query as context
  - LLM generates a response that factors in the query along with the context containing the retrieved documents

### Agents in AI

- In a nutshell, agents are LLMs with a role (that have access to memory and external tools).
- Reasoning ability of LLMs allow it to plan and act to complete tasks
- Some notable components of agents are
  - LLM (with defined role & task)
  - Memory (short-term & long-term)
  - Planning (eg. reflection, self-critics, query routing etc)
  - Tools (eg. web-search, bash-command-execution etc)
- The ReAct (Reason + Act) Framework is used to demonstrate how Agents behave
  - [ReAct Framework](./media/react_framework_flowchart.png, "ReAct = Reason + Act (With LLMs)")
  - Thought: Receive user query to then being reasoning about a plan for the next action
  - Action: Agent decides an action and executes it.
  - Observation: The Agent observes feedback from the action.
  - Repeat until task is completed.
