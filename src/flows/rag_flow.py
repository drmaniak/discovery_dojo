from pocketflow import Flow

from nodes.rag_novelty import (
    # RAG Flow nodes
    EmbeddingNode,
    NoveltyAssessmentNode,
    RankingNode,
    RetrievalNode,
)


def create_rag_flow():
    """
    Create and return the RAG (Retrieval Augmented Generation) Flow for novelty assessment.

    Flow Structure:
    EmbeddingNode >> RetrievalNode >> RankingNode >> NoveltyAssessmentNode

    This flow takes a finalized research idea and assesses its novelty by:
    1. Embedding the research idea text
    2. Retrieving similar papers from Qdrant vector database
    3. Optionally reranking papers using local Qwen models
    4. Generating a comprehensive novelty assessment
    """
    # Create all RAG nodes with retries for robustness
    embedding = EmbeddingNode(max_retries=2, wait=1)
    retrieval = RetrievalNode(max_retries=3, wait=2)  # More retries for DB operations
    ranking = RankingNode(max_retries=2, wait=1)
    assessment = NoveltyAssessmentNode(max_retries=2, wait=1)

    # Connect nodes in sequence
    embedding >> retrieval >> ranking >> assessment

    # Return regular Flow (no async needed for RAG flow)
    return Flow(start=embedding)
