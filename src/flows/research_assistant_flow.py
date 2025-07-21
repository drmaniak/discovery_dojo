from pocketflow import AsyncFlow

from flows.idea_generation_flow import create_idea_generation_flow
from flows.rag_flow import create_rag_flow


def create_full_research_pipeline():
    """
    Create the complete research pipeline that combines Idea Generation + RAG Flow.

    This creates a nested flow structure where:
    1. The Idea Generation Flow runs first (including validation)
    2. Upon completion, the RAG Flow automatically starts for novelty assessment

    Flow Structure:
    [Idea Generation Flow] >> [RAG Flow]
    """
    # Create the two main flows
    idea_flow = create_idea_generation_flow()
    rag_flow = create_rag_flow()

    # Connect them sequentially
    idea_flow >> rag_flow

    # Return AsyncFlow since idea generation uses async parallel search
    return AsyncFlow(start=idea_flow)


def create_research_assistant_flow():
    """
    Main entry point for the Research Assistant.
    Currently returns the Idea Generation Flow.
    """
    return create_idea_generation_flow()
