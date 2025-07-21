from pocketflow import AsyncFlow

from flows.idea_generation_flow import create_idea_generation_flow
from flows.plan_flow import create_planning_flow
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
    Returns the full research pipeline (Idea Generation + RAG).
    """
    return create_full_research_pipeline()


def create_complete_research_assistant():
    """
    Create the complete 3-phase research assistant pipeline.

    This combines all three flows in sequence:
    1. Idea Generation Flow (with interactive validation)
    2. RAG Flow (novelty assessment against ArXiv papers)
    3. Planning Flow (comprehensive research plan generation)

    Flow Structure:
    [Idea Generation Flow] >> [RAG Flow] >> [Planning Flow]

    Each flow builds upon the previous one's output, creating a comprehensive
    research pipeline from user question to actionable research plan.
    """
    # Create all three main flows
    idea_flow = create_idea_generation_flow()
    rag_flow = create_rag_flow()
    planning_flow = create_planning_flow()

    # Connect them sequentially - each flow's output feeds the next
    idea_flow >> rag_flow >> planning_flow

    # Return AsyncFlow since idea generation uses async parallel search
    return AsyncFlow(start=idea_flow)
