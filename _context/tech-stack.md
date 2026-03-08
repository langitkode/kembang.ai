# Technology Stack

Backend framework
FastAPI

Language
Python 3.11+

Database
PostgreSQL

Vector database
Qdrant or pgvector

Cache
Redis

ORM
SQLAlchemy / SQLModel

Background jobs
RQ or Celery

Embeddings
text-embedding-3-small
bge-small

LLM models

default:
gpt-4o-mini

fallback:
mistral-small

reranker
bge-reranker

Monitoring

OpenTelemetry
custom usage logger

Deployment

Railway
Docker
