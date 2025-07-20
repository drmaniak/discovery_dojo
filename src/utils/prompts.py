from datetime import datetime


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


query_writer_instructions = """Your goal is to generate a targeted web search query.

    <CONTEXT>
    Current date: {current_date}
    Please ensure your queries account for the most current information available as of this date.
    </CONTEXT>

    <TOPIC>
    {research_topic}
    </TOPIC>

    """


query_generation_user_prompt = """
            Generate {num_queries} diverse search queries that would help gather comprehensive information to answer this question. Each query should approach the topic from a different angle or focus on different aspects.

            For each query, provide:
            - query: The actual search query string
            - rationale: Why this query is relevant and what angle it covers

            Make sure each query is:
            - Specific and focused
            - Different from the others
            - Relevant to the original question (as modified by user feedback if provided)
            - Suitable for web search
            """
query_generation_feedback_prompt = """
            IMPORTANT: The user has provided specific refinement feedback: "{user_feedback}"
            Please incorporate this feedback when generating search queries. Modify the research focus accordingly.
            """


summarization_user_prompt = """
        Summarize the following search results for the query: "{search_query}"

        Query Rationale: {search_query_rationale}

        Search Results:
        {combined_content}

        Provide a concise summary that captures the key information and insights relevant to the original query and its rationale. Focus on factual information and main themes.

        Summary:"""


idea_generation_structure_prompt = """
                Generate a single, well-developed research idea that:
                1. Directly addresses the original question (as modified by user feedback if provided)
                2. Is informed by the gathered information
                3. Is specific and actionable
                4. Builds upon current knowledge shown in the summaries
                5. Could lead to meaningful insights or discoveries
                6. Incorporates any user feedback or refinement requests

                Format your response as:

                Research Idea:

                [Provide one comprehensive research idea with detailed explanation, including:
                - The specific research focus or hypothesis
                - Key methodologies or approaches to investigate
                - Expected outcomes or contributions
                - How it builds on the gathered information]

                The idea should be substantial and focused enough to guide actual research work.
            """
