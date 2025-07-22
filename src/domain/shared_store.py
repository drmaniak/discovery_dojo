"""Helper functions for robust SharedStore management in PocketFlow."""

from typing import Any

from domain.config import (
    ArxivPaper,
    NoveltyAssessment,
    PlanValidationResult,
    RankedPaper,
    ResearchPlan,
    SearchQuery,
    SearchResult,
    SharedStore,
    UserPlanningInput,
    ValidationResult,
)


def get_shared_store(shared_dict: dict[str, Any]) -> SharedStore:
    """
    Safely extract SharedStore from PocketFlow shared dictionary.

    Args:
        shared_dict: Raw shared dictionary from PocketFlow

    Returns:
        SharedStore: Validated SharedStore object

    Raises:
        ValueError: If shared_dict doesn't contain valid SharedStore data
    """
    try:
        if isinstance(shared_dict.get("store"), SharedStore):
            return shared_dict["store"]
        elif "store" in shared_dict:
            return SharedStore.from_dict(shared_dict["store"])
        else:
            # Try to create from top-level keys (backward compatibility)
            return SharedStore.from_dict(shared_dict)
    except Exception as e:
        raise ValueError(f"Invalid SharedStore data in shared dictionary: {str(e)}")


def update_shared_store(shared_dict: dict[str, Any], store: SharedStore) -> None:
    """
    Update the PocketFlow shared dictionary with SharedStore data.

    Args:
        shared_dict: Raw shared dictionary from PocketFlow
        store: Updated SharedStore object
    """
    shared_dict["store"] = store


def safe_get_search_queries(store: SharedStore) -> list[SearchQuery] | list[str]:
    """
    Safely get search queries from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        List of search query strings
    """
    return store.search_queries if store.search_queries else []


def safe_get_search_results(store: SharedStore) -> list[SearchResult]:
    """
    Safely get search results from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        List of SearchResult objects
    """
    return store.search_results if store.search_results else []


def safe_get_research_ideas(store: SharedStore) -> str | None:
    """
    Safely get research ideas from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        Research ideas string or None if not set
    """
    return store.research_ideas


def safe_get_validation_history(store: SharedStore) -> list[ValidationResult]:
    """
    Safely get validation history from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        List of ValidationResult objects
    """
    return store.validation_history if store.validation_history else []


def display_current_state(store: SharedStore) -> str:
    """
    Create a formatted display of the current state for user interaction.

    Args:
        store: SharedStore object

    Returns:
        Formatted string showing current state
    """
    output = []
    output.append("=" * 60)
    output.append("RESEARCH IDEA GENERATION - CURRENT STATE")
    output.append("=" * 60)

    output.append(f"\nOriginal Question: {store.user_question}")
    output.append(f"Validation Cycle: {store.current_cycle}/{store.config.max_cycles}")

    if store.search_queries:
        output.append(f"\nSearch Queries Generated ({len(store.search_queries)}):")
        for i, search_query in enumerate(store.search_queries, 1):
            output.append(f'  {i}. "{search_query.query}"')
            output.append(f"     Rationale: {search_query.rationale}")

    if store.research_ideas:
        output.append("\nCurrent Research Ideas:")
        output.append("-" * 40)
        output.append(store.research_ideas)
        output.append("-" * 40)

    if store.validation_history:
        output.append("\nValidation History:")
        for i, validation in enumerate(store.validation_history, 1):
            status = "✓ APPROVED" if validation.approved else "✗ NEEDS WORK"
            output.append(f"  Cycle {validation.cycle_number}: {status}")
            output.append(f"    Feedback: {validation.feedback}")
            if validation.user_input:
                output.append(f"    User Input: {validation.user_input}")

    output.append("\n" + "=" * 60)
    return "\n".join(output)


def get_user_validation_input() -> tuple[bool, str, str | None]:
    """
    Get user validation input interactively.

    Returns:
        Tuple of (approved: bool, feedback: str, user_input: Optional[str])
    """
    print("\nValidation Options:")
    print("1. Approve these ideas (type 'approve' or 'a')")
    print("2. Request refinement (type 'refine' or 'r')")
    print("3. Provide specific feedback (type 'feedback' or 'f')")

    while True:
        choice = input("\nYour choice: ").strip().lower()

        if choice in ["approve", "a"]:
            return True, "Ideas approved by user", None

        elif choice in ["refine", "r"]:
            user_input = input(
                "Any specific refinement suggestions (optional): "
            ).strip()
            feedback = "User requested general refinement"
            if user_input:
                feedback += f" with suggestions: {user_input}"
            return False, feedback, user_input if user_input else None

        elif choice in ["feedback", "f"]:
            feedback = input("Please provide your detailed feedback: ").strip()
            while not feedback:
                feedback = input("Feedback cannot be empty. Please try again: ").strip()

            user_input = input(
                "Any specific suggestions for improvement (optional): "
            ).strip()
            return False, feedback, user_input if user_input else None

        else:
            print("Invalid choice. Please type 'approve', 'refine', or 'feedback'")


def check_completion_conditions(store: SharedStore) -> tuple[bool, str]:
    """
    Check if the flow should complete based on current conditions.

    Args:
        store: SharedStore object

    Returns:
        Tuple of (should_complete: bool, reason: str)
    """
    # Check if max cycles reached
    if store.is_max_cycles_reached():
        return True, "max_cycles_reached"

    # Check if ideas were approved in latest validation
    if store.validation_history:
        latest = store.validation_history[-1]
        if latest.approved:
            return True, "approved"

    return False, "continue"


def format_final_output(store: SharedStore) -> str:
    """
    Format the final output when the flow completes.

    Args:
        store: SharedStore object

    Returns:
        Formatted final output string
    """
    output = []
    output.append("=" * 60)
    output.append("RESEARCH IDEA GENERATION - COMPLETED")
    output.append("=" * 60)

    output.append(f"\nOriginal Question: {store.user_question}")
    output.append(f"Total Validation Cycles: {store.current_cycle}")

    if store.final_ideas:
        output.append("\nFINAL RESEARCH IDEAS:")
        output.append("-" * 40)
        output.append(store.final_ideas)
        output.append("-" * 40)

    # Show completion reason
    if store.validation_history and store.validation_history[-1].approved:
        output.append("\n✓ Completion Reason: Ideas approved by user")
    elif store.is_max_cycles_reached():
        output.append(
            f"\n⚠ Completion Reason: Maximum cycles ({store.config.max_cycles}) reached"
        )

    output.append("\n" + "=" * 60)
    return "\n".join(output)


# RAG-specific display functions


def display_rag_status(store: SharedStore) -> str:
    """
    Display current RAG flow status.

    Args:
        store: SharedStore object

    Returns:
        Formatted string showing RAG status
    """
    output = []
    output.append("🔍 RAG NOVELTY ASSESSMENT STATUS")
    output.append("-" * 40)

    if not store.config.enable_rag_flow:
        output.append("❌ RAG flow disabled")
        return "\n".join(output)

    # Embedding status
    if store.embedded_query:
        output.append(
            f"✅ Research idea embedded ({len(store.embedded_query.embedding)} dimensions)"
        )
    else:
        output.append("⏳ Research idea not yet embedded")

    # Retrieval status
    if store.retrieved_papers:
        output.append(
            f"✅ Retrieved {len(store.retrieved_papers)} papers from database"
        )
        avg_similarity = sum(p.similarity_score for p in store.retrieved_papers) / len(
            store.retrieved_papers
        )
        output.append(f"   Average similarity: {avg_similarity:.3f}")
    else:
        output.append("⏳ Papers not yet retrieved")

    # Ranking status
    if store.final_papers:
        reranking_used = any(p.rerank_score is not None for p in store.final_papers)
        method = "reranking" if reranking_used else "similarity"
        output.append(f"✅ Ranked {len(store.final_papers)} papers using {method}")

        avg_novelty = sum(p.novelty_score for p in store.final_papers) / len(
            store.final_papers
        )
        output.append(f"   Average novelty: {avg_novelty:.3f}")
    else:
        output.append("⏳ Papers not yet ranked")

    # Assessment status
    if store.novelty_assessment:
        output.append("✅ Novelty assessment completed")
        output.append(
            f"   Final novelty score: {store.novelty_assessment.final_novelty_score:.2f}"
        )
        output.append(f"   Confidence: {store.novelty_assessment.confidence:.2f}")
    else:
        output.append("⏳ Novelty assessment not yet completed")

    return "\n".join(output)


def display_novelty_assessment_summary(assessment: NoveltyAssessment) -> str:
    """
    Display a summary of the novelty assessment.

    Args:
        assessment: NoveltyAssessment object

    Returns:
        Formatted summary string
    """
    output = []
    output.append("=" * 60)
    output.append("NOVELTY ASSESSMENT SUMMARY")
    output.append("=" * 60)

    output.append("\nResearch Idea:")
    output.append("-" * 20)
    output.append(
        assessment.research_idea[:300] + "..."
        if len(assessment.research_idea) > 300
        else assessment.research_idea
    )

    output.append("\nAssessment Results:")
    output.append("-" * 20)
    output.append(f"📊 Novelty Score: {assessment.final_novelty_score:.2f}/1.0")
    output.append(f"🎯 Confidence: {assessment.confidence:.2f}/1.0")
    output.append(f"📚 Papers Retrieved: {assessment.total_papers_retrieved}")
    output.append(f"🔍 Papers Analyzed: {assessment.final_papers_count}")
    output.append(
        f"🔄 Reranking Used: {'Yes' if assessment.reranking_enabled else 'No'}"
    )

    # Novelty interpretation
    if assessment.final_novelty_score >= 0.8:
        interpretation = "🟢 HIGHLY NOVEL - Very few similar papers found"
    elif assessment.final_novelty_score >= 0.6:
        interpretation = "🟡 MODERATELY NOVEL - Some similar work exists"
    elif assessment.final_novelty_score >= 0.4:
        interpretation = "🟠 LIMITED NOVELTY - Substantial similar work exists"
    else:
        interpretation = "🔴 LOW NOVELTY - Extensive similar work found"

    output.append(f"\n{interpretation}")

    if assessment.top_similar_papers:
        output.append("\nTop Similar Papers:")
        output.append("-" * 20)
        for i, ranked_paper in enumerate(assessment.top_similar_papers[:5], 1):
            paper = ranked_paper.paper
            output.append(f"{i}. {paper.title}")
            authors = get_author_string(paper)
            if authors:
                output.append(f"   By {authors}")
            output.append(
                f"   Similarity: {paper.similarity_score:.3f} | Novelty: {ranked_paper.novelty_score:.3f}"
            )
            if ranked_paper.rerank_score is not None:
                output.append(f"   Rerank Score: {ranked_paper.rerank_score:.3f}")

    output.append("\n" + "=" * 60)
    return "\n".join(output)


def display_rag_papers(papers: list[RankedPaper], max_papers: int = 10) -> str:
    """
    Display ranked papers in a formatted table.

    Args:
        papers: List of RankedPaper objects
        max_papers: Maximum number of papers to display

    Returns:
        Formatted papers display
    """
    if not papers:
        return "No papers found."

    output = []
    output.append(f"\n📚 TOP {min(len(papers), max_papers)} SIMILAR PAPERS")
    output.append("=" * 80)

    for i, ranked_paper in enumerate(papers[:max_papers], 1):
        paper = ranked_paper.paper
        output.append(f"\n{i}. {paper.title}")
        output.append(f"   Similarity: {paper.similarity_score:.3f}")
        output.append(f"   Novelty: {ranked_paper.novelty_score:.3f}")

        if ranked_paper.rerank_score is not None:
            output.append(f"   Rerank Score: {ranked_paper.rerank_score:.3f}")

        # Show first 100 characters of abstract
        abstract_preview = (
            paper.abstract[:200] + "..."
            if len(paper.abstract) > 200
            else paper.abstract
        )
        output.append(f"   Abstract: {abstract_preview}")

        # Show metadata if available
        author_string = get_author_string(paper)
        if author_string:
            output.append(f"   {author_string}")

    output.append("\n" + "=" * 80)
    return "\n".join(output)


def get_author_string(paper: ArxivPaper) -> str | None:
    if paper.metadata:
        if paper.metadata.get("authors"):
            authors = paper.metadata["authors"]
            if isinstance(authors, list):
                authors_str = ", ".join(authors[:2])  # Show first 2 authors
                if len(authors) > 2:
                    authors_str += f" et al. (+{len(authors) - 2} more)"
            else:
                authors_str = str(authors)
                authors_list = authors_str.split(",")
                if len(authors_list) > 2:
                    authors_str = (
                        f"{authors_list[:2]} et al. (+{len(authors) - 2} more)"
                    )

            return f"Authors: {authors_str}"


def format_full_pipeline_output(store: SharedStore) -> str:
    """
    Format the complete output for the full research pipeline including RAG results.

    Args:
        store: SharedStore object

    Returns:
        Formatted complete output string
    """
    output = []
    output.append("=" * 80)
    output.append("FULL RESEARCH PIPELINE - COMPLETED")
    output.append("=" * 80)

    # Basic info
    output.append(f"\nOriginal Question: {store.user_question}")
    output.append(f"Total Validation Cycles: {store.current_cycle}")

    # Idea Generation Results
    if store.final_ideas:
        output.append("\n🧠 FINAL RESEARCH IDEAS:")
        output.append("-" * 50)
        output.append(store.final_ideas)
        output.append("-" * 50)

    # RAG Results
    if store.novelty_assessment:
        output.append(
            "\n" + display_novelty_assessment_summary(store.novelty_assessment)
        )

        if store.final_papers:
            output.append(display_rag_papers(store.final_papers, max_papers=5))

    # Show completion reason
    if store.validation_history and store.validation_history[-1].approved:
        output.append("\n✓ Completion Reason: Ideas approved by user")
    elif store.is_max_cycles_reached():
        output.append(
            f"\n⚠ Completion Reason: Maximum cycles ({store.config.max_cycles}) reached"
        )

    output.append("\n" + "=" * 80)
    return "\n".join(output)


# =====================================================================
# PLANNING FLOW HELPER FUNCTIONS
# =====================================================================


def safe_get_planning_input(store: SharedStore) -> UserPlanningInput | None:
    """
    Safely get user planning input from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        UserPlanningInput object or None if not set
    """
    return store.user_planning_input


def safe_get_research_plan(store: SharedStore) -> ResearchPlan | None:
    """
    Safely get research plan from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        ResearchPlan object or None if not set
    """
    return store.research_plan


def safe_get_plan_validation_history(store: SharedStore) -> list[PlanValidationResult]:
    """
    Safely get plan validation history from SharedStore.

    Args:
        store: SharedStore object

    Returns:
        List of PlanValidationResult objects
    """
    return store.plan_validation_history if store.plan_validation_history else []


def check_planning_completion_conditions(store: SharedStore) -> dict[str, Any]:
    """
    Check planning flow completion conditions.

    Args:
        store: SharedStore object

    Returns:
        Dict with completion status information
    """
    return {
        "planning_completed": store.planning_completed,
        "has_research_plan": store.research_plan is not None,
        "validation_cycles": len(store.plan_validation_history),
        "max_cycles_reached": store.is_max_plan_cycles_reached(),
        "current_cycle": store.plan_current_cycle,
        "max_allowed_cycles": store.plan_config.max_refinement_cycles,
    }


def display_planning_progress(store: SharedStore) -> None:
    """
    Display current planning flow progress to the user.

    Args:
        store: SharedStore object
    """
    print("\n📊 PLANNING PROGRESS:")
    print(f"{'=' * 50}")

    # Basic status
    status = "Completed" if store.planning_completed else "In Progress"
    print(f"Status: {status}")

    # Plan information
    if store.research_plan:
        print(f"📋 Plan Title: {store.research_plan.title}")
        print(
            f"📝 Project Type: {store.research_plan.project_type.replace('_', ' ').title()}"
        )
        print(f"⏰ Timeline: {store.research_plan.timeline.replace('_', ' ').title()}")
        print(f"📈 Phases: {len(store.research_plan.phases)}")

    # Validation progress
    if store.plan_validation_history:
        print(
            f"🔄 Validation Cycles: {len(store.plan_validation_history)}/{store.plan_config.max_refinement_cycles}"
        )
        latest = store.plan_validation_history[-1]
        approval_status = "✅ Approved" if latest.approved else "🔄 Needs Refinement"
        print(f"Latest Status: {approval_status}")

    print(f"{'=' * 50}")


def format_planning_output(store: SharedStore) -> str:
    """
    Format final planning output for display.

    Args:
        store: SharedStore object

    Returns:
        Formatted string with planning results
    """
    if not store.planning_completed or not store.research_plan:
        return "❌ Planning flow not completed or no plan available."

    plan = store.research_plan
    output = []

    # Header
    output.append("🎉 RESEARCH PLANNING COMPLETED!")
    output.append("=" * 60)

    # Plan overview
    output.append(f"📋 Plan Title: {plan.title}")
    output.append(f"📝 Project Type: {plan.project_type.replace('_', ' ').title()}")
    output.append(f"⏰ Timeline: {plan.timeline.replace('_', ' ').title()}")
    output.append(f"👥 Target Audience: {plan.target_audience.title()}")
    output.append(f"📈 Total Phases: {len(plan.phases)}")

    output.append("\n" + "=" * 60)

    # Executive summary
    output.append("🎯 EXECUTIVE SUMMARY:")
    output.append(plan.executive_summary)

    output.append("\n" + "=" * 60)

    # Phase overview
    output.append("📅 PHASE OVERVIEW:")
    for phase in plan.phases:
        output.append(f"  Phase {phase.phase_number}: {phase.title}")
        output.append(f"    ⏱️  Duration: {phase.duration}")
        output.append(f"    ✅ Tasks: {len(phase.tasks)}")
        output.append(f"    🎯 Deliverables: {len(phase.deliverables)}")

    # Validation summary
    if store.plan_validation_history:
        output.append("\n🔍 VALIDATION SUMMARY:")
        output.append(f"  Cycles completed: {len(store.plan_validation_history)}")
        final_validation = store.plan_validation_history[-1]
        if final_validation.approved:
            output.append("  ✅ Final status: Approved")
        else:
            output.append("  ⏱️  Final status: Maximum cycles reached")

    output.append("\n" + "=" * 60)
    output.append("📁 Plan saved to file for detailed review")
    output.append("=" * 60)

    return "\n".join(output)


def format_full_research_assistant_output(store: SharedStore) -> str:
    """
    Format complete research assistant output including all three flows.

    Args:
        store: SharedStore object

    Returns:
        Comprehensive formatted string with all results
    """
    output = []

    # Main header
    output.append("🤖 COMPLETE RESEARCH ASSISTANT RESULTS")
    output.append("=" * 80)

    # Phase 1: Idea Generation
    output.append("\n📋 PHASE 1: IDEA GENERATION")
    output.append("-" * 40)
    if store.final_ideas:
        output.append("✅ Status: Completed")
        output.append(f"💡 Research Idea: {store.final_ideas[:200]}...")
        output.append(f"🔄 Validation Cycles: {len(store.validation_history)}")
    else:
        output.append("❌ Status: Not completed")

    # Phase 2: Novelty Assessment
    output.append("\n🔍 PHASE 2: NOVELTY ASSESSMENT")
    output.append("-" * 40)
    if store.novelty_assessment:
        output.append("✅ Status: Completed")
        output.append(
            f"📊 Novelty Score: {store.novelty_assessment.final_novelty_score:.2f}/1.0"
        )
        output.append(f"📈 Confidence: {store.novelty_assessment.confidence:.2f}")
        output.append(
            f"📚 Papers Analyzed: {store.novelty_assessment.final_papers_count}"
        )
    else:
        output.append("❌ Status: Not completed")

    # Phase 3: Research Planning
    output.append("\n📅 PHASE 3: RESEARCH PLANNING")
    output.append("-" * 40)
    if store.planning_completed and store.research_plan:
        plan = store.research_plan
        output.append("✅ Status: Completed")
        output.append(f"📋 Plan Title: {plan.title}")
        output.append(f"📝 Project Type: {plan.project_type.replace('_', ' ').title()}")
        output.append(f"⏰ Timeline: {plan.timeline.replace('_', ' ').title()}")
        output.append(f"📈 Phases: {len(plan.phases)}")
        output.append(f"🔄 Planning Cycles: {len(store.plan_validation_history)}")
    else:
        output.append("❌ Status: Not completed")

    output.append("\n" + "=" * 80)
    output.append("🎉 COMPREHENSIVE RESEARCH PIPELINE COMPLETED!")
    output.append("📁 All results saved to respective files")
    output.append("=" * 80)

    return "\n".join(output)


# Utility function for testing and debugging
def create_test_shared_store() -> dict[str, Any]:
    """Create a test shared store for development and testing."""
    from .config import SearchConfig, create_shared_store

    config = SearchConfig(
        num_queries=2,
        max_cycles=2,
        tavily_api_key="test_key",
        openai_api_key="test_key",
    )

    store = create_shared_store(
        user_question="How can AI help with climate change?", config=config
    )

    return {"store": store}
