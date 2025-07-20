from flows.idea_generation_flow import create_idea_generation_flow
from flows.legacy_qa_flow import create_qa_flow
from flows.research_assistant_flow import create_research_assistant_flow


# Factory function for easy access
def get_flow(flow_type: str = "idea_generation"):
    """
    Factory function to get different flow types.

    Args:
        flow_type: Type of flow to create ('qa', 'idea_generation', 'research')

    Returns:
        Configured flow instance
    """
    if flow_type == "qa":
        return create_qa_flow()
    elif flow_type == "idea_generation":
        return create_idea_generation_flow()
    elif flow_type == "research":
        return create_research_assistant_flow()
    else:
        raise ValueError(f"Unknown flow type: {flow_type}")
