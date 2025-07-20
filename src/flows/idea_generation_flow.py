"""Flow definitions for the Research Assistant application."""

from pocketflow import AsyncFlow

from nodes.idea_generation import (
    # Idea Generation Flow nodes
    FinalizationNode,
    IdeaGenerationNode,
    InteractiveValidationNode,
    ParallelSearchNode,
    QueryGenerationNode,
    SummarizationNode,
)


def create_idea_generation_flow():
    """
    Create and return the main Idea Generation Flow with parameterized search,
    validation loops, and user interaction.

    Flow Structure:
    QueryGeneration >> ParallelSearch >> Summarization >> IdeaGeneration >> Validation
                                                              ^                   |
                                                              |-- refine --------|
                                                              |
    Finalization <-- approve/max_cycles_reached --------------|
    """
    # Create all nodes
    query_gen = QueryGenerationNode(max_retries=2, wait=1)
    parallel_search = ParallelSearchNode(max_retries=2, wait=2)
    summarization = SummarizationNode(max_retries=2, wait=1)
    idea_generation = IdeaGenerationNode(max_retries=2, wait=1)
    validation = InteractiveValidationNode()
    finalization = FinalizationNode()

    # Connect nodes in the main sequence
    query_gen >> parallel_search >> summarization >> idea_generation >> validation

    # Connect validation outcomes
    validation - "approve" >> finalization
    validation - "max_cycles_reached" >> finalization
    validation - "refine" >> query_gen  # Loop back for refinement

    # Create AsyncFlow to handle the parallel search node
    return AsyncFlow(start=query_gen)
