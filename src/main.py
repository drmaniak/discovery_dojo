"""Main entry point for the Research Assistant application."""

import asyncio
import os
import sys

from pocketflow import AsyncFlow

from domain.config import RAGConfig, SearchConfig, create_shared_store
from domain.shared_store import (
    format_final_output,
    format_full_pipeline_output,
    format_full_research_assistant_output,
    format_planning_output,
)
from flows.flow_factory import get_flow
from flows.legacy_qa_flow import create_qa_flow


def setup_environment() -> bool:
    """
    Check if required environment variables are set.

    Returns:
        True if environment is properly configured, False otherwise
    """
    required_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
    optional_vars = ["NEBIUS_API_KEY"]

    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   {var}")
        print("\nPlease set these environment variables and try again.")
        print("Example:")
        print("export OPENAI_API_KEY='your-openai-key'")
        print("export TAVILY_API_KEY='your-tavily-key'")
        return False

    # Check optional variables and warn
    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    if missing_optional:
        print("⚠️ Optional environment variables not set:")
        for var in missing_optional:
            print(f"   {var}")
        print(
            "Note: NEBIUS_API_KEY is required for RAG novelty assessment with embeddings"
        )
        print("Example: export NEBIUS_API_KEY='your-nebius-key'")
        print()

    return True


def get_user_question() -> str:
    """Get research question from user with examples."""
    print("🔬 Welcome to the AI Research Assistant!")
    print("=" * 50)
    print("\nThis comprehensive tool helps you:")
    print("📋 PHASE 1: Generate research ideas by:")
    print("  • Creating diverse search queries from your question")
    print("  • Searching the web for relevant information")
    print("  • Generating concrete research ideas")
    print("  • Iteratively refining ideas with your feedback")
    print("🔍 PHASE 2: Assess novelty by:")
    print("  • Comparing against 2.7M ArXiv papers")
    print("  • Calculating mathematical novelty scores")
    print("  • Optional reranking with local AI models")
    print("📅 PHASE 3: Create research plans by:")
    print("  • Interactive project configuration")
    print("  • Comprehensive phase planning")
    print("  • Beautiful markdown output")
    print("\nExample research questions:")
    print("• How can AI help with climate change research?")
    print("• What are the latest developments in quantum computing?")
    print("• How can machine learning improve healthcare outcomes?")
    print("• Can we use LLMs to improve software testing?")
    print("• How might blockchain enhance scientific reproducibility?")

    while True:
        question = input("\n💭 Enter your research question: ").strip()
        if question:
            return question
        print("Please enter a valid question.")


def get_configuration(include_rag: bool = False) -> SearchConfig:
    """Get configuration from user input and environment."""
    print("\n⚙️ Configuration")
    print("-" * 20)

    # Get number of search queries
    while True:
        try:
            num_queries = input(
                "Number of search queries to generate (1-5, default 3): "
            ).strip()
            if not num_queries:
                num_queries = 3
            else:
                num_queries = int(num_queries)

            if 1 <= num_queries <= 5:
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")

    # Get max validation cycles
    while True:
        try:
            max_cycles = input("Maximum validation cycles (1-5, default 3): ").strip()
            if not max_cycles:
                max_cycles = 3
            else:
                max_cycles = int(max_cycles)

            if 1 <= max_cycles <= 5:
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")

    # RAG Configuration
    rag_config = RAGConfig()  # Use defaults
    enable_rag = True  # Default enabled

    if include_rag:
        print("\n🔍 RAG (Novelty Assessment) Configuration")
        print("-" * 40)

        # Enable/disable RAG
        while True:
            rag_choice = (
                input("Enable novelty assessment with RAG? (y/n, default y): ")
                .strip()
                .lower()
            )
            if not rag_choice or rag_choice in ["y", "yes"]:
                enable_rag = True
                break
            elif rag_choice in ["n", "no"]:
                enable_rag = False
                break
            else:
                print("Please enter 'y' or 'n'.")

        if enable_rag:
            # Get Qdrant URL
            qdrant_url = input(
                f"Qdrant URL (default {rag_config.qdrant_url}): "
            ).strip()
            if qdrant_url:
                rag_config.qdrant_url = qdrant_url

            # Get collection name
            collection_name = input(
                f"Collection name (default {rag_config.collection_name}): "
            ).strip()
            if collection_name:
                rag_config.collection_name = collection_name

            # Get reranking option
            while True:
                rerank_choice = (
                    input("Enable reranking with local Qwen models? (y/n, default n): ")
                    .strip()
                    .lower()
                )
                if not rerank_choice or rerank_choice in ["n", "no"]:
                    rag_config.enable_reranking = False
                    break
                elif rerank_choice in ["y", "yes"]:
                    rag_config.enable_reranking = True

                    # Get reranker model
                    print("\nAvailable reranker models:")
                    print("1. Qwen/Qwen3-Reranker-0.6B (faster, smaller)")
                    print("2. Qwen/Qwen3-Reranker-4B (slower, better)")

                    while True:
                        model_choice = input(
                            "Choose model (1 or 2, default 1): "
                        ).strip()
                        if not model_choice or model_choice == "1":
                            rag_config.rerank_model = "Qwen/Qwen3-Reranker-0.6B"
                            break
                        elif model_choice == "2":
                            rag_config.rerank_model = "Qwen/Qwen3-Reranker-4B"
                            break
                        else:
                            print("Please enter 1 or 2.")

                    # Get reranker URL
                    rerank_url = input(
                        f"Local reranker URL (default {rag_config.rerank_base_url}): "
                    ).strip()
                    if rerank_url:
                        rag_config.rerank_base_url = rerank_url

                    break
                else:
                    print("Please enter 'y' or 'n'.")

    return SearchConfig(
        num_queries=num_queries,
        max_cycles=max_cycles,
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        rag_config=rag_config,
        enable_rag_flow=enable_rag,
    )


async def run_idea_generation_flow(user_question: str, config: SearchConfig):
    """
    Run the main idea generation flow only.

    Args:
        user_question: The research question from user
        config: Configuration for the flow
    """
    # Create shared store
    shared_store = create_shared_store(user_question, config)
    shared_dict = {"store": shared_store}

    print("\n🚀 Starting research idea generation...")
    print(
        f"📊 Configuration: {config.num_queries} queries, {config.max_cycles} max cycles"
    )
    print("\n" + "=" * 60)

    try:
        # Get and run the flow
        flow = get_flow("idea_generation")
        if isinstance(flow, AsyncFlow):
            await flow.run_async(shared_dict)
        else:
            flow.run(shared_dict)

        print("\n✅ Research idea generation completed!")

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Partial results may be available in the shared store.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please check your API keys and network connection.")
        sys.exit(1)


async def run_full_research_pipeline(user_question: str, config: SearchConfig):
    """
    Run the complete research pipeline (Idea Generation + RAG Novelty Assessment).

    Args:
        user_question: The research question from user
        config: Configuration for the flow
    """
    # Create shared store
    shared_store = create_shared_store(user_question, config)
    shared_dict = {"store": shared_store}

    print("\n🚀 Starting full research pipeline...")
    print(
        f"📊 Configuration: {config.num_queries} queries, {config.max_cycles} max cycles"
    )
    if config.enable_rag_flow:
        print(
            f"🔍 RAG Assessment: {config.rag_config.collection_name} at {config.rag_config.qdrant_url}"
        )
        if config.rag_config.enable_reranking:
            print(f"🔄 Reranking: {config.rag_config.rerank_model}")
        else:
            print("📊 Ranking: Similarity-based only")
    print("\n" + "=" * 60)

    try:
        # Check if RAG is enabled
        if config.enable_rag_flow:
            # Check if Nebius API key is available for embeddings
            if not os.getenv("NEBIUS_API_KEY"):
                print(
                    "⚠️ Warning: NEBIUS_API_KEY not set. RAG novelty assessment requires embeddings."
                )
                print("Continuing with idea generation only...")
                flow = get_flow("idea_generation")
            else:
                # Run full pipeline
                flow = get_flow("full_pipeline")
        else:
            # Run idea generation only
            flow = get_flow("idea_generation")

        if isinstance(flow, AsyncFlow):
            await flow.run_async(shared_dict)
        else:
            flow.run(shared_dict)

        # Display final results
        store = shared_dict["store"]
        if store.rag_completed and store.novelty_assessment:
            print("\n🎉 Full research pipeline completed!")

            # Display detailed results using the new function
            full_output = format_full_pipeline_output(store)
            print(full_output)
        else:
            print("\n✅ Research idea generation completed!")

            # Display standard final output
            final_output = format_final_output(store)
            print(final_output)

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Partial results may be available in the shared store.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please check your API keys and network connection.")
        if "Qdrant" in str(e):
            print("💡 Tip: Make sure Qdrant server is running and accessible.")
        elif "NEBIUS_API_KEY" in str(e):
            print("💡 Tip: Set NEBIUS_API_KEY for embedding generation.")
        sys.exit(1)


def run_simple_qa():
    """Run the legacy simple Q&A flow."""
    print("🤖 Simple Q&A Mode")
    print("=" * 20)

    shared = {"question": None, "answer": None}

    qa_flow = create_qa_flow()
    qa_flow.run(shared)
    print(f"\nQuestion: {shared['question']}")
    print(f"Answer: {shared['answer']}")


async def run_complete_research_assistant(user_question: str, config: SearchConfig):
    """
    Run the complete 3-phase research assistant pipeline.

    This includes:
    1. Idea Generation Flow with interactive validation
    2. RAG Flow for novelty assessment
    3. Planning Flow for comprehensive research plan generation

    Args:
        user_question: The research question from user
        config: Configuration for the flows
    """
    # Create shared store
    shared_store = create_shared_store(user_question, config)
    shared_dict = {"store": shared_store}

    print("\n🚀 Starting Complete Research Assistant Pipeline...")
    print(
        f"📊 Configuration: {config.num_queries} queries, {config.max_cycles} max cycles"
    )
    print(
        f"🔍 RAG Assessment: {config.rag_config.collection_name} at {config.rag_config.qdrant_url}"
    )
    if config.rag_config.enable_reranking:
        print(f"🔄 Reranking: {config.rag_config.rerank_model}")
    else:
        print("📊 Ranking: Similarity-based only")
    print("📋 Planning: Interactive research plan generation")
    print("\n" + "=" * 80)

    try:
        # Check required API keys
        missing_keys = []
        if not os.getenv("NEBIUS_API_KEY"):
            missing_keys.append("NEBIUS_API_KEY")

        if missing_keys:
            print(f"⚠️ Warning: Missing API keys: {', '.join(missing_keys)}")
            print(
                "The complete pipeline requires all API keys. Falling back to idea generation only..."
            )
            flow = get_flow("idea_generation")
        else:
            # Run complete research assistant pipeline
            flow = get_flow("complete_assistant")

        if isinstance(flow, AsyncFlow):
            await flow.run_async(shared_dict)
        else:
            flow.run(shared_dict)

        # Display comprehensive results
        store = shared_dict["store"]
        if store.planning_completed and store.research_plan:
            print("\n🎉 Complete Research Assistant Pipeline Completed!")

            # Display comprehensive results
            full_output = format_full_research_assistant_output(store)
            print(full_output)
        elif store.rag_completed and store.novelty_assessment:
            print("\n✅ Research pipeline completed (without planning)!")
            full_output = format_full_pipeline_output(store)
            print(full_output)
        else:
            print("\n✅ Idea generation completed!")
            final_output = format_final_output(store)
            print(final_output)

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Partial results may be available in the shared store.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please check your API keys and network connection.")
        if "Qdrant" in str(e):
            print("💡 Tip: Make sure Qdrant server is running and accessible.")
        elif "NEBIUS_API_KEY" in str(e):
            print("💡 Tip: Set NEBIUS_API_KEY for embedding generation.")
        sys.exit(1)


def run_planning_only_mode():
    """
    Run planning flow only - requires existing research idea and novelty assessment.
    This mode is useful when you want to create plans for existing research ideas.
    """
    print("\n📋 PLANNING ONLY MODE")
    print("=" * 50)
    print("This mode creates research plans from existing ideas.")
    print("You'll need to provide a research idea manually.")

    # Get research idea from user
    print("\n💡 Please provide your research idea:")
    research_idea = input("Research idea: ").strip()

    if not research_idea:
        print("❌ No research idea provided. Exiting.")
        return

    # Create minimal configuration for planning only
    config = SearchConfig(
        num_queries=1,  # Not used in planning only
        max_cycles=1,  # Not used in planning only
        tavily_api_key=os.getenv("TAVILY_API_KEY", "dummy"),  # Not used
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),  # Required for LLM
        enable_rag_flow=False,  # RAG not used in planning only
    )

    # Create shared store and populate with manual research idea
    shared_store = create_shared_store("Planning only mode", config)
    shared_store.final_ideas = research_idea
    shared_store.completed = True  # Mark idea generation as "completed"

    # Mock novelty assessment for planning (not available in planning-only mode)
    from domain.config import NoveltyAssessment

    mock_assessment = NoveltyAssessment(
        research_idea=research_idea,
        total_papers_retrieved=0,
        reranking_enabled=False,
        final_papers_count=0,
        final_novelty_score=0.5,  # Neutral score
        confidence=0.3,  # Low confidence since no real assessment
        top_similar_papers=[],
        assessment_summary="Planning-only mode: No novelty assessment performed.",
    )
    shared_store.novelty_assessment = mock_assessment
    shared_store.rag_completed = True  # Mark RAG as "completed"

    shared_dict = {"store": shared_store}

    print("\n🚀 Starting Planning Flow...")
    print(f"💡 Research Idea: {research_idea[:100]}...")
    print("\n" + "=" * 60)

    try:
        # Run planning flow only
        planning_flow = get_flow("planning")
        planning_flow.run(shared_dict)

        # Display results
        store = shared_dict["store"]
        if store.planning_completed and store.research_plan:
            print("\n🎉 Research Planning Completed!")
            planning_output = format_planning_output(store)
            print(planning_output)
        else:
            print("\n❌ Planning flow did not complete successfully.")

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Partial results may be available in the shared store.")
    except Exception as e:
        print(f"\n❌ An error occurred during planning: {str(e)}")
        print("Please check your OpenAI API key and network connection.")
        sys.exit(1)


async def main_async():
    """Main async function for the research assistant."""
    if not setup_environment():
        return

    print("\n🔧 Select Mode:")
    print("1. Idea Generation Only (no novelty assessment)")
    print("2. Full Research Pipeline (idea generation + RAG novelty assessment)")
    print("3. Complete Research Assistant (idea generation + RAG + planning)")
    print("4. Planning Only (requires existing research idea)")
    print("5. Simple Q&A (legacy mode)")

    while True:
        choice = input("\nChoose mode (1, 2, 3, 4, or 5): ").strip()
        if choice in ["1", "2", "3", "4", "5"]:
            break
        print("Please enter 1, 2, 3, 4, or 5.")

    if choice == "1":
        # Idea Generation Only
        user_question = get_user_question()
        config = get_configuration(include_rag=False)
        await run_idea_generation_flow(user_question, config)
    elif choice == "2":
        # Full Research Pipeline (Ideas + RAG)
        user_question = get_user_question()
        config = get_configuration(include_rag=True)
        await run_full_research_pipeline(user_question, config)
    elif choice == "3":
        # Complete Research Assistant (Ideas + RAG + Planning)
        user_question = get_user_question()
        config = get_configuration(include_rag=True)
        await run_complete_research_assistant(user_question, config)
    elif choice == "4":
        # Planning Only Mode
        run_planning_only_mode()
    else:
        # Simple Q&A Flow
        run_simple_qa()


def main():
    """Main synchronous entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
