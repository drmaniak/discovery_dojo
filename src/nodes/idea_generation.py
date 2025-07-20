from pocketflow import AsyncParallelBatchNode, BatchNode, Node

from domain.config import SearchQueriesResponse, SearchResult
from domain.shared_store import (
    check_completion_conditions,
    display_current_state,
    format_final_output,
    get_shared_store,
    get_user_validation_input,
    update_shared_store,
)
from utils import prompts
from utils.llm_utils import call_llm, call_llm_structured

# from utils.search_utils import search_web
from utils.tavily_search import search_web


class QueryGenerationNode(Node):
    """Generate N parameterized search queries from user question."""

    def prep(self, shared):
        """Read user question, configuration, and any user feedback from shared store."""
        store = get_shared_store(shared)

        # Check for user feedback from validation history
        user_feedback = None
        if store.validation_history:
            latest_validation = store.validation_history[-1]
            if latest_validation.user_input:
                user_feedback = latest_validation.user_input

        return store.user_question, store.config.num_queries, user_feedback

    def exec(self, prep_res):
        """Generate diverse search queries using LLM."""
        user_question, num_queries, user_feedback = prep_res

        # Build prompt with user feedback if available
        base_prompt = f"""
        Given this research question: "{user_question}"
        """

        if user_feedback:
            base_prompt += prompts.query_generation_feedback_prompt.format(
                user_feedback=user_feedback
            )

        prompt = base_prompt + prompts.query_generation_user_prompt.format(
            num_queries=num_queries
        )

        instructions = (
            f"Generate exactly {num_queries} search queries with rationale for each."
        )

        # Use structured output to get SearchQuery objects
        response = call_llm_structured(
            prompt=prompt,
            response_model=SearchQueriesResponse,
            instructions=instructions,
        )

        if not response:
            raise ValueError(
                f"Empty Response at QueryGeneration: {user_question=}, {num_queries=}, {user_feedback=}"
            )
        else:
            return response.queries

    def post(self, shared, prep_res, exec_res):
        """Store generated queries in shared store."""
        store = get_shared_store(shared)
        store.search_queries = exec_res
        update_shared_store(shared, store)
        user_question, num_queries, user_feedback = prep_res
        feedback_status = " (incorporating user feedback)" if user_feedback else ""
        print(
            f"✅ QueryGenerationNode completed: Generated {len(exec_res)} search queries{feedback_status}"
        )
        return "default"


class ParallelSearchNode(AsyncParallelBatchNode):
    """Execute search queries in parallel using Tavily API."""

    async def prep_async(self, shared):
        """Read search queries from shared store."""
        store = get_shared_store(shared)
        return store.search_queries

    async def exec_async(self, search_query):  # type: ignore
        """Execute a single search query."""
        # Get API key from shared store
        shared_dict = getattr(self, "_shared_dict", None)
        if shared_dict:
            store = get_shared_store(shared_dict)
            api_key = store.config.tavily_api_key
        else:
            # Fallback - this shouldn't happen in normal flow
            import os

            api_key = os.getenv("TAVILY_API_KEY", "")

        # Perform the search using the query string
        results = await search_web([search_query.query], api_key, max_results=5)

        # Create SearchResult with the full SearchQuery object
        if results:
            search_dict = results[0]  # Now returns dict instead of SearchResult
            # Create proper SearchResult with SearchQuery object
            return SearchResult(
                query=search_query,  # Use the full SearchQuery object
                results=search_dict.get("results", []),
                summary=search_dict.get("summary", None),
            )
        else:
            return SearchResult(query=search_query, results=[])

    async def post_async(self, shared, prep_res, exec_res_list):  # type: ignore
        """Store search results in shared store."""
        # Store shared dict for exec_async access
        self._shared_dict = shared

        store = get_shared_store(shared)
        store.search_results = exec_res_list
        update_shared_store(shared, store)
        total_results = sum(len(result.results) for result in exec_res_list)
        print(
            f"✅ ParallelSearchNode completed: Found {total_results} total search results from {len(exec_res_list)} queries"
        )
        return "default"


class SummarizationNode(BatchNode):
    """Summarize each search result set."""

    def prep(self, shared):
        """Read search results from shared store."""
        store = get_shared_store(shared)
        return store.search_results

    def exec(self, search_result):  # type: ignore
        """Summarize a single search result."""
        if not search_result.results:
            return "No search results found for this query."

        # Combine all result content
        content_parts = []
        for result in search_result.results[:3]:  # Use top 3 results
            if result.get("content"):
                content_parts.append(
                    f"Title: {result.get('title', 'Unknown')}\nContent: {result['content']}"
                )

        if not content_parts:
            return "No usable content found in search results."

        combined_content = "\n\n---\n\n".join(content_parts)

        # TODO: Remove this if the next prompt assignment works
        # prompt = f"""
        # Summarize the following search results for the query: "{search_result.query.query}"
        #
        # Query Rationale: {search_result.query.rationale}
        #
        # Search Results:
        # {combined_content}
        #
        # Provide a concise summary that captures the key information and insights relevant to the original query and its rationale. Focus on factual information and main themes.
        #
        # Summary:"""

        prompt = prompts.summarization_user_prompt.format(
            search_query=search_result.query.query,
            search_query_rationale=search_result.query.rationale,
            combined_content=combined_content,
        )

        summary = call_llm(prompt)
        return summary.strip()

    def post(self, shared, prep_res, exec_res_list):  # type: ignore
        """Update search results with summaries."""
        store = get_shared_store(shared)

        # Update each search result with its summary
        for i, summary in enumerate(exec_res_list):
            if i < len(store.search_results):
                store.search_results[i].summary = summary

        update_shared_store(shared, store)
        print(
            f"✅ SummarizationNode completed: Summarized {len(exec_res_list)} search result sets"
        )
        return "default"


class IdeaGenerationNode(Node):
    """Generate research ideas from summarized search results."""

    def prep(self, shared):
        """Read user question, search summaries, and user feedback."""
        store = get_shared_store(shared)
        summaries = []
        for result in store.search_results:
            if result.summary:
                summaries.append(
                    f"Query: {result.query.query}\nRationale: {result.query.rationale}\nSummary: {result.summary}"
                )

        # Check for user feedback from validation history
        user_feedback = None
        validation_feedback = None
        if store.validation_history:
            latest_validation = store.validation_history[-1]
            if latest_validation.user_input:
                user_feedback = latest_validation.user_input
            validation_feedback = latest_validation.feedback

        return store.user_question, summaries, user_feedback, validation_feedback

    def exec(self, prep_res):
        """Generate comprehensive research ideas."""
        user_question, summaries, user_feedback, validation_feedback = prep_res

        if not summaries:
            return "Unable to generate research ideas - no search summaries available."

        combined_summaries = "\n\n---\n\n".join(summaries)

        # Build prompt with user feedback if available
        base_prompt = f"""
            Based on the following research question and gathered information, generate ONE comprehensive, focused research idea.

            Original Question: "{user_question}"

            Gathered Information:
            {combined_summaries}
        """

        if user_feedback or validation_feedback:
            base_prompt += """
                USER FEEDBACK FOR REFINEMENT:
            """
            if user_feedback:
                base_prompt += f"- Specific user instruction: {user_feedback}\n"
            if validation_feedback:
                base_prompt += f"- General feedback: {validation_feedback}\n"

            base_prompt += """
                IMPORTANT: Please incorporate this feedback into the research idea. Make the requested changes while maintaining scientific rigor.
            """

        prompt = base_prompt + prompts.idea_generation_structure_prompt

        research_ideas = call_llm(prompt)
        return research_ideas.strip()

    def post(self, shared, prep_res, exec_res):
        """Store research ideas in shared store."""
        store = get_shared_store(shared)
        store.research_ideas = exec_res
        update_shared_store(shared, store)
        user_question, summaries, user_feedback, validation_feedback = prep_res
        feedback_status = (
            " (incorporating user feedback)"
            if (user_feedback or validation_feedback)
            else ""
        )
        print(
            f"✅ IdeaGenerationNode completed: Generated research idea ({len(exec_res)} characters){feedback_status}"
        )
        return "default"


class InteractiveValidationNode(Node):
    """Present ideas to user for validation with cycle management."""

    def prep(self, shared):
        """Read current state for validation."""
        store = get_shared_store(shared)
        return store

    def exec(self, store):  # type: ignore
        """Display current state and get user validation."""
        # Display current state
        current_state = display_current_state(store)
        print(current_state)

        # Check if max cycles reached
        if store.is_max_cycles_reached():
            print(f"\n⚠ Maximum validation cycles ({store.config.max_cycles}) reached.")
            print("Auto-approving current ideas to complete the process.")
            return True, "Maximum cycles reached - auto-approved", None

        # Get user input
        print(f"\nCycle {store.current_cycle + 1} of {store.config.max_cycles}")
        approved, feedback, user_input = get_user_validation_input()

        return approved, feedback, user_input

    def post(self, shared, prep_res, exec_res):
        """Process validation result and determine next action."""
        store = prep_res  # prep_res is the store object
        approved, feedback, user_input = exec_res

        # Add validation result to history
        store.add_validation_result(approved, feedback, user_input)

        # Update shared store
        update_shared_store(shared, store)

        # Determine next action
        should_complete, reason = check_completion_conditions(store)

        if should_complete:
            if reason == "approved":
                print(
                    f"✅ InteractiveValidationNode completed: Ideas approved (cycle {store.current_cycle})"
                )
                return "approve"
            elif reason == "max_cycles_reached":
                print(
                    f"✅ InteractiveValidationNode completed: Max cycles reached ({store.config.max_cycles})"
                )
                return "max_cycles_reached"

        # Continue refining
        print(
            f"🔄 InteractiveValidationNode: Refining ideas (cycle {store.current_cycle})"
        )
        return "refine"


class FinalizationNode(Node):
    """Store final approved ideas and mark completion."""

    def prep(self, shared):
        """Read current research ideas."""
        store = get_shared_store(shared)
        return store.research_ideas

    def exec(self, research_ideas):  # type: ignore
        """Format final output."""
        if not research_ideas:
            return "No research ideas were generated."

        return research_ideas

    def post(self, shared, prep_res, exec_res):
        """Mark flow as completed."""
        store = get_shared_store(shared)
        store.final_ideas = exec_res
        store.completed = True
        update_shared_store(shared, store)

        final_output = format_final_output(store)
        print(final_output)

        print(
            f"✅ FinalizationNode completed: Flow finished with {store.current_cycle} validation cycles"
        )
        return "default"


# Legacy nodes for backward compatibility (keep existing simple Q&A flow)
class GetQuestionNode(Node):
    def exec(self, _):  # type: ignore
        user_question = input("Enter your question: ")
        return user_question

    def post(self, shared, prep_res, exec_res):
        shared["question"] = exec_res
        return "default"


class AnswerNode(Node):
    def prep(self, shared):
        return shared["question"]

    def exec(self, question):  # type: ignore
        return call_llm(question)

    def post(self, shared, prep_res, exec_res):
        shared["answer"] = exec_res
