"""Main entry point for the Research Assistant application."""

import asyncio
import os
import sys

from domain.config import SearchConfig, create_shared_store
from flows.flow_factory import get_flow
from flows.legacy_qa_flow import create_qa_flow


def setup_environment() -> bool:
    """
    Check if required environment variables are set.

    Returns:
        True if environment is properly configured, False otherwise
    """
    required_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
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

    return True


def get_user_question() -> str:
    """Get research question from user with examples."""
    print("🔬 Welcome to the AI Research Assistant!")
    print("=" * 50)
    print("\nThis tool helps you generate research ideas by:")
    print("• Creating diverse search queries from your question")
    print("• Searching the web for relevant information")
    print("• Generating concrete research ideas")
    print("• Iteratively refining ideas with your feedback")
    print("\nExample questions:")
    print("• How can AI help with climate change research?")
    print("• What are the latest developments in quantum computing?")
    print("• How can machine learning improve healthcare outcomes?")

    while True:
        question = input("\n💭 Enter your research question: ").strip()
        if question:
            return question
        print("Please enter a valid question.")


def get_configuration() -> SearchConfig:
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

    return SearchConfig(
        num_queries=num_queries,
        max_cycles=max_cycles,
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
    )


async def run_idea_generation_flow(user_question: str, config: SearchConfig):
    """
    Run the main idea generation flow.

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
        await flow.run_async(shared_dict)

        print("\n✅ Research idea generation completed!")

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user.")
        print("Partial results may be available in the shared store.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please check your API keys and network connection.")
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


async def main_async():
    """Main async function for the research assistant."""
    if not setup_environment():
        return

    print("\n🔧 Select Mode:")
    print("1. Research Idea Generation (full flow)")
    print("2. Simple Q&A (legacy mode)")

    while True:
        choice = input("\nChoose mode (1 or 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("Please enter 1 or 2.")

    if choice == "1":
        # Research Idea Generation Flow
        user_question = get_user_question()
        config = get_configuration()
        await run_idea_generation_flow(user_question, config)
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
