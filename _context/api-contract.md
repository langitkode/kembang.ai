# API Contracts

All endpoints are tenant-aware.
Base path:
/api/v1
Authentication:
JWT Bearer Token

Headers:
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>

# Auth

POST /auth/login
request
{
"email": "user@email.com",
"password": "string"
}

response
{
"access_token": "jwt_token"
}

# Chat

POST /chat/message
request
{
"conversation_id": "optional",
"message": "string"
}

response
{
"conversation_id": "uuid",
"reply": "assistant response",
"sources": []
}
GET /chat/history/{conversation_id}
response
{
"messages": [
{
"role": "user",
"content": "hello"
},
{
"role": "assistant",
"content": "hi"
}
]
}

# Knowledge Base

POST /kb/upload
multipart form
file
response
{
"document_id": "uuid"
}

GET /kb/documents
response
[
{
"id": "uuid",
"name": "faq.pdf"
}
]

# Admin

GET /admin/usage
response
{
"requests": 1000,
"tokens": 450000,
"estimated_cost": 3.2
}
