# Database Schema

Multi-tenant schema

tables:
tenants
users
projects
knowledge_bases
documents
chunks
conversations
messages
usage_logs

tenants:
id
name
plan
created_at

users:
id
tenant_id
email
password_hash
role

knowledge_bases:
id
tenant_id
name

documents:
id
kb_id
file_name
source_type

chunks:
id
document_id
content
embedding
metadata

conversations:
id
tenant_id
user_identifier
created_at

messages:
id
conversation_id
role
content
tokens_used
created_at

usage_logs:
id
tenant_id
model
input_tokens
output_tokens
cost_estimate
timestamp
