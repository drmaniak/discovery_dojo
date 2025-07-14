# 🧠 Modular Research Ideation Assistant with PocketFlow

## 📋 Overview of the System

We propose an AI assistant that helps researchers brainstorm and evaluate new ideas using PocketFlow – a minimalist LLM orchestration framework ([the-pocket.github.io](https://the-pocket.github.io)). The system takes a freeform problem description as input and outputs:

1. Several plausible research ideas or directions
2. A brief novelty assessment for each idea based on a light literature scan
3. One or more suggested validation experiments per idea

All components are implemented as a graph of modular nodes in PocketFlow for clarity and debuggability. This design emphasizes clean code (minimal "glue" logic) and transparency over complex frameworks, aligning with PocketFlow's ethos of "100-line" simplicity (zero bloat, no heavy dependencies). We favor OpenAI's GPT models for language tasks, while using lightweight tools/APIs for retrieval. The entire system is scoped to ~15 hours of engineering effort, ensuring it's more robust than a quick 6-hour hack while avoiding over-engineered complexity.

## 🔄 Key Steps (Nodes) in the Workflow:

1. **Problem Ingestion** – Accept the user's freeform problem description.
2. **Idea Generation** – Use an LLM to propose multiple research ideas addressing the problem.
3. **Literature Retrieval (Novelty Scan)** – Use an external API (e.g. Semantic Scholar or ArXiv) to fetch related paper abstracts for each idea.
4. **Novelty Assessment** – Have an LLM compare each idea to retrieved abstracts to judge how novel the idea is.
5. **Experiment Planning** – Use an LLM to suggest validation experiments (setup, metrics, datasets) for each idea.
6. **Output Formatting** – Aggregate the results into a coherent, readable report.

Each of these stages is implemented as one or more PocketFlow nodes (encapsulating either an LLM prompt or a tool invocation) connected in a directed graph (the flow). The PocketFlow shared memory is used to pass data (problem description, ideas, retrieved texts, etc.) between nodes. This modular design makes it easy to test or modify each part independently (for example, debugging the idea generation prompt without running the whole pipeline). Below we detail the nodes, including suggested LLM models, tool choices, and prompt scaffolds for each stage. We also provide a pseudocode sketch of the PocketFlow graph connecting these components.

## 💡 Node 1: Idea Generation (LLM)

**Function**: Generate several possible research ideas or directions to address the given problem. The node will likely return 3–5 succinct ideas. We use an OpenAI GPT-4 model (via API) for its strong creativity and reasoning, though GPT-3.5 could be used to reduce cost with some quality trade-off.

**Prompt Design**: The prompt should clearly restate the problem and ask for a list of novel research ideas. For example:

```
System: You are an AI research assistant skilled in creative brainstorming.
User: The problem is: "{user_problem_description}".
Generate **3 distinct research ideas** to tackle this problem.

- Each idea should be a one-sentence description of a possible approach or direction.
- Focus on plausible, innovative solutions, not incremental tweaks.
- Label them "Idea 1, Idea 2, ..."
```

This scaffold ensures the LLM knows its role and the expected format (a numbered list of ideas). The instructions emphasize distinct and innovative ideas to encourage diversity. We keep the output structured (one idea per line, labeled) for easy parsing in the next nodes.

**Output Example**: For input "Image models struggle with generating hands," the LLM might output:

1. Idea 1: Use a hand-specific augmentation pipeline to provide extra training data on hands for image generators.
2. Idea 2: Develop a hierarchical GAN where a sub-network specializes in rendering hands with correct anatomy.
3. Idea 3: Introduce a fine-grained finger pose loss function to penalize anatomical errors in generated hands.

This node's implementation in PocketFlow would likely subclass Node (or use the provided LLM Wrapper utility). For instance, a GenerateIdeasNode could call the OpenAI API with the above prompt and return the list of ideas. We emphasize logging the raw LLM output for debugging. Since PocketFlow encourages "agentic coding" and minimal abstractions, we can directly call the OpenAI SDK inside the node, avoiding extra layers that could obscure errors (aligning with low tech-debt).

## 🔍 Node 2: Literature Retrieval for Novelty (Tool)

**Function**: For each generated idea, retrieve a few relevant references (titles/abstracts of papers) to inform novelty assessment. Rather than relying on the LLM's internal knowledge (which could be outdated or hallucinated), we use a tool-based approach: query an academic search API. This keeps our system up-to-date and fact-based.

**Tool Choice**: We favor lightweight, publicly available APIs that return paper metadata (title, abstract) without requiring full-text parsing. Two good options are:

1. **Semantic Scholar API**: Allows keyword searches and returns JSON with paper titles, abstracts, years, etc. Semantic Scholar's AI-driven search is robust across many fields, which is useful if the user's problem is in any scientific domain. We can use the free tier (requires an API key, but straightforward to integrate via Python requests).

2. **ArXiv API**: Useful especially for CS/AI problems. We can query ArXiv's database by keywords; the API returns a feed of matching papers with titles and abstracts. No key needed, and parsing can be done via an Atom feed or using existing Python libraries (like arxiv package). ArXiv is comprehensive for many STEM fields, though it may miss non-arXiv papers.

Given the 12–20h implementation budget, using one of these is sufficient. We might start with the Semantic Scholar title/abstract search endpoint, as it's simple: e.g. GET /v1/paper/search?query={idea_description}&fields=title,abstract,url. This returns a list of top papers. We can then take the top 3 results for analysis.

**Query Formation**: The simplest approach is to use the idea description itself as the query. For example, if Idea 1 is "hand-specific augmentation pipeline for image generators," the query could be a direct string of that. Optionally, we can enhance the query by extracting keywords (e.g. "data augmentation hands image generation") – this can be done by a quick heuristic or even asking the LLM to produce a search query (an extra node, but might be overkill). For a first iteration, direct query is acceptable, acknowledging it might miss papers if wording is unusual. In an enhancement, synonym expansion or multiple queries (keywords plus method names) could increase recall.

**Output**: This node will output a short list of references per idea. Each reference can be just a title + year + maybe a very short abstract snippet. We intentionally keep only a "metadata-level" snippet – enough to judge similarity, without diving into full papers (which would be too slow and unnecessary for a quick novelty check). For example, for the augmentation idea, the top 2 results might be:

- Ref A: "Data Augmentation Strategies for Improving Hand Generation in GANs" – 2023 (Abstract: proposes adding hand pose augmentation to training data…)
- Ref B: "Enhancing GANs for Hands via Anatomy-Aware Data Augmentation" – 2021 (Abstract: uses synthetic hand datasets to improve generation…)

If the search finds nothing highly relevant (e.g., truly novel idea), it might still return some loosely related papers (perhaps on image generation quality or on hands in computer vision). That in itself is a signal of novelty if no direct matches appear.

This retrieval node can be implemented as a PocketFlow Node that calls the API. If multiple ideas are generated, we can handle this in two ways:

- **Sequential loop**: Iterate ideas in Python, calling the retrieval node for each. This might be simplest for implementation (one can use a for-loop outside the PocketFlow graph, or have the node itself handle a list).
- **Batch/Parallel nodes**: PocketFlow supports batch processing via BatchNode and even parallel flows. We could use a BatchNode that takes the list of ideas and performs retrieval in parallel or sequentially inside the graph. For clarity, a sequential approach is fine (3 ideas won't be too slow even if done one by one, and it's easier to debug).

**Debuggability**: We will log each API query and result count. Because this is an external call, it can fail or return empty – by isolating it in one node, we can easily mock or stub it during testing (e.g. use a saved response). If the API fails or rate-limits, we might have the node output an empty list or a special token that signals "no data," and handle it gracefully in the novelty analysis node (perhaps treating missing data as a case where the idea could be novel, but noting the uncertainty).

## 🔬 Node 3: Novelty Assessment (LLM)

**Function**: Analyze the idea against the retrieved literature to estimate its novelty. Essentially, this node answers: "Has this idea been done before, or how is it different from what's out there?" It produces a short text rationale for each idea's novelty, possibly with a verdict like "novel" vs "not novel" or on a rough scale.

**Why LLM**: This task requires understanding nuanced similarities. While one could use an automated similarity score (e.g. embedding cosine similarity between the idea and paper abstracts), that alone doesn't provide an explanation and might be brittle across domains. Using an LLM allows a concise comparative analysis in natural language, closer to how an expert would reason about novelty. In fact, current research on "AI scientists" often uses LLMs with retrieved papers to judge novelty, albeit with special prompts and care to avoid inconsistencies. We'll leverage this approach in a simpler form.

**Prompt Design**: We prompt the LLM with the idea and the retrieved references. For instance:

```
System: You are a research assistant helping to assess novelty of ideas using literature.
User:
Idea: "{idea_description}"
Relevant Papers:

1. {Title 1 (Year)} – {brief abstract or key point}
2. {Title 2 (Year)} – {brief abstract or key point}
3. {Title 3 (Year)} – {brief abstract or key point}

Determine if the idea is novel. Explain why it is novel or not, referring to the papers if needed.

- If similar work exists, describe how those papers overlap with the idea.
- If the idea seems new or significantly different, point that out.
```

We include 2–3 of the most relevant papers from Node 2. The "Relevant Papers" section in the prompt gives the LLM factual grounding, which mitigates hallucination and anchors the assessment in real literature. We ask for an explanation rather than just a label, to get a nuanced answer (and to be more useful to the user).

**Expected Output**: A few sentences explaining novelty. For example:

> **Novelty Analysis**: This idea appears moderately novel. Prior work like "Data Augmentation Strategies for Improving Hand Generation in GANs" (2023) has already explored augmenting training data with hand images. That approach is quite similar in aiming to improve hand realism via more data. However, our idea specifically suggests a dedicated pipeline for hand augmentation, which might be a new twist. No paper was found that uses a separate sub-network just for hands, so that part seems novel. Overall, the idea overlaps with existing augmentation strategies but combines them in a potentially unique way.

The assessment above cites an example reference (if integrated into final output, we could even include a citation link). The LLM identified overlap with one paper but also highlighted what aspect is unique. This is the kind of insight we want. If an idea were entirely novel (no similar papers), the LLM might say so and note the lack of related literature. If an idea is clearly already done, it would explain that too ("This idea is not very novel, as Smith et al. 2022 and Lee 2021 have effectively the same proposal.").

**Model Choice**: GPT-4 is preferred here as well for its better comprehension of technical text. But GPT-3.5 might suffice if abstracts are short and the prompt is focused. We should also be cautious to keep the prompt length reasonable – feeding in many long abstracts can hit context limits and confuse the LLM. That's why we limit to a handful of papers and possibly truncated abstracts (just the most relevant sentences). This aligns with the "lightweight scan, not full document parsing" constraint – we are giving just enough info for a decision.

**PocketFlow Implementation**: Similar to Node 1, this can be an LLMNode that reads from shared memory the current idea and its retrieved papers, and returns a text or structured result. PocketFlow's graph can loop this node for each idea or use a batch approach. A neat approach is to combine retrieval and assessment in a sub-flow: for each idea, call retrieval then assessment. PocketFlow can support sub-flows or we can simply sequence these nodes and use a "fan-out" for multiple ideas. For clarity, pseudocode will be provided soon.

**Debugging Considerations**: We will test this node with known scenarios to ensure it behaves. One potential pitfall is if the LLM output is inconsistent (due to phrasing differences or if references are too many). As an optional enhancement, we could enforce a more structured output (e.g., always end with a "[Novelty: High/Medium/Low]" label for programmatic use). However, to keep code simple, we may rely on just parsing keywords in the explanation if needed. The main output is textual, which is fine for the user.

Additionally, we note that using an LLM as a judge has some reliability issues if prompts are not consistent. Our approach mitigates this by providing concrete references and asking for a comparison (reducing subjective guesswork). In the future, we could incorporate few-shot examples of novelty judgments to calibrate the LLM (as done by recent research), but this might be beyond our 20h scope. We'll document this as a future improvement.

## 🧪 Node 4: Experiment Planning (LLM)

**Function**: For each idea, propose one or more experiments to validate or explore the idea. This includes suggesting an experimental setup, metrics to measure success, and relevant datasets or benchmarks if appropriate. Essentially, it turns an idea into a testable hypothesis.

**Prompt Design**: We use another LLM prompt that takes an idea (and optionally the novelty info) and asks for experiment suggestions. The prompt could be:

```
System: You are an expert in designing scientific experiments.
User: We have a research idea: "{idea_description}".
Describe one or two **experiments** to test this idea. For each experiment, include:

- the experiment setup (what is being done),
- the metric or criteria to evaluate success,
- and mention any dataset or tool that could be used.
  Be concise and specific.
```

We do not necessarily include the novelty analysis in this prompt – the experiment planning can be done on the idea alone. (However, if the idea was found to be not novel, one might design experiments referencing prior work's setup; but to keep it simple, we treat each idea independently here. Optionally, we could instruct the LLM like "Given the idea and that similar work exists, suggest an experiment highlighting what's new in this idea," but that complexity can be skipped initially).

**Expected Output**: A short description of 1-2 experiments. For example, for the hand augmentation idea:

> **Experiment Suggestion**:
>
> **Experiment 1**: Train two image generation models – one with the new hand-specific augmentation pipeline and one without it – on a standard face/image dataset that often fails on hands (e.g. CelebA or a hands dataset). Compare the models on hand realism metrics, such as Frechet Inception Distance focused on hand regions, or human evaluation specifically rating the quality of generated hands.
>
> **Experiment 2** (optional): Conduct an ablation study where you vary the amount of augmented hand data added. Evaluate whether more hand-focused data correlates with better generated hand quality (using a hand pose accuracy metric or classification of hand vs non-hand artifacts).

This output gives a concrete way to validate the idea: a comparative setup, evaluation metrics (FID, human eval, pose accuracy), and even points to a dataset (CelebA, which has faces but known issues with hands, or a dedicated hands dataset if available). It's specific enough to guide an early-stage researcher on next steps. We'd aim for a similar level of detail for each idea.

**LLM Model**: Again GPT-4 is ideal for depth, but GPT-3.5 could be used here too. The prompt is straightforward and doesn't require external info (all knowledge about common metrics/datasets is in the model).

If needed, we can inject some hints in the prompt if the domain requires it. For instance, if the problem domain is known (like "an NLP problem"), we might tell the LLM to think of relevant benchmarks (GLUE, etc.). But a capable model will often infer context (e.g., if the idea mentions "image generation," it will know about image datasets and metrics like FID or human eval).

**PocketFlow Integration**: This is another LLM node that takes each idea (and possibly we pass along the novelty result just for context or to include in final output). We can chain this after the Novelty node. Each idea flows through: Idea -> (Retrieve->Assess novelty) -> Experiment plan. Or we might do novelty for all ideas then experiments for all – either way works. For simplicity, doing it idea-by-idea in sequence might be easier to implement: the shared store can carry a structure like results = []. For each idea, we retrieve papers, assess novelty, plan experiment, then append {idea, novelty_analysis, experiment_plan} to results. This loop could be coded imperatively around the PocketFlow nodes, or as part of the flow with a batch mechanism. The pseudocode below will illustrate a logical sequence.

**Debugging**: This node's output might sometimes be too brief or too general (LLMs sometimes give high-level answers). If so, we can refine the prompt by adding an example or by explicitly asking for specifics ("name a dataset if possible", etc.). We prefer to handle this via prompt tweaks rather than adding complex post-processing. It's also easy to test this node independently by feeding in a sample idea and seeing what it gives, adjusting the prompt until the format is satisfying.

## 📊 Node 5: Output Formatting and Aggregation

**Function**: Compile the ideas, novelty assessments, and experiment plans into a final structured report for the user. The output should be easy to read (likely in Markdown format, since the user's instructions emphasize clear formatting), with logical sections or lists for each idea.

**Approach**: Since we already have nicely formatted pieces (the idea as a sentence, novelty text, experiment text), we can either directly assemble them with a simple template, or use an LLM to polish the wording. Given our priority on low complexity, we will implement formatting in code (template strings), ensuring we follow the requested Markdown style (using headings, bullet points, etc.). This avoids an extra LLM call and guarantees no surprising rewording. However, we will ensure the final text flows well – possibly by writing a small function to format each idea section.

**Formatting Plan**: We can structure the output as follows:

```
Idea 1: Idea description
Novelty: … (the novelty analysis text) …
Proposed Experiments:

    Experiment 1 description…

    Experiment 2 description (if any)…

Idea 2: Idea description
Novelty: …
Proposed Experiments: …
```

And so on. We use bold subheadings for "Novelty" and "Proposed Experiments" to make it skimmable. Bullet points for experiments if multiple. If we have citations or references from the novelty scan, we might incorporate them here (e.g., citing the reference that was similar). For example, in the novelty text we might already include something like "(Smith 2023 showed a similar approach)…". We could format that as a reference or just mention it. Since the user's guidelines mentioned possibly including citations, we can include inline citations or links for the papers if available (e.g., link the Semantic Scholar or ArXiv page).

**Citation Enrichment** (optional): To add value, we could hyperlink the paper titles in the novelty section to their source (using the URL from the API). This way the user can follow up on related work. This doesn't add much code complexity (the retrieval node can store the URL for each reference). We'll ensure not to clutter the text excessively – perhaps link one key paper per idea that was mentioned.

**PocketFlow Implementation**: This final stage might be done in the "main" function after running the flow, because it's just formatting the collected results. Alternatively, one could have a custom Node that reads all results from shared storage and produces a markdown string. Either way, it's straightforward. For clarity, writing a small Python function to loop over results and format text might be easiest to implement and debug (you can print the final markdown to console or file and inspect it).

**Example Final Output Snippet**: Continuing the earlier example, the final answer to the user might look like:

## Idea 1: Hand-Specific Data Augmentation Pipeline for Image Generators

**Novelty:** This idea is partly explored in prior work. For instance, _"Data Augmentation Strategies for Improving Hand Generation in GANs" (2023)_ has a similar concept of adding hand-focused training data. Our idea's twist is to create a dedicated pipeline stage for hands, which isn't explicitly covered by existing papers. Thus, the idea isn't completely new, but it offers a novel combination of known strategies (augmentation + specialized pipeline).

**Proposed Experiments:**

- _Experiment 1:_ Train two GAN models – one with the hand-specific augmentation pipeline and one without – on a dataset like CelebA. Compare their performance on generating realistic hands, using metrics such as Hand-FID (FID computed on hand regions) or human evaluation for hand realism.
- _Experiment 2:_ Conduct an ablation by varying the quantity of augmented hand data. Verify if more hand data yields proportional improvement in generated hand quality, measured by a hand pose accuracy metric on the generated images.

(And similarly for Idea 2, Idea 3…)

This output uses Markdown headings for each idea, bold labels for sections, and clear, concise descriptions, fulfilling the user's formatting preferences. The key is the user can trust that the novelty statements are literature-grounded.

## 🔄 PocketFlow Graph Structure (Pseudocode)

Finally, here is a high-level pseudocode sketch of how these nodes connect in a PocketFlow graph. This illustrates the modular design and how data flows:

```python
from pocketflow import Node, Flow, BatchNode

# Define Node classes (simplified pseudocode)

class IdeaGenerator(Node):
    def run(self, inputs):
        problem = inputs["problem_description"]
        # Call OpenAI API with brainstorming prompt...
        ideas = openai_chat(prompt_for_ideas(problem))
        # Parse into a list of idea strings
        return {"ideas": parse_list(ideas)}

class LiteratureSearch(Node):
    def run(self, inputs):
        idea = inputs["idea"]
        # Query Semantic Scholar API for top results
        papers = semantic_scholar_search(query=idea, top_k=3)
        # Extract (title, year, abstract, url) for each paper
        return {"references": papers}

class NoveltyAnalyzer(Node):
    def run(self, inputs):
        idea = inputs["idea"]
        refs = inputs["references"]
        # Construct prompt with idea + refs
        prompt = make_novelty_prompt(idea, refs)
        analysis = openai_chat(prompt)
        return {"novelty_analysis": analysis}

class ExperimentPlanner(Node):
    def run(self, inputs):
        idea = inputs["idea"]
        prompt = make_experiment_prompt(idea)
        plan = openai_chat(prompt)
        return {"experiment_plan": plan}

# Construct flow
flow = Flow()

# Node instances
gen = IdeaGenerator()
search = LiteratureSearch()
assess = NoveltyAnalyzer()
plan = ExperimentPlanner()

# Connect nodes
flow.add(gen)  # start node
gen.connect(search, fan_out="ideas")  # fan out each idea into a search
search.connect(assess)  # for each idea, after search do assess
assess.connect(plan)  # then plan experiments

# After plan, aggregate results (could be inside plan node or separate)

# Execute flow
result = flow.run({"problem_description": user_input})
```

In this sketch, the IdeaGenerator produces a list of ideas. PocketFlow can fan-out the flow such that each idea is fed into the next nodes. The LiteratureSearch node runs for each idea (this could also be a BatchNode processing list input). Then each search result goes into NoveltyAnalyzer, and then into ExperimentPlanner. We collect the outputs (perhaps the ExperimentPlanner node or the Flow returns a list of results for each idea).

This graph approach ensures each piece is isolated and testable. For instance, LiteratureSearch can be unit-tested with a dummy idea to see if it returns expected dummy references. Similarly, we can swap out the OpenAI calls with mocks to test flow control. PocketFlow's minimalism (graph + shared store) means the data passing is explicit and easy to trace, aiding debugging.

Additionally, PocketFlow supports visualization and debugging tools that we can use to step through the graph if needed, though our flow is relatively straightforward.

## ✨ Optional Enhancements and Considerations

Finally, we consider some improvements and how we balanced LLM vs tool usage:

1. **Confidence Scoring**: We could assign confidence scores at various stages. For example, the NoveltyAnalyzer could output a confidence level (perhaps based on how many similar papers were found or the LLM's language – e.g., presence of uncertain words). We might implement a simple heuristic: if no references found, confidence in novelty is high; if many found, novelty confidence low. Alternatively, use the LLM to output an explicit "novelty: X%" (though that may be arbitrary). For experiment plans, confidence is less quantifiable, but we could rank ideas by the novelty to suggest which might be most worth pursuing. Since the user didn't explicitly request confidence metrics, this would be a bonus feature for internal use (e.g., maybe highlight the most novel idea).

2. **Reranking or Filtering Ideas**: If the LLM generates a lot of ideas, we might want to filter out those that are clearly not novel. For instance, if an idea gets a "not novel" assessment (lots of overlap with literature), the assistant could optionally omit it or at least flag it. We could then ask the IdeaGenerator to replace it with another idea (this would introduce an iterative loop: if idea not novel, maybe try a different one). However, given time constraints, our initial system will likely just report the novelty and leave it to the user to decide. As an enhancement, we could implement a "novelty threshold": e.g., generate 5 ideas, run novelty check, then automatically drop any that are "not novel" and present the rest (or mark them). PocketFlow could handle this with a decision node (if novelty == "not novel" go back and generate a new idea, etc.), similar to how the example agent flow makes decisions. This adds complexity but is feasible.

3. **Citation and Reference Enrichment**: As mentioned, linking actual papers in the output can greatly help the user. We have the data from the retrieval node, so we can easily provide the title and maybe a link (DOI or Semantic Scholar link) for key related works. This makes the report more informative and credible (since the user can verify the novelty claims by reading those abstracts or papers). We should be careful not to overload the user with too many citations – one or two per idea is usually enough. The PocketFlow node outputs can carry these references; our formatting function can integrate them. We already showed an example with one reference cited. In practice, we might list them at the end of the idea section, e.g., "(Related work: Smith et al 2023, Lee 2021)".

4. **User Feedback Loop**: To support iterative refinement, we could allow the user to give feedback after seeing the ideas. For example, the user might say "I like Idea 2, but can you expand more on it?" or "Any other ideas? Idea 3 seems too similar to known work." In a fully interactive system, we could incorporate this by making the flow callable multiple times or having a persistent agent. With PocketFlow, one could design a loop where after presenting ideas, the user's choice triggers a sub-flow (perhaps generating more details or alternate ideas). This is outside the one-shot query→answer flow, but we can mention how the modular design makes it easier to extend: e.g., we could add a node at the end that waits for user selection and then either re-runs the idea generation (skipping ones) or goes deeper on a chosen idea (maybe retrieving more papers or designing a project plan). Due to time scope, we won't implement it now, but the system is built in a way that each part can be invoked as needed for such loops.

5. **Balancing LLM vs Tool Reasoning**: We deliberately use LLMs for what they're best at (creative generation and synthesis of information) and tools for what they're best at (fetching factual data and searching). For example, we don't ask the LLM to scour its memory for related work, which could cause hallucinations or miss recent papers – instead we call an API to get real papers. Conversely, we don't try to hard-code logic for evaluating novelty (a complex semantic task) – we let the LLM read and reason with the text, which is more flexible than any static algorithm for this step. This balance ensures debuggability too: tool steps are transparent (we can log queries and results), and LLM steps are constrained with clear prompts and provided context, which reduces random outputs. Each node can be tested independently: e.g., we can verify the retrieval returns sensible papers, and we can try the novelty prompt on known examples to see if it correctly identifies novelty or not. By partitioning tasks this way, if the final output has an issue, we can pinpoint which node likely caused it (for instance, if an experiment suggestion is irrelevant, that's Node 4's prompt to fix; if a novelty claim is incorrect, maybe Node 2 missed a key paper or Node 3 misinterpreted it).

6. **Modularity and Low Technical Debt**: Because PocketFlow doesn't enforce a lot of boilerplate, our code remains simple functions corresponding to each logical step. This makes it easy to maintain. Should we need to swap out the LLM provider (say use Anthropic's Claude for idea generation if it gives more varied ideas, or a local model for privacy), we can do so by just changing the API call inside the node – no changes to the overall flow structure. Similarly, if a better academic API emerges, we can replace the Semantic Scholar query function without affecting other parts. PocketFlow's vendor-agnostic design encourages this flexibility.

## 🌟 Summary

In summary, the designed assistant uses PocketFlow to orchestrate a clear,
multi-step reasoning pipeline: from user problem to ideas, from ideas to
literature checks, and from ideas to experiments. Each component is chosen to
maximize clarity (both for the developer and the end-user). By leveraging
powerful LLMs alongside targeted retrieval, the system grounds its suggestions
in reality – a critical feature for research applications. At the same time, it
maintains a high-level of explainability (each idea comes with reasoning and
references). All of this is achieved with minimal complexity in code, aligning
with the goal of a debuggable, low-debt solution. The result is an AI assistant
that not only inspires new research directions but also provides context and
next steps, functioning as a valuable co-pilot in early-stage R&D
brainstorming.

**Sources**: The design draws on PocketFlow's documentation and examples for building LLM workflows, as well as recent research on automated idea generation and novelty checking which validates our approach of combining LLMs with literature search.
