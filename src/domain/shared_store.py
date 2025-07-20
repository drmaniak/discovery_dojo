"""Helper functions for robust SharedStore management in PocketFlow."""

from typing import Any

from domain.config import (
    SearchQuery,
    SearchResult,
    SharedStore,
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
