# Console App Backend Proposal - Superadmin Monitoring Enhancement

**Date:** 2026-03-09  
**Priority:** HIGH  
**Status:** Proposed

---

## 📊 Executive Summary

Tenant Dashboard telah berkembang dengan fitur-fitur baru (FAQ, Products, API Keys, Playground). Console/Superadmin app saat ini **tidak memiliki visibility** terhadap fitur-fitur tersebut.

**Gap Analysis:**

| Feature | Tenant App | Console Monitoring | Status |
|---------|-----------|-------------------|--------|
| Knowledge Base | ✅ Full CRUD | ⚠️ View all docs (no per-tenant stats) | Partial |
| FAQ Management | ✅ Full CRUD | ❌ **NOTHING** | 🔴 Missing |
| Product Catalog | ✅ Full CRUD | ❌ **NOTHING** | 🔴 Missing |
| API Keys | ✅ Generate/manage | ❌ **NOTHING** | 🔴 Missing |
| Playground | ✅ Test chatbot | ❌ **NOTHING** | 🟡 Optional |
| Conversations | ✅ View their chats | ✅ View all chats (no analytics) | Partial |
| Team Members | ✅ Manage team | ✅ Global users (no per-tenant) | Partial |

---

## 🎯 Priority 1: Critical Monitoring (🔴 HIGH)

### **1. FAQ Overview & Analytics**

**Why:** Tenant bisa buat FAQ sendiri, superadmin perlu monitor:
- Total FAQ per tenant
- FAQ categories yang paling banyak digunakan
- FAQ yang sering di-trigger
- Ability to toggle global FAQs

**New Backend Endpoints:**
```python
# List all FAQs across tenants with pagination & filters
GET /api/v1/superadmin/faq
  - Query params: tenant_id, category, is_active, page, page_size
  - Response: { faqs: [...], total: number, page: number }

# FAQ statistics
GET /api/v1/superadmin/faq/stats
  - Response: {
      total_faqs: number,
      by_category: [{ category: string, count: number }],
      by_tenant: [{ tenant_id: string, tenant_name: string, count: number }],
      top_faqs: [{ id: string, category: string, usage_count: number }]
    }

# FAQs for specific tenant
GET /api/v1/superadmin/faq/{tenant_id}
  - Response: { faqs: [...], tenant_info: {...} }
```

**Console Page:** `/superadmin/faq`
- List all FAQs dengan filter by tenant, category, status
- Stats cards: total FAQs, top categories, active tenants
- Toggle active/inactive per FAQ
- View tenant details

---

### **2. Product Catalog Overview**

**Why:** Tenant manage products, superadmin perlu visibility:
- Total products per tenant
- Product categories distribution
- Products with low stock (inventory monitoring)
- Pricing overview

**New Backend Endpoints:**
```python
# List all products with filters
GET /api/v1/superadmin/products
  - Query params: tenant_id, category, min_price, max_price, low_stock_only, page, page_size
  - Response: { products: [...], total: number, page: number }

# Product statistics
GET /api/v1/superadmin/products/stats
  - Response: {
      total_products: number,
      by_category: [{ category: string, count: number }],
      by_tenant: [{ tenant_id: string, count: number }],
      low_stock_count: number,
      avg_price: number
    }

# Low stock products (below threshold)
GET /api/v1/superadmin/products/low-stock
  - Query params: threshold (default: 10)
  - Response: { products: [...], threshold: number }

# Products for specific tenant
GET /api/v1/superadmin/products/{tenant_id}
  - Response: { products: [...], tenant_info: {...} }
```

**Console Page:** `/superadmin/products`
- Product catalog view dengan filter tenant, category, price range
- Low stock alerts (red highlight for products < 10 units)
- Category distribution chart
- Export to CSV button

---

### **3. API Key Usage & Management**

**Why:** Tenant generate API keys, superadmin perlu track:
- Which tenants have active API keys
- API key usage statistics (request count)
- Revoke keys if needed (security)

**New Backend Endpoints:**
```python
# List all API keys
GET /api/v1/superadmin/api-keys
  - Query params: tenant_id, is_active, page, page_size
  - Response: { 
      api_keys: [{
        id: string,
        tenant_id: string,
        tenant_name: string,
        key_masked: "kw_live_••••xxxx",
        created_at: string,
        is_active: boolean,
        last_used_at: string | null
      }],
      total: number
    }

# API key usage statistics
GET /api/v1/superadmin/api-keys/usage
  - Query params: tenant_id, date_from, date_to
  - Response: {
      total_requests: number,
      by_tenant: [{ tenant_id: string, requests: number }],
      by_day: [{ date: string, requests: number }]
    }

# Revoke specific API key
POST /api/v1/superadmin/api-keys/{id}/revoke
  - Response: { success: true, message: "API key revoked" }
```

**Console Page:** `/superadmin/api-keys`
- Table: Tenant | API Key (masked) | Created | Last Used | Status | Actions
- Usage statistics chart (requests per day)
- Revoke button with confirmation dialog
- Filter by active/inactive

---

## 📋 Priority 2: Enhanced Monitoring (🟡 MEDIUM)

### **4. Tenant Activity Dashboard**

**Why:** Monitor tenant engagement:
- Last login per tenant
- Feature usage (KB uploads, FAQ updates, product updates)
- Active vs inactive tenants
- Resource usage per tenant

**New Backend Endpoints:**
```python
# Tenant activity log
GET /api/v1/superadmin/tenants/activity
  - Query params: tenant_id, action_type, date_from, date_to, page, page_size
  - Response: {
      activities: [{
        id: string,
        tenant_id: string,
        tenant_name: string,
        action: string,  # "kb_upload", "faq_create", "product_update", "login"
        details: object,
        timestamp: string
      }],
      total: number
    }

# Detailed tenant stats
GET /api/v1/superadmin/tenants/{id}/stats
  - Response: {
      tenant_info: {...},
      documents_count: number,
      faqs_count: number,
      products_count: number,
      conversations_count: number,
      api_requests: number,
      last_login: string,
      created_at: string
    }
```

**Console Enhancement:** Update `/tenants` page
- Add "Last Active" column
- Activity timeline per tenant (modal on click)
- Feature usage breakdown (pie chart)
- Export tenant report button

---

### **5. Conversation Analytics**

**Why:** Current conversation view hanya list, perlu analytics:
- Conversations per day/week/month
- Average response time
- Most common intents (FAQ vs RAG vs Smalltalk)
- User satisfaction metrics (if implemented later)

**New Backend Endpoints:**
```python
# Conversation analytics
GET /api/v1/superadmin/conversations/analytics
  - Query params: date_from, date_to, tenant_id
  - Response: {
      total_conversations: number,
      by_day: [{ date: string, count: number }],
      by_tenant: [{ tenant_id: string, count: number }],
      avg_messages_per_conversation: number
    }

# Intent distribution
GET /api/v1/superadmin/conversations/intents
  - Query params: date_from, date_to
  - Response: {
      by_intent: [{ intent: string, count: number, percentage: number }],
      top_questions: [{ question: string, count: number }]
    }

# Conversation metrics
GET /api/v1/superadmin/conversations/metrics
  - Query params: date_from, date_to
  - Response: {
      avg_response_time_ms: number,
      avg_tokens_per_response: number,
      rag_cache_hit_rate: number,
      faq_match_rate: number
    }
```

**Console Enhancement:** Update `/chat` page
- Add "Analytics" tab
- Charts: conversations over time, intent distribution pie chart
- Metrics cards: avg response time, FAQ match rate, RAG cache hit rate
- Export analytics button (CSV/PDF)

---

### **6. Playground Sessions (Optional)**

**Why:** Monitor testing activity:
- Who's using playground
- Most tested questions
- Test success rate

**Backend Endpoints:**
```python
# Playground usage
GET /api/v1/superadmin/playground/sessions
  - Query params: tenant_id, date_from, date_to
  - Response: {
      sessions: [{
        user_email: string,
        tenant_id: string,
        messages_count: number,
        started_at: string,
        last_active: string
      }],
      total: number
    }
```

**Console Page:** Optional, bisa integrate ke `/chat` atau `/tenants`

---

## 🎨 Priority 3: System Health (🟢 LOW)

### **7. Enhanced Infrastructure Monitoring**

**Current:** `/infra` sudah ada dengan health check

**Enhancement:**
- Per-tenant resource usage
- RAG performance metrics
- Embedding generation stats
- Vector database health

**Backend Endpoints:**
```python
# Per-tenant metrics
GET /api/v1/superadmin/metrics/per-tenant
  - Response: {
      by_tenant: [{
        tenant_id: string,
        documents: number,
        vectors: number,
        api_requests: number,
        storage_mb: number
      }]
    }

# RAG pipeline metrics
GET /api/v1/superadmin/metrics/rag
  - Response: {
      avg_retrieval_time_ms: number,
      avg_generation_time_ms: number,
      cache_hit_rate: number,
      total_queries: number
    }

# Embedding stats
GET /api/v1/superadmin/metrics/embeddings
  - Response: {
      total_vectors: number,
      model: string,
      dimensions: number,
      avg_vector_size: number
    }
```

**Console Enhancement:** Update `/infra` page
- Add per-tenant resource usage table
- RAG performance chart
- Vector database stats

---

## 📦 Summary: Backend Endpoints Required

### **Total: 15 New Endpoints**

#### FAQ Management (3 endpoints)
```
GET /api/v1/superadmin/faq
GET /api/v1/superadmin/faq/stats
GET /api/v1/superadmin/faq/{tenant_id}
```

#### Product Catalog (4 endpoints)
```
GET /api/v1/superadmin/products
GET /api/v1/superadmin/products/stats
GET /api/v1/superadmin/products/low-stock
GET /api/v1/superadmin/products/{tenant_id}
```

#### API Keys (3 endpoints)
```
GET /api/v1/superadmin/api-keys
GET /api/v1/superadmin/api-keys/usage
POST /api/v1/superadmin/api-keys/{id}/revoke
```

#### Tenant Activity (2 endpoints)
```
GET /api/v1/superadmin/tenants/activity
GET /api/v1/superadmin/tenants/{id}/stats
```

#### Conversation Analytics (3 endpoints)
```
GET /api/v1/superadmin/conversations/analytics
GET /api/v1/superadmin/conversations/intents
GET /api/v1/superadmin/conversations/metrics
```

#### Enhanced Metrics (3 endpoints)
```
GET /api/v1/superadmin/metrics/per-tenant
GET /api/v1/superadmin/metrics/rag
GET /api/v1/superadmin/metrics/embeddings
```

---

## 🖥️ Console Pages to Create/Update

| Page | Path | Priority | Status |
|------|------|----------|--------|
| **FAQ Management** | `/superadmin/faq` | 🔴 HIGH | New |
| **Product Catalog** | `/superadmin/products` | 🔴 HIGH | New |
| **API Keys** | `/superadmin/api-keys` | 🔴 HIGH | New |
| **Tenant Activity** | `/tenants/[id]/activity` | 🟡 MEDIUM | Enhancement |
| **Analytics** | `/chat/analytics` | 🟡 MEDIUM | Enhancement |
| **Infrastructure** | `/infra` | 🟢 LOW | Enhancement |

---

## ⏱️ Estimated Implementation Time

### **Phase 1: Priority 1 (🔴 HIGH)**
- Backend (10 endpoints): 4-6 hours
- Frontend Console (3 pages): 3-4 hours
- Testing: 1-2 hours
- **Total: 8-12 hours**

### **Phase 2: Priority 2 (🟡 MEDIUM)**
- Backend (5 endpoints): 3-4 hours
- Frontend Console (2 enhancements): 2-3 hours
- Testing: 1 hour
- **Total: 6-8 hours**

### **Phase 3: Priority 3 (🟢 LOW)**
- Backend (3 endpoints): 2-3 hours
- Frontend Console (1 enhancement): 1-2 hours
- Testing: 1 hour
- **Total: 4-6 hours**

---

## 🎯 Recommended Approach

**Start with Phase 1 (Priority 1 - HIGH):**

1. **FAQ Overview** - Most critical, tenants already using extensively
2. **Product Catalog** - Visibility into tenant product management
3. **API Keys** - Security & access control

**Benefits:**
- ✅ Complete visibility into tenant features
- ✅ Security monitoring (API keys)
- ✅ Inventory alerts (low stock products)
- ✅ Usage analytics (FAQ stats)

---

## 📞 Next Steps

1. **Review this proposal** with backend team
2. **Prioritize endpoints** based on backend capacity
3. **Start with Phase 1** implementation
4. **Test thoroughly** before deployment
5. **Monitor usage** and gather feedback from superadmin users

---

## 📝 Notes

- All endpoints should follow existing authentication/authorization patterns
- Superadmin-only access (role-based)
- Pagination required for list endpoints
- Rate limiting should be applied
- Logging & audit trail for all superadmin actions

---

**Questions?** Reach out to frontend team for clarification on UI/UX requirements.

**Status:** ⚠️ **AWAITING BACKEND REVIEW**

---
