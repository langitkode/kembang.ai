# Project Overview

Project name: Agency-first Chatbot SaaS
Target: UMKM customer service automation

Goal:
Build a stateful AI chatbot platform that agencies can deploy for multiple SME clients.

Key characteristics:

- multi-tenant SaaS ready
- agency-first architecture
- hybrid RAG pipeline
- cost-efficient inference
- hallucination minimized
- monitoring per tenant
- stateful conversation

Backend stack:

- FastAPI
- PostgreSQL
- Redis
- Vector DB (Qdrant / pgvector)
- LLM APIs (OpenAI / Mistral / Anthropic)

Deployment (initial):

- Railway
- HuggingFace Spaces (demo)

Architecture style:

- monolith backend
- modular internal architecture

Key backend modules:

1. Auth & Tenant Management
2. Conversation Manager
3. Knowledge Base
4. RAG Pipeline
5. Tool System
6. Monitoring & Usage Tracking
7. Admin API

Non-goals (v1):

- distributed microservices
- complex agent orchestration
- realtime streaming pipelines

Design priorities:

1. simplicity
2. low cost inference
3. easy deployment
4. agency scalability
