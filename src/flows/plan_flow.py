from pocketflow import Flow

from nodes.plan_generation import (
    PlanFinalizationNode,
    PlanGenerationNode,
    PlanOutputNode,
    PlanValidationNode,
    UserPlanningConfigNode,
)


def create_planning_flow():
    """
    Create and return the Planning Flow for comprehensive research plan generation.

    Flow Structure:
    UserPlanningConfig >> PlanGeneration >> PlanValidation >> PlanFinalization >> PlanOutput
                                              ↑                 |
                                              |-- refine -------|
                                              |
                                          approve/max_cycles

    This flow takes validated research ideas and novelty assessments to create:
    1. Interactive user configuration for project type and timeline
    2. LLM-generated comprehensive research plan with structured phases
    3. Interactive validation and refinement cycles
    4. Beautiful markdown output saved to file
    """
    # Create planning nodes with appropriate retries
    user_config = UserPlanningConfigNode()
    plan_generation = PlanGenerationNode(max_retries=2, wait=1)
    plan_validation = PlanValidationNode()
    plan_finalization = PlanFinalizationNode()
    plan_output = PlanOutputNode()

    # Connect main sequence
    user_config >> plan_generation >> plan_validation

    # Connect validation outcomes with branching
    plan_validation - "approve" >> plan_finalization
    plan_validation - "max_cycles_reached" >> plan_finalization
    plan_validation - "refine" >> plan_generation  # Loop back for refinement

    # Final output generation
    plan_finalization >> plan_output

    # Return regular Flow (no async needed for planning flow)
    return Flow(start=user_config)
