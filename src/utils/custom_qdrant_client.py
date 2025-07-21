"""Simplified Qdrant client using the official qdrant-client library."""

from typing import List, Optional

from qdrant_client import QdrantClient as OfficialQdrantClient

from domain.config import ArxivPaper


class QdrantClient:
    """Simplified wrapper around the official Qdrant client."""

    def __init__(self, url: str, collection_name: str):
        """
        Initialize Qdrant client using the official library.

        Args:
            url: Qdrant server URL (e.g., "http://localhost:6333")
            collection_name: Name of the collection to search
        """
        # Parse URL to extract host and port
        if url.startswith("http://"):
            host_port = url[7:]  # Remove "http://"
        elif url.startswith("https://"):
            host_port = url[8:]  # Remove "https://"
        else:
            host_port = url

        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 6333  # Default Qdrant port

        self.collection_name = collection_name
        self.client = OfficialQdrantClient(host=host, port=port)

    def health_check(self) -> bool:
        """
        Check if Qdrant server is available.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Try to get collection info as a health check
            self.client.get_collections()
            return True
        except Exception:
            return False

    def get_collection_info(self) -> dict:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection information

        Raises:
            RuntimeError: If collection doesn't exist or request fails
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "result": {
                    "status": collection_info.status.value
                    if collection_info.status
                    else "unknown",
                    "vectors_count": collection_info.vectors_count,
                    "points_count": collection_info.points_count,
                    "segments_count": collection_info.segments_count,
                }
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get collection info: {str(e)}")

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 50,
        score_threshold: Optional[float] = None,
    ) -> List[ArxivPaper]:
        """
        Search for similar vectors in the collection.

        Args:
            query_vector: The query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score (optional)

        Returns:
            List of ArxivPaper objects sorted by similarity score

        Raises:
            RuntimeError: If search request fails
        """
        try:
            # Perform search using the modern query_points API
            result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )
            hits = result.points

            # Convert search results to ArxivPaper objects
            papers = []
            for i, hit in enumerate(hits):
                try:
                    payload = hit.payload or {}
                    paper = ArxivPaper(
                        id=payload.get("id", str(hit.id)),
                        title=payload.get("title", "Unknown Title"),
                        abstract=payload.get("abstract", ""),
                        similarity_score=float(hit.score),
                        metadata={
                            "authors": payload.get("authors", []),
                            "categories": payload.get("categories", []),
                            "submitted": payload.get("submitted", ""),
                            "doi": payload.get("doi", ""),
                            "point_id": hit.id,
                        },
                    )
                    papers.append(paper)
                except Exception as e:
                    print(f"Warning: Failed to parse search result {i}: {str(e)}")
                    continue

            return papers

        except Exception as e:
            raise RuntimeError(f"Vector search failed: {str(e)}")

    def count_points(self) -> int:
        """
        Get the total number of points in the collection.

        Returns:
            Number of points in the collection

        Raises:
            RuntimeError: If request fails
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count or 0
        except Exception as e:
            raise RuntimeError(f"Failed to count points: {str(e)}")

    def close(self):
        """Close the client connection."""
        if hasattr(self.client, "close"):
            self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def search_arxiv_papers(
    query_vector: List[float],
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "arxiv_papers",
    top_k: int = 50,
) -> List[ArxivPaper]:
    """
    Convenience function to search ArXiv papers using the official client.

    Args:
        query_vector: The query embedding vector
        qdrant_url: Qdrant server URL
        collection_name: Collection name
        top_k: Number of results to return

    Returns:
        List of ArxivPaper objects

    Raises:
        RuntimeError: If search fails
    """
    with QdrantClient(qdrant_url, collection_name) as client:
        return client.search_vectors(query_vector, top_k)


if __name__ == "__main__":
    # Test the simplified Qdrant client
    import random

    print("Testing simplified Qdrant client...")

    try:
        with QdrantClient("http://localhost:6333", "arxiv_papers") as client:
            # Health check
            if not client.health_check():
                print("❌ Qdrant server not available")
                exit(1)
            print("✅ Qdrant server is healthy")

            # Collection info
            try:
                info = client.get_collection_info()
                print(f"✅ Collection status: {info['result']['status']}")

                count = client.count_points()
                print(f"✅ Collection has {count:,} papers")

                # Test search with a random vector
                test_vector = [random.random() for _ in range(4096)]
                papers = client.search_vectors(test_vector, top_k=3)
                print(f"✅ Found {len(papers)} papers in test search:")
                for i, paper in enumerate(papers, 1):
                    print(
                        f"  {i}. {paper.title[:50]}... (similarity: {paper.similarity_score:.3f})"
                    )

            except Exception as e:
                print(f"❌ Collection access failed: {str(e)}")

    except Exception as e:
        print(f"❌ Qdrant client test failed: {str(e)}")
