"""Simple Tavily API integration using the official TavilyClient."""

import asyncio
from typing import Any, Dict, List

from tavily import TavilyClient


def tavily_search(
    query: str, api_key: str, max_results: int = 5, include_raw_content: bool = False
) -> Dict[str, Any]:
    """
    Search the web using the Tavily API and return results.

    Args:
        query: The search query to execute
        api_key: Tavily API key
        max_results: Maximum number of results to return
        include_raw_content: Whether to include raw content from sources

    Returns:
        Dictionary containing search results with query and results list
    """
    client = TavilyClient(api_key=api_key)
    response = client.search(
        query, max_results=max_results, include_raw_content=include_raw_content
    )

    # Return in our expected format
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
