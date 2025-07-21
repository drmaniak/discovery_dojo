from flows.idea_generation_flow import create_idea_generation_flow
from flows.legacy_qa_flow import create_qa_flow
from flows.rag_flow import create_rag_flow
from flows.research_assistant_flow import (
    create_full_research_pipeline,
    create_research_assistant_flow,
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
            - 'full_pipeline': Complete pipeline (idea generation + RAG)
            - 'research': Alias for 'full_pipeline'

    Returns:
        Configured flow instance
    """
    if flow_type == "qa":
        return create_qa_flow()
    elif flow_type == "idea_generation":
        return create_idea_generation_flow()
    elif flow_type == "rag":
        return create_rag_flow()
    elif flow_type == "full_pipeline":
        return create_full_research_pipeline()
    elif flow_type == "research":
        return create_research_assistant_flow()  # Alias for full pipeline
    else:
        raise ValueError(
            f"Unknown flow type: {flow_type}. Available types: qa, idea_generation, rag, full_pipeline, research"
        )
