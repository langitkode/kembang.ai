# RAG Implementation

Goal:
low hallucination
low cost
fast response

Pipeline:

User Query
↓
Query rewrite
↓
Embedding
↓
Hybrid retrieval
↓
Rerank
↓
Context build
↓
LLM response

# Query Rewrite

Purpose
improve retrieval accuracy.
Example
User:
"berapa harga produk ini?"
Rewrite:
"price information of product"

# Hybrid Retrieval

vector search

- keyword search
  Implementation
  vector_results = vector_search(query_embedding)
  keyword_results = bm25_search(query_text)
  combined = merge_results(vector_results, keyword_results)

# Reranking

Use cross encoder.
Input:
query + candidate chunk
Output:
relevance score.
Select top 4 chunks.

# Context Builder

Combine chunks.
Example

Context:
chunk 1
chunk 2
chunk 3
chunk 4

Limit
max_tokens_context = 1500

# Prompt Template

System
"You are a customer service assistant for SMEs."
Rules

- answer using context
- do not hallucinate
- if unknown say "information unavailable"

# LLM Generation

model routing
simple question → small model
complex question → stronger model

# Post Processing

Extract sources
Format response
Return

{
answer: "...",
sources: [...]
}
