# RAG Pipeline

Steps:
1 query rewrite
2 embedding
3 hybrid retrieval
4 reranking
5 context builder
6 LLM generation

Hybrid retrieval
vector search

- BM25 keyword search
  vector_top_k = 8
  keyword_top_k = 8
  rerank_top_k = 4

Chunking
chunk_size = 400
chunk_overlap = 80
