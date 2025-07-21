"""Enhanced node classes for the Idea Generation Flow."""

from pocketflow import Node

from domain.config import (
    EmbeddedQuery,
    NoveltyAssessment,
)
from domain.shared_store import (
    display_novelty_assessment_summary,
    get_shared_store,
    update_shared_store,
)
from utils.custom_qdrant_client import QdrantClient
from utils.llm_utils import call_embedder
from utils.reranking import rerank_papers_optional

# RAG Flow Nodes for Novelty Assessment


class EmbeddingNode(Node):
    """Embed the final research idea for vector similarity search."""

    def prep(self, shared):
        """Read the final research idea from shared store."""
        store = get_shared_store(shared)
        if not store.final_ideas:
            raise RuntimeError("No final research ideas available for embedding")
        return store.final_ideas

    def exec(self, research_idea):  # type: ignore
        """Generate embedding for the research idea."""
        try:
            embedding = call_embedder(research_idea, model="Qwen/Qwen3-Embedding-8B")
            return embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    def post(self, shared, prep_res, exec_res):
        """Store embedded query in shared store."""
        store = get_shared_store(shared)
        store.embedded_query = EmbeddedQuery(
            text=prep_res, embedding=exec_res, embedding_model="Qwen/Qwen3-Embedding-8B"
        )
        update_shared_store(shared, store)
        print(
            f"✅ EmbeddingNode completed: Generated {len(exec_res)}-dimensional embedding"
        )
        return "default"


class RetrievalNode(Node):
    """Retrieve similar papers from Qdrant vector database."""

    def prep(self, shared):
        """Read embedded query and RAG configuration."""
        store = get_shared_store(shared)
        if not store.embedded_query:
            raise RuntimeError("No embedded query available for retrieval")
        return store.embedded_query, store.config.rag_config

    def exec(self, prep_res):
        """Search for similar papers in Qdrant database."""
        embedded_query, rag_config = prep_res

        try:
            # Check if Qdrant is available
            with QdrantClient(
                rag_config.qdrant_url, rag_config.collection_name
            ) as client:
                if not client.health_check():
                    raise RuntimeError(
                        f"Qdrant server not available at {rag_config.qdrant_url}"
                    )

                # Get collection info
                try:
                    # info = client.get_collection_info()
                    total_papers = client.count_points()
                    print(
                        f"📊 Searching {total_papers:,} papers in collection '{rag_config.collection_name}'"
                    )
                except Exception as e:
                    print(f"⚠️ Could not get collection info: {str(e)}")

                # Perform vector search
                papers = client.search_vectors(
                    query_vector=embedded_query.embedding,
                    top_k=rag_config.top_k_retrieval,
                )

                return papers

        except Exception as e:
            raise RuntimeError(f"Failed to retrieve papers from Qdrant: {str(e)}")

    def post(self, shared, prep_res, exec_res):
        """Store retrieved papers in shared store."""
        store = get_shared_store(shared)
        store.retrieved_papers = exec_res
        update_shared_store(shared, store)

        avg_similarity = (
            sum(p.similarity_score for p in exec_res) / len(exec_res) if exec_res else 0
        )
        print(
            f"✅ RetrievalNode completed: Retrieved {len(exec_res)} papers (avg similarity: {avg_similarity:.3f})"
        )
        return "default"


class RankingNode(Node):
    """Optionally rerank papers and select top N for final assessment."""

    def prep(self, shared):
        """Read retrieved papers, embedded query, and configuration."""
        store = get_shared_store(shared)
        if not store.retrieved_papers:
            raise RuntimeError("No retrieved papers available for ranking")
        if not store.embedded_query:
            raise RuntimeError("No embedded query available for ranking")
        return (
            store.embedded_query.text,
            store.retrieved_papers,
            store.config.rag_config,
        )

    def exec(self, prep_res):
        """Rank papers using optional reranking."""
        query_text, papers, rag_config = prep_res

        if not papers:
            return []

        try:
            # Use the optional reranking function
            ranked_papers = rerank_papers_optional(
                query=query_text, papers=papers, config=rag_config
            )

            return ranked_papers

        except Exception as e:
            raise RuntimeError(f"Failed to rank papers: {str(e)}")

    def post(self, shared, prep_res, exec_res):
        """Store ranked papers in shared store."""
        store = get_shared_store(shared)
        store.final_papers = exec_res
        update_shared_store(shared, store)

        if exec_res:
            avg_novelty = sum(p.novelty_score for p in exec_res) / len(exec_res)
            reranking_used = any(p.rerank_score is not None for p in exec_res)
            method = "reranking" if reranking_used else "similarity"
            print(
                f"✅ RankingNode completed: Ranked {len(exec_res)} papers using {method} (avg novelty: {avg_novelty:.3f})"
            )
        else:
            print("✅ RankingNode completed: No papers to rank")

        return "default"


class NoveltyAssessmentNode(Node):
    """Generate final novelty assessment using LLM analysis."""

    def prep(self, shared):
        """Read all data needed for novelty assessment."""
        store = get_shared_store(shared)
        if not store.final_papers:
            # No papers found - still generate assessment
            return (
                store.embedded_query.text if store.embedded_query else "",
                [],
                store.config.rag_config,
            )
        if not store.embedded_query:
            query_text = ""
        else:
            query_text = store.embedded_query.text
        return query_text, store.final_papers, store.config.rag_config

    def exec(self, prep_res):
        """Generate novelty assessment using mathematical approach - average novelty scores."""
        research_idea, ranked_papers, rag_config = prep_res

        if not ranked_papers:
            # No similar papers found - high novelty
            assessment = NoveltyAssessment(
                research_idea=research_idea,
                total_papers_retrieved=0,
                reranking_enabled=rag_config.enable_reranking,
                final_papers_count=0,
                final_novelty_score=0.95,  # High novelty if no similar papers
                confidence=0.8,
                top_similar_papers=[],
                assessment_summary="No similar papers found in the database, suggesting high novelty for this research idea.",
            )
            return assessment

        # Calculate final novelty score mathematically
        # Average the novelty scores (which are already 1 - similarity)
        novelty_scores = [ranked_paper.novelty_score for ranked_paper in ranked_papers]
        final_novelty_score = sum(novelty_scores) / len(novelty_scores)

        # Calculate confidence based on consistency of novelty scores
        # If all scores are similar, we have high confidence
        # If scores vary widely, confidence is lower
        if len(novelty_scores) > 1:
            variance = sum(
                (score - final_novelty_score) ** 2 for score in novelty_scores
            ) / len(novelty_scores)
            # Convert variance to confidence (lower variance = higher confidence)
            # Scale so that variance of 0.01 gives confidence ~0.9, variance of 0.25 gives confidence ~0.3
            confidence = max(0.3, min(0.9, 0.9 - (variance * 2.4)))
        else:
            confidence = 0.7  # Single paper, moderate confidence

        # Generate assessment summary based on the mathematical analysis
        top_papers = ranked_papers[:5]  # Top 5 most similar
        min_novelty = min(novelty_scores)
        max_novelty = max(novelty_scores)

        # Create interpretative summary
        if final_novelty_score >= 0.8:
            novelty_level = "highly novel"
            interpretation = "high potential for original contributions"
        elif final_novelty_score >= 0.6:
            novelty_level = "moderately novel"
            interpretation = "good potential with some novel aspects"
        elif final_novelty_score >= 0.4:
            novelty_level = "somewhat novel"
            interpretation = "limited novelty, significant overlap with existing work"
        else:
            novelty_level = "limited novelty"
            interpretation = "substantial overlap with existing research"

        # Build summary of most similar papers
        paper_summaries = []
        for i, ranked_paper in enumerate(top_papers, 1):
            paper = ranked_paper.paper
            paper_summaries.append(
                f"{i}. {paper.title} (novelty: {ranked_paper.novelty_score:.3f})"
            )

        assessment_summary = f"""MATHEMATICAL NOVELTY ASSESSMENT

        Final Novelty Score: {final_novelty_score:.3f} ({novelty_level})
        Confidence Level: {confidence:.3f}
        Score Range: {min_novelty:.3f} - {max_novelty:.3f}
        Papers Analyzed: {len(ranked_papers)}

        INTERPRETATION:
        This research idea demonstrates {interpretation}. The novelty score of {final_novelty_score:.3f} is calculated as the average of individual paper novelty scores (1 - similarity_score).

        MOST SIMILAR PAPERS:
        {chr(10).join(paper_summaries)}

        METHODOLOGY:
        • Novelty scores are calculated as 1 - cosine_similarity for each paper
        • Final score is the mathematical average of all individual novelty scores
        • Confidence reflects consistency across papers (lower variance = higher confidence)
        • No LLM bias or hallucination risk in scoring

        RECOMMENDATION:
        {"This research direction shows strong potential for novel contributions." if final_novelty_score >= 0.6 else "Consider refining the approach to increase differentiation from existing work, or focus on specific novel aspects."}"""

        # Create assessment
        assessment = NoveltyAssessment(
            research_idea=research_idea,
            total_papers_retrieved=len(ranked_papers),
            reranking_enabled=rag_config.enable_reranking,
            final_papers_count=len(ranked_papers),
            final_novelty_score=final_novelty_score,
            confidence=confidence,
            top_similar_papers=ranked_papers[:10],  # Store top 10
            assessment_summary=assessment_summary,
        )

        return assessment

    def post(self, shared, prep_res, exec_res):
        """Store novelty assessment and mark RAG flow as completed."""
        store = get_shared_store(shared)
        store.novelty_assessment = exec_res
        store.rag_completed = True
        update_shared_store(shared, store)

        # Display brief summary first
        print(
            f"✅ NoveltyAssessmentNode completed: Novelty score {exec_res.final_novelty_score:.2f} (confidence: {exec_res.confidence:.2f})"
        )

        # Display detailed assessment summary
        detailed_summary = display_novelty_assessment_summary(exec_res)
        print(detailed_summary)

        return "default"
