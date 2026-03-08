# Tool System

Tools allow chatbot to perform actions.

Examples:
product_lookup
check_order_status
create_support_ticket

Tool architecture:
LLM decides tool
↓
tool router
↓
execute tool
↓
return result
↓
LLM final response
