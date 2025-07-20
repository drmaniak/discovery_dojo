import os
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchConfig(BaseModel):
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
    def feedback_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Validation feedback cannot be empty")
        return v.strip()


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

    class Config:
        arbitrary_types_allowed = True

    @field_validator("user_question")
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
