"""Optional reranking functionality using local Qwen reranker models."""

import requests
from openai import OpenAI

from domain.config import ArxivPaper, RAGConfig, RankedPaper


class QwenReranker:
    """Client for local Qwen reranker models with OpenAI-compatible API."""

    def __init__(self, base_url: str, model: str):
        """
        Initialize reranker client.

        Args:
            base_url: Base URL of the local reranker service
            model: Model name (e.g., "Qwen/Qwen3-Reranker-0.6B")
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = OpenAI(
            base_url=self.base_url,
            api_key="dummy",  # Local models typically don't need real API keys
        )

    def is_available(self) -> bool:
        """
        Check if the reranker service is available.

        Returns:
            True if service is available, False otherwise
        """
        try:
            # Try to get model info
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """
        Rerank documents using the local Qwen reranker.

        Args:
            query: The query text
            documents: List of document texts to rerank

        Returns:
            List of reranking scores (higher = more relevant)

        Raises:
            RuntimeError: If reranking fails
        """
        if not documents:
            return []

        try:
            # Format documents for reranking
            # This assumes the reranker expects query-document pairs
            # pairs = [{"query": query, "document": doc} for doc in documents]

            # Call the reranker via completions endpoint with structured format
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a reranking model. Rank the relevance of documents to the query. Return scores as JSON array of floats.",
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\n\nDocuments: {documents}\n\nReturn relevance scores:",
                    },
                ],
                temperature=0.0,
            )

            # Parse scores from response
            scores_text = response.choices[0].message.content

            # Simple fallback: return uniform scores if parsing fails
            try:
                import json

                scores = json.loads(str(scores_text))
                if isinstance(scores, list) and len(scores) == len(documents):
                    return [float(score) for score in scores]
            except Exception as e:
                print(f"❌ ERROR when loading json scores in rereanking step: {str(e)}")

            # Fallback: return decreasing scores based on position
            return [1.0 - (i * 0.1) for i in range(len(documents))]

        except Exception as e:
            raise RuntimeError(f"Reranking failed: {str(e)}")


def create_ranked_papers_by_similarity(
    papers: list[ArxivPaper], top_n: int
) -> list[RankedPaper]:
    """
    Create ranked papers using only similarity scores (no reranking).

    Args:
        papers: List of papers with similarity scores
        top_n: Number of top papers to return

    Returns:
        List of RankedPaper objects ranked by similarity
    """
    # Sort by similarity score (descending)
    sorted_papers = sorted(papers, key=lambda p: p.similarity_score, reverse=True)

    ranked_papers = []
    for i, paper in enumerate(sorted_papers[:top_n]):
        novelty_score = 1.0 - paper.similarity_score  # Novelty = inverse of similarity

        ranked_paper = RankedPaper(
            paper=paper,
            original_rank=i + 1,
            rerank_score=None,  # No reranking used
            final_rank=i + 1,
            novelty_score=max(0.0, min(1.0, novelty_score)),  # Clamp to [0, 1]
        )
        ranked_papers.append(ranked_paper)

    return ranked_papers


def rerank_with_qwen(
    query: str, papers: list[ArxivPaper], reranker: QwenReranker, top_n: int
) -> list[RankedPaper]:
    """
    Rerank papers using Qwen reranker model.

    Args:
        query: The research idea query
        papers: List of papers to rerank
        reranker: QwenReranker instance
        top_n: Number of top papers to return

    Returns:
        List of RankedPaper objects ranked by reranker scores
    """
    if not papers:
        return []

    # Prepare documents for reranking (title + abstract)
    documents = []
    for paper in papers:
        doc_text = f"Title: {paper.title}\nAbstract: {paper.abstract}"
        documents.append(doc_text)

    # Get reranking scores
    rerank_scores = reranker.rerank(query, documents)

    # Combine papers with their rerank scores
    paper_scores = list(zip(papers, rerank_scores))

    # Sort by rerank score (descending)
    sorted_papers = sorted(paper_scores, key=lambda x: x[1], reverse=True)

    # Create RankedPaper objects
    ranked_papers = []
    for final_rank, (paper, rerank_score) in enumerate(sorted_papers[:top_n], 1):
        # Find original rank (position in original similarity-sorted list)
        original_rank = next(
            (i + 1 for i, p in enumerate(papers) if p.id == paper.id), final_rank
        )

        # Calculate novelty score from rerank score
        # Assuming rerank scores are in [0, 1] range
        normalized_score = max(0.0, min(1.0, float(rerank_score)))
        novelty_score = 1.0 - normalized_score

        ranked_paper = RankedPaper(
            paper=paper,
            original_rank=original_rank,
            rerank_score=normalized_score,
            final_rank=final_rank,
            novelty_score=novelty_score,
        )
        ranked_papers.append(ranked_paper)

    return ranked_papers


def rerank_papers_optional(
    query: str, papers: list[ArxivPaper], config: RAGConfig
) -> list[RankedPaper]:
    """
    Optionally rerank papers based on configuration.

    Args:
        query: The research idea query
        papers: List of papers retrieved from Qdrant
        config: RAG configuration with reranking settings

    Returns:
        List of RankedPaper objects, either similarity-ranked or reranked
    """
    if not papers:
        return []

    # Check if reranking is enabled and configured
    if not config.enable_reranking or not config.rerank_model:
        print(f"📊 Using similarity ranking (top {config.top_n_final} papers)")
        return create_ranked_papers_by_similarity(papers, config.top_n_final)

    # Try to use reranking
    try:
        print(f"🔄 Attempting reranking with {config.rerank_model}...")

        reranker = QwenReranker(config.rerank_base_url, config.rerank_model)

        if not reranker.is_available():
            print(
                "⚠️ Reranker service not available, falling back to similarity ranking"
            )
            return create_ranked_papers_by_similarity(papers, config.top_n_final)

        ranked_papers = rerank_with_qwen(query, papers, reranker, config.top_n_final)
        print(f"✅ Reranking completed using {config.rerank_model}")
        return ranked_papers

    except Exception as e:
        print(f"⚠️ Reranking failed ({str(e)}), falling back to similarity ranking")
        return create_ranked_papers_by_similarity(papers, config.top_n_final)


if __name__ == "__main__":
    # Test reranking functionality
    from domain.config import RAGConfig

    print("Testing reranking functionality...")

    # Create test config with reranking enabled
    config = RAGConfig(
        enable_reranking=True,
        rerank_model="Qwen/Qwen3-Reranker-0.6B",
        rerank_base_url="http://localhost:8080",
        top_n_final=5,
    )

    # Create test papers
    test_papers = [
        ArxivPaper(
            id="1",
            title="AI in Climate Research",
            abstract="This paper explores artificial intelligence applications in climate science...",
            similarity_score=0.8,
        ),
        ArxivPaper(
            id="2",
            title="Machine Learning for Weather Prediction",
            abstract="We present novel machine learning approaches for weather forecasting...",
            similarity_score=0.7,
        ),
    ]

    test_query = "How can AI help with climate change research?"

    # Test reranking
    try:
        ranked_papers = rerank_papers_optional(test_query, test_papers, config)
        print(f"✅ Got {len(ranked_papers)} ranked papers")

        for paper in ranked_papers:
            print(f"  - {paper.paper.title} (novelty: {paper.novelty_score:.2f})")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
