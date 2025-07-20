# Project Design

This app is meant to be an AI assistant that can take a user question and
convert it into a research plan. The intermediate steps between the question
to the plan can include things like

> [!IMPORTANT]
> Notes for AI
>
> This is my high-level plan, but I think we should approach this piece by piece
> and create functionality sequentially.
>
> This is my high-level plan, but I think we should approach this piece by piece
> and create functionality sequentially.
>
> The following sections will each contain one chunk of functionality, so use
> them to understand my requirements, and keeping in line with pocketflow's
> design guidelines, come up with a simple, yet powerful and clean solution
>
> Never complete more than one section at a time, and always add your notes as
> a subsection under each section that you are editing.

## Idea Generation Node

> Some Nodes that would be required

input: The user sends in a question that will be used as the root to generate ideas

1. query -> search query (generate 2 search queries, that must proceed through the flow in parallel)
2. web search (tavily)
3. result summarization
4. Research Idea generation (this is the output that will be passed to next flow, once num_iters expires. It will be later used to perform RAG over a database of ArXiV papers of titles + abstracts)
5. Validation - Acts as a critic to the genreated research idea (loops back to node 1)

## RAG Flow

## Novelty Flow

## Planning Flow
