import asyncio
from typing import Any, Dict, List

from tavily import TavilyClient


def strip_thinking_tokens(text: str) -> str:
    """
    Remove <think> and </think> tags and their content from the text.

    Iteratively removes all occurrences of content enclosed in thinking tokens.

    Args:
        text (str): The text to process

    Returns:
        str: The text with thinking tokens and their content removed
    """
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text


def deduplicate_and_format_sources(
    search_response: dict[str, Any] | list[dict[str, Any]],
    max_tokens_per_source: int,
    fetch_full_page: bool = False,
) -> str:
    """
    Format and deduplicate search responses from various search APIs.

    Takes either a single search response or list of responses from search APIs,
    deduplicates them by URL, and formats them into a structured string.

    Args:
        search_response (Union[Dict[str, Any], List[Dict[str, Any]]]): Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results
        max_tokens_per_source (int): Maximum number of tokens to include for each source's content
        fetch_full_page (bool, optional): Whether to include the full page content. Defaults to False.

    Returns:
        str: Formatted string with deduplicated sources

    Raises:
        ValueError: If input is neither a dict with 'results' key nor a list of search results
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response["results"]
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and "results" in response:
                sources_list.extend(response["results"])
            else:
                sources_list.extend(response)
    else:
        raise ValueError(
            "Input must be either a dict with 'results' or a list of search results"
        )

    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source["url"] not in unique_sources:
            unique_sources[source["url"]] = source

    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source: {source['title']}\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += (
            f"Most relevant content from source: {source['content']}\n===\n"
        )
        if fetch_full_page:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get("raw_content", "")
            if raw_content is None:
                raw_content = ""
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"

    return formatted_text.strip()


def format_sources(search_results: dict[str, Any]) -> str:
    """
    Format search results into a bullet-point list of sources with URLs.

    Creates a simple bulleted list of search results with title and URL for each source.

    Args:
        search_results (Dict[str, Any]): Search response containing a 'results' key with
                                        a list of search result objects

    Returns:
        str: Formatted string with sources as bullet points in the format "* title : url"
    """
    return "\n".join(
        f"* {source['title']} : {source['url']}" for source in search_results["results"]
    )


def tavily_search(
    query: str,
    api_key: str,
    max_results: int = 5,
    include_raw_content: bool = False,
    # query: str, fetch_full_page: bool = True, max_results: int = 3
) -> dict[str, Any]:
    """
    Search the web using the Tavily API and return formatted results.

    Uses the TavilyClient to perform searches. Tavily API key must be configured
    in the environment.

    Args:
        query (str): The search query to execute
        fetch_full_page (bool, optional): Whether to include raw content from sources.
                                         Defaults to True.
        max_results (int, optional): Maximum number of results to return. Defaults to 3.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Search response containing:
            - results (list): List of search result dictionaries, each containing:
                - title (str): Title of the search result
                - url (str): URL of the search result
                - content (str): Snippet/summary of the content
                - raw_content (str or None): Full content of the page if available and
                                            fetch_full_page is True
    """

    tavily_client = TavilyClient(api_key=api_key)
    response = tavily_client.search(
        query, max_results=max_results, include_raw_content=include_raw_content
    )

    return {"query": query, "results": response.get("results", [])}


def tavily_search_multiple(
    queries: List[str], api_key: str, max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Perform multiple searches sequentially.

    Args:
        queries: List of search query strings
        api_key: Tavily API key
        max_results: Maximum number of results per query

    Returns:
        List of dictionaries with query and results
    """
    results = []

    for query in queries:
        try:
            result = tavily_search(query, api_key, max_results)
            results.append(result)
        except Exception as e:
            print(f"Warning: Search failed for query '{query}': {str(e)}")
            # Create empty result for failed queries
            results.append(
                {
                    "query": query,
                    "results": [],
                    "summary": "Search failed - no results available",
                }
            )

    return results


# Async wrapper for PocketFlow compatibility
async def search_web(
    queries: List[str], api_key: str, max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Async wrapper for search functionality (runs in thread pool).

    Args:
        queries: List of search queries
        api_key: Tavily API key
        max_results: Maximum results per query

    Returns:
        List of dictionaries with query and results
    """
    # Run the synchronous search in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, tavily_search_multiple, queries, api_key, max_results
    )


# Synchronous wrapper for compatibility
def search_web_sync(
    queries: List[str], api_key: str, max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for search functionality.

    Args:
        queries: List of search queries
        api_key: Tavily API key
        max_results: Maximum results per query

    Returns:
        List of dictionaries with query and results
    """
    return tavily_search_multiple(queries, api_key, max_results)


if __name__ == "__main__":
    # Test the search functionality
    import os

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("Please set TAVILY_API_KEY environment variable")
        exit(1)

    # Test queries
    test_queries = [
        "artificial intelligence climate change research",
        "machine learning environmental monitoring",
    ]

    print("Testing Tavily search...")
    results = search_web_sync(test_queries, api_key, max_results=3)

    for i, result in enumerate(results):
        print(f"\n=== Results for query {i + 1}: '{result['query']}' ===")
        print(f"Found {len(result['results'])} results")
        for j, res in enumerate(result["results"][:2]):  # Show first 2 results
            print(f"{j + 1}. {res.get('title', 'No title')}")
            print(f"   URL: {res.get('url', 'No URL')}")
            content = res.get("content", "No content")
            print(f"   Content: {content[:200]}...")
