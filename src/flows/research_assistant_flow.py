from flows.idea_generation_flow import create_idea_generation_flow


def create_research_assistant_flow():
    """
    Main entry point for the Research Assistant.
    Currently returns the Idea Generation Flow.
    """
    return create_idea_generation_flow()
