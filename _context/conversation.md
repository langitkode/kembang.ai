# Stateful Conversation System

Conversation stored in database.
Conversation flow:
user message
↓
load conversation history
↓
compress history
↓
retrieve context
↓
generate response
↓
store response

History management:
last_k_messages = 6
older messages summarized into:
conversation_summary
stored in conversations table.
