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
from utils import prompts
from utils.custom_qdrant_client import QdrantClient
from utils.llm_utils import call_embedder, call_llm
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
        """Generate comprehensive novelty assessment."""
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

        # Prepare paper summaries for LLM
        paper_summaries = []
        for i, ranked_paper in enumerate(
            ranked_papers[:5], 1
        ):  # Top 5 for LLM analysis
            paper = ranked_paper.paper
            paper_summaries.append(f"""
            Paper {i}:
            Title: {paper.title}
            Abstract: {paper.abstract[:600]}{"..." if len(paper.abstract) > 600 else ""}
            Similarity Score: {paper.similarity_score:.3f}
            Novelty Score: {ranked_paper.novelty_score:.3f}
            """)

        combined_papers = "\n".join(paper_summaries)

        prompt = prompts.novelty_assessment_prompt.format(
            research_idea=research_idea, combined_papers=combined_papers
        )

        try:
            response = call_llm(prompt)

            # Parse novelty score and confidence
            lines = response.split("\n")
            novelty_score = 0.5  # Default
            confidence = 0.7  # Default
            assessment_text = response

            for line in lines:
                line = line.strip()
                if line.startswith("NOVELTY SCORE:"):
                    try:
                        score_text = line.split(":", 1)[1].strip()
                        # Extract just the number part
                        import re

                        match = re.search(r"(\d+\.?\d*)", score_text)
                        if match:
                            novelty_score = float(match.group(1))
                            novelty_score = max(
                                0.0, min(1.0, novelty_score)
                            )  # Clamp to [0,1]
                    except Exception as e:
                        print(f"Error in LLM-based Novelty calculation: {str(e)}")

                elif line.startswith("CONFIDENCE:"):
                    try:
                        conf_text = line.split(":", 1)[1].strip()
                        import re

                        match = re.search(r"(\d+\.?\d*)", conf_text)
                        if match:
                            confidence = float(match.group(1))
                            confidence = max(
                                0.0, min(1.0, confidence)
                            )  # Clamp to [0,1]
                    except Exception as e:
                        print(f"Error in LLM-based Novelty calculation: {str(e)}")

            # Create assessment
            assessment = NoveltyAssessment(
                research_idea=research_idea,
                total_papers_retrieved=len(ranked_papers) if ranked_papers else 0,
                reranking_enabled=rag_config.enable_reranking,
                final_papers_count=len(ranked_papers),
                final_novelty_score=novelty_score,
                confidence=confidence,
                top_similar_papers=ranked_papers[:10],  # Store top 10
                assessment_summary=assessment_text,
            )

            return assessment

        except Exception as e:
            # Fallback assessment if LLM fails
            avg_novelty = (
                sum(p.novelty_score for p in ranked_papers) / len(ranked_papers)
                if ranked_papers
                else 0.8
            )

            assessment = NoveltyAssessment(
                research_idea=research_idea,
                total_papers_retrieved=len(ranked_papers) if ranked_papers else 0,
                reranking_enabled=rag_config.enable_reranking,
                final_papers_count=len(ranked_papers),
                final_novelty_score=avg_novelty,
                confidence=0.6,  # Lower confidence for fallback
                top_similar_papers=ranked_papers[:10],
                assessment_summary=f"Automated assessment failed ({str(e)}). Novelty estimated from similarity scores: {avg_novelty:.2f}",
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
