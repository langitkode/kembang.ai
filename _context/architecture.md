# System Architecture

High level architecture:
Client
↓
API Gateway
↓
FastAPI Backend
↓
Infrastructure

Clients:

- web widget
- whatsapp integration
- internal dashboard

FastAPI Modules:
auth
tenants
conversations
knowledge_base
rag
tools
monitoring
admin

Infrastructure:
PostgreSQL
Redis
Vector DB
LLM Providers
