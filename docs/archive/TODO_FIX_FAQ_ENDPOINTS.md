# 🔧 TODO: Fix Remaining FAQ Endpoints for Superadmin

**Status:** Partially Fixed  
**Priority:** HIGH

---

## ✅ Already Fixed

- [x] `GET /api/v1/faq` - List FAQs (supports superadmin)
- [x] `GET /api/v1/faq/{id}` - Get FAQ by ID (supports superadmin)

---

## ⏳ Still Need Fix

### **Files to Update:** `app/api/routes_faq.py`

#### **1. POST /api/v1/faq** (Line ~172)
```python
# CURRENT (broken)
async def create_faq(
    body: FAQCreate,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,  # ❌ Remove this
):

# FIX
async def create_faq(
    body: FAQCreate,
    db: DBSession,
    user: CurrentUser,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
):
    # Add logic to determine tenant_id
    if user.role == "superadmin" and x_tenant_id:
        tenant_uuid = uuid.UUID(x_tenant_id)
    else:
        tenant_uuid = user.tenant_id
    
    # Use tenant_uuid instead of tenant.id
```

#### **2. PUT /api/v1/faq/{id}** (Line ~217)
```python
# Replace tenant: CurrentTenant with x_tenant_id header
# Add superadmin logic
```

#### **3. DELETE /api/v1/faq/{id}** (Line ~277)
```python
# Replace tenant: CurrentTenant with x_tenant_id header
# Add superadmin logic
```

#### **4. POST /api/v1/faq/templates/import** (Line ~307)
```python
# Replace tenant: CurrentTenant with x_tenant_id header
# Add superadmin logic
```

#### **5. GET /api/v1/faq/templates/categories** (Line ~423)
```python
# This endpoint doesn't need tenant context - can remove CurrentTenant dependency
```

---

## 📝 Quick Fix Script

Run this Python script to auto-fix:

```python
import re

with open('app/api/routes_faq.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace CurrentTenant with optional header
content = re.sub(
    r'(\nasync def \w+\([^)]*)tenant: CurrentTenant,',
    r'\1x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),',
    content
)

with open('app/api/routes_faq.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed! Now update function bodies to use x_tenant_id logic")
```

---

## ✅ Test After Fix

```bash
# Test as superadmin
curl http://localhost:8000/api/v1/faq \
  -H "Authorization: Bearer SUPERADMIN_TOKEN"

# Should return FAQs from ALL tenants
```

---

**Estimated Time:** 15 minutes  
**Difficulty:** Easy (copy-paste from list_documents example)
