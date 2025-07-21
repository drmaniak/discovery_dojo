from flows.idea_generation_flow import create_idea_generation_flow
from flows.legacy_qa_flow import create_qa_flow
from flows.plan_flow import create_planning_flow
from flows.rag_flow import create_rag_flow
from flows.research_assistant_flow import (
    create_complete_research_assistant,
    create_full_research_pipeline,
)


# Factory function for easy access
def get_flow(flow_type: str = "idea_generation"):
    """
    Factory function to get different flow types.

    Args:
        flow_type: Type of flow to create:
            - 'qa': Simple Q&A flow (legacy)
            - 'idea_generation': Only idea generation flow
            - 'rag': Only RAG novelty assessment flow
            - 'planning': Only planning flow (requires existing research idea)
            - 'full_pipeline': Complete pipeline (idea generation + RAG)
            - 'complete_assistant': Full 3-phase pipeline (idea + RAG + planning)
            - 'research': Alias for 'complete_assistant'

    Returns:
        Configured flow instance
    """
    if flow_type == "qa":
        return create_qa_flow()
    elif flow_type == "idea_generation":
        return create_idea_generation_flow()
    elif flow_type == "rag":
        return create_rag_flow()
    elif flow_type == "planning":
        return create_planning_flow()
    elif flow_type == "full_pipeline":
        return create_full_research_pipeline()  # Ideas + RAG only
    elif flow_type == "complete_assistant":
        return create_complete_research_assistant()  # All 3 flows
    elif flow_type == "research":
        return create_complete_research_assistant()  # Alias for complete
    else:
        available_types = [
            "qa",
            "idea_generation",
            "rag",
            "planning",
            "full_pipeline",
            "complete_assistant",
            "research",
        ]
        raise ValueError(
            f"Unknown flow type: {flow_type}. Available types: {', '.join(available_types)}"
        )
