# 🔬 Discovery Dojo

> **AI Research Assistant** - Transform your questions into comprehensive research plans
>
> Discovery Dojo is an intelligent research assistant that converts user questions into fully-developed research plans through a three-phase pipeline: idea generation, novelty assessment, and research planning.

## 🏗️ Architecture Overview

The system uses a **flow-based architecture** built on the PocketFlow framework, orchestrating multiple AI agents through structured workflows with shared state management.

### 📊 Information Flow

```
User Question → Idea Generation → RAG Novelty Assessment → Research Planning → Markdown Output
     ↓              ↓                     ↓                      ↓              ↓
  Web Search    Validation            ArXiv Papers        Interactive Config    File Save
  Parallel      Refinement           Vector Similarity    Plan Validation      Pretty Display
```

### 🔄 Three Main Flows

#### 1. **Idea Generation Flow** 🧠

```
Query → Parallel Search → Summarization → Idea Generation → Interactive Validation → Finalization
  ↓         (Tavily)          ↓               ↓                    ↑                    ↓
Multiple                 Web Results      Research Ideas     User Feedback      Final Ideas
Queries                  Processing       Generation         Loop Back          Storage
```

#### 2. **RAG Novelty Assessment Flow** 📚

```
Research Idea → Embedding → Retrieval → Reranking → Novelty Assessment
     ↓            ↓           ↓         (Optional)         ↓
  Text Input   Vector DB   Similar Papers   Top-N        Novelty Score
             (Qdrant)     from ArXiv      Selection      + Analysis
```

#### 3. **Research Planning Flow** 📋

```
User Config → Plan Generation → Validation → Finalization → Markdown Output
     ↓             ↓              ↓            ↓               ↓
Project Type    LLM Planning   User Review  Add Metadata   Beautiful File
Timeline        Structured     Refinement   Timestamps     + Console Display
Requirements    Output         Cycles       Context
```

## 🧱 Core Components

### 🎯 Nodes (Processing Units)

- **QueryGenerationNode**: Creates diverse search queries from user input
- **ParallelSearchNode**: Executes multiple web searches concurrently (Tavily API)
- **SummarizationNode**: Processes and summarizes search results
- **IdeaGenerationNode**: Generates research ideas using LLM
- **InteractiveValidationNode**: User feedback and refinement cycles
- **EmbeddingNode**: Vector embeddings for similarity search
- **RetrievalNode**: Qdrant vector database integration
- **RankingNode**: Optional reranking with local Qwen models
- **NoveltyAssessmentNode**: Comprehensive novelty scoring
- **PlanGenerationNode**: Structured research plan creation
- **PlanOutputNode**: Beautiful markdown generation and file output

## 🎨 Design Patterns

### 🤖 **Agent Pattern**

Each node is an autonomous agent with specific responsibilities, retry logic, and error handling.

### 🗺️ **Map-Reduce Pattern**

- **Map**: Parallel web searches across multiple queries
- **Reduce**: Consolidate results into coherent research ideas

### 🔄 **Workflow Pattern**

Sequential flow orchestration with conditional branching:

- Validation loops with user feedback
- Early termination on approval
- Maximum cycle limits

### 🔍 **RAG Pattern (Retrieval Augmented Generation)**

- **Retrieval**: Vector similarity search in ArXiv papers
- **Augmentation**: Context-aware novelty assessment
- **Generation**: Evidence-based analysis of proposed research idea against retrieved papers.

### 📊 **Pipeline Pattern**

Modular pipeline stages that can be run independently or combined:

```python
get_flow("idea_generation")    # Ideas only
get_flow("rag")               # Novelty only
get_flow("planning")          # Planning only
get_flow("complete_assistant") # Full pipeline
```

### 🏭 **Factory Pattern**

Dynamic flow creation based on user requirements:

```python
flow = get_flow(flow_type)
await flow.run_async(shared_dict)
```

## 🚀 Usage

### Quick Start

```bash
# Install dependencies
uv sync

# Set environment variables
export OPENAI_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export NEBIUS_API_KEY="your-key"

# Run the full research assistant
uv run src/main.py
```

> [!IMPORTANT]
> Ensure you have access to a valid Qdrant Databse with embedded ArXiV papers for the RAG flow to work.
>
> You will be asked to provide a url to the valid Qdrant database during the flow.

### Flow Options

- **Complete Assistant**: Full 3-phase pipeline (recommended)
- **Idea Generation**: Web research + idea creation only
- **RAG Assessment**: Novelty analysis against academic papers
- **Planning**: Convert ideas into actionable research plans
- **Legacy Q/A**: Flow for a simple single-llm-call question answering

## 🛠️ Technology Stack

- **Framework**: PocketFlow (async workflow orchestration)
- **LLM**: OpenAI GPT models with structured output
- **Search**: Tavily API for web research
- **Vector DB**: Qdrant for similarity search
- **Embeddings**: Qwen3-Embedding models
- **Reranking**: Optional Qwen3-Reranker models
- **Output**: Beautiful markdown with emojis and formatting

## 📁 Project Structure

```
src/
├── domain/          # Domain models and shared state
├── flows/           # Flow definitions and orchestration
├── nodes/           # Individual processing nodes
├── utils/           # LLM, search, and utility functions
├── adapters/        # External service integrations
└── main.py         # CLI interface and flow execution
```

---
