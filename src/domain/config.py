"""Configuration and data models for the Idea Generation Flow using Pydantic."""

import os
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RAGConfig(BaseModel):
    """Configuration for RAG (Retrieval Augmented Generation) novelty assessment."""

    qdrant_url: str = Field(
        default="http://localhost:6333", description="Qdrant database URL"
    )
    collection_name: str = Field(
        default="arxiv_papers", description="Qdrant collection name"
    )
    top_k_retrieval: int = Field(
        default=50, ge=1, le=200, description="Number of papers to retrieve"
    )
    top_n_final: int = Field(
        default=10, ge=1, le=50, description="Final number of papers after ranking"
    )
    embedding_model: str = Field(
        default="Qwen/Qwen3-Embedding-8B", description="Embedding model name"
    )

    # Optional reranking configuration
    enable_reranking: bool = Field(
        default=False, description="Whether to enable reranking"
    )
    rerank_model: str | None = Field(default=None, description="Reranking model name")
    rerank_base_url: str = Field(
        default="http://localhost:8080", description="Local reranker endpoint"
    )


class SearchConfig(BaseModel):
    """Configuration for search parameters and API keys."""

    num_queries: int = Field(
        default=3, ge=1, le=5, description="Number of serach queries to generate"
    )
    max_cycles: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of validation cycles before completion",
    )
    tavily_api_key: str = Field(description="Tavily API key for web search")
    openai_api_key: str = Field(description="OpenAI API key for llm calls")

    # RAG configuration
    rag_config: RAGConfig = Field(
        default_factory=RAGConfig, description="RAG novelty assessment configuration"
    )
    enable_rag_flow: bool = Field(
        default=True, description="Whether to enable RAG flow after idea generation"
    )

    @field_validator("tavily_api_key")
    @classmethod
    def tavily_api_key_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("TAVILY_API_KEY cannot be empty")
        return v.strip()

    @field_validator("openai_api_key")
    @classmethod
    def openai_api_key_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("OPENAI_API_KEY cannot be empty")
        return v.strip()

    @classmethod
    def from_env(cls) -> "SearchConfig":
        """Create SearchConfig from environment variables."""
        return cls(
            num_queries=int(os.getenv("NUM_SEARCH_QUERIES", "3")),
            max_cycles=int(os.getenv("MAX_VALIDATION_CYCLES", "3")),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        )


class SearchQuery(BaseModel):
    """The search query generated from the user input, with rationale behind its relevance."""

    query: str = Field(description="The search query used")
    rationale: str = Field(
        description="The rationale behind why this query is relevant to the user input."
    )

    @field_validator("query")
    def query_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Search query cannot be empty")

        return v.strip()


# Response models for structured LLM output
class SearchQueriesResponse(BaseModel):
    """Response model for generating multiple search queries."""

    queries: list[SearchQuery] = Field(
        description="List of search queries with rationale"
    )


class SearchResult(BaseModel):
    """Individual seach results for a query with findings"""

    query: SearchQuery = Field(description="The search query used")
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Raw search results from API"
    )
    summary: str | None = Field(
        default=None, description="LLM-generated summary of results"
    )


class ValidationResult(BaseModel):
    """Result of a validation cycle with user feedback."""

    approved: bool = Field(description="Whether the ideas were approved")
    feedback: str = Field(description="Validation feedback or critique")
    user_input: str | None = Field(
        default=None, description="Optional user input for refinement"
    )
    cycle_number: int = Field(description="Which validation cycle this represents")

    @field_validator("feedback")
    @classmethod
    def feedback_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Validation feedback cannot be empty")
        return v.strip()


# RAG-specific data models
class EmbeddedQuery(BaseModel):
    """Query text with its vector embedding."""

    text: str = Field(description="The research idea text")
    embedding: list[float] = Field(description="Vector embedding of the text")
    embedding_model: str = Field(description="Model used for embedding")


class ArxivPaper(BaseModel):
    """Individual ArXiv paper from database."""

    id: str = Field(description="Paper identifier")
    title: str = Field(description="Paper title")
    abstract: str = Field(description="Paper abstract")
    similarity_score: float = Field(description="Similarity score to query")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional paper metadata"
    )


class RankedPaper(BaseModel):
    """Paper with ranking information."""

    paper: ArxivPaper = Field(description="The paper data")
    original_rank: int = Field(description="Original ranking by similarity")
    rerank_score: float | None = Field(
        default=None, description="Reranking score if reranking enabled"
    )
    final_rank: int = Field(description="Final ranking position")
    novelty_score: float = Field(description="Novelty score (inverse of similarity)")


class NoveltyAssessment(BaseModel):
    """Final novelty assessment of the research idea."""

    research_idea: str = Field(description="The research idea being assessed")
    total_papers_retrieved: int = Field(
        description="Number of papers retrieved from database"
    )
    reranking_enabled: bool = Field(description="Whether reranking was used")
    final_papers_count: int = Field(
        description="Number of papers used in final assessment"
    )
    final_novelty_score: float = Field(
        description="Overall novelty score (0-1, higher = more novel)"
    )
    confidence: float = Field(description="Confidence in the assessment (0-1)")
    top_similar_papers: list[RankedPaper] = Field(
        description="Most similar papers found"
    )
    assessment_summary: str = Field(
        description="LLM-generated summary of novelty assessment"
    )


class SharedStore(BaseModel):
    """Main shared store for the Idea Generation Flow with type safety."""

    # Configuration
    config: SearchConfig = Field(description="Search and validation configuration")

    # Input
    user_question: str = Field(description="Original user question")

    # Processing data
    search_queries: list[SearchQuery] = Field(
        default_factory=list, description="Generated search queries"
    )
    search_results: list[SearchResult] = Field(
        default_factory=list, description="Search results with summaries"
    )
    research_ideas: str | None = Field(
        default=None, description="Generated research ideas"
    )

    # Validation tracking
    validation_history: list[ValidationResult] = Field(
        default_factory=list, description="History of validation attempts"
    )
    current_cycle: int = Field(default=0, description="Current validation cycle number")

    # Output
    final_ideas: str | None = Field(
        default=None, description="Final approved research ideas"
    )
    completed: bool = Field(default=False, description="Whether the flow has completed")

    # RAG Flow data
    embedded_query: EmbeddedQuery | None = Field(
        default=None, description="Embedded research idea"
    )
    retrieved_papers: list[ArxivPaper] = Field(
        default_factory=list, description="Papers retrieved from Qdrant"
    )
    final_papers: list[RankedPaper] = Field(
        default_factory=list, description="Final ranked papers"
    )
    novelty_assessment: NoveltyAssessment | None = Field(
        default=None, description="Final novelty assessment"
    )
    rag_completed: bool = Field(
        default=False, description="Whether RAG flow has completed"
    )

    class Config:
        arbitrary_types_allowed = True

    @field_validator("user_question")
    @classmethod
    def user_question_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("User question cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for PocketFlow compatibility."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SharedStore":
        """Create SharedStore from dictionary."""
        return cls(**data)

    def get_current_validation_count(self) -> int:
        """Get the number of validation attempts made."""
        return len(self.validation_history)

    def is_max_cycles_reached(self) -> bool:
        """Check if maximum validation cycles have been reached."""
        return self.current_cycle >= self.config.max_cycles

    def add_validation_result(
        self, approved: bool, feedback: str, user_input: str | None = None
    ) -> None:
        """Add a new validation result to history."""
        self.current_cycle += 1
        validation_result = ValidationResult(
            approved=approved,
            feedback=feedback,
            user_input=user_input,
            cycle_number=self.current_cycle,
        )
        self.validation_history.append(validation_result)


def create_shared_store(
    user_question: str, config: SearchConfig | None = None
) -> SharedStore:
    """Factory function to create a properly initialized SharedStore."""
    if config is None:
        config = SearchConfig.from_env()

    return SharedStore(config=config, user_question=user_question)
