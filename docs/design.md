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

## Idea Generation Flow

> Some Nodes that would be required

input: The user sends in a question that will be used as the root to generate ideas

1. query -> search query (generate 2 search queries, that must proceed through the flow in parallel)
2. web search (tavily)
3. result summarization
4. Research Idea generation (this is the output that will be passed to next flow, once num_iters expires. It will be later used to perform RAG over a database of ArXiV papers of titles + abstracts)
5. Validation - Acts as a critic to the genreated research idea (loops back to node 1)

## RAG Flow

input: The generated and validated research idea from the Idea Generation Flow

1. Our embedded database of papers is stored in a qdrant database that can be accessed at http://localhost:6333
2. There exists a function to perform embedding using Nebius in the (../utils/call_llm.py) file that can be used to embed our query.
3. Perform a retrieval using qdrant, adopting the max-sim method of comparison to get the top_k results
4. We need to rerank the results and reduce their number to top_n after reranking
5. We need to assign a novelty score of our idea against each of the top_n result, which could be considered as the inverse of the similarity.
6. Aggregate the novelty scores across all results to get the final novelty score of the generated idea against retrieved and reranked research works
7. Ensure we use well designed pydantic schema and state in a manner similar to the previous flow.

## Planning Flow

input: The validated research Idea, the novelty assessment and top_n retrieved papers

1. We need to take human input in terms of timeline, type of project (academic paper, general research, presentation, educational-deepdive,etc)
2. We need to critically view the provided research idea, the novelty assessment and top_n retrieved papers and the user inputs to come up with a plan
3. We can accept user feedback to modify or tailor the plan, up to max_times.
4. The final plan can be printed to the STDOUT as well as being saved to a markdown document with beautiful formatting and vibrant icons, employing a clear and not needlessly verbose style of language.
