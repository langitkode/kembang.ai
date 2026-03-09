# Database & Endpoint Analysis - Deep Dive

**Date:** 2026-03-09  
**Analysis Type:** Root Cause Analysis  
**Status:** ✅ ANALYSIS COMPLETE

---

## 🔍 PROBLEM IDENTIFICATION

### **User's Concern:**
> "FAQ Overview, product catalog apakah terpisah dari sistem monitoring atau tabel tenant_id?"

### **Analysis Result:**
✅ **Structure is CORRECT** - Tables are properly separated with clear tenant_id relationships

---

## 📊 DATABASE STRUCTURE VERIFICATION

### **✅ Table Separation:**

```sql
-- FAQ Table (SEPARATE) ✅
tenant_faqs
├── id (PK)
├── tenant_id (FK → tenants.id) INDEXED ✅
├── category
├── question_patterns (ARRAY)
├── answer
├── confidence
├── is_active
└── timestamps

-- Product Table (SEPARATE) ✅
products
├── id (PK)
├── tenant_id (FK → tenants.id) INDEXED ✅
├── sku
├── name
├── category
├── price
├── stock_quantity
└── timestamps

-- Knowledge Base Table (SEPARATE) ✅
knowledge_bases
├── id (PK)
├── tenant_id (FK → tenants.id) INDEXED ✅
└── name

-- Documents Table (SEPARATE) ✅
documents
├── id (PK)
├── kb_id (FK → knowledge_bases.id)
└── file_name
```

**Status:** ✅ **ALL TABLES PROPERLY SEPARATED**

---

## 🔗 RELATIONSHIP ANALYSIS

### **✅ Clear Relationships:**

```
tenants (id: UUID)
├── 1:N → tenant_faqs (tenant_id: UUID) ✅
├── 1:N → products (tenant_id: UUID) ✅
├── 1:N → knowledge_bases (tenant_id: UUID) ✅
└── 1:N → users (tenant_id: UUID) ✅
```

**Foreign Key Constraints:**
```python
# TenantFAQ
tenant_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("tenants.id", ondelete="CASCADE"),  # ✅ CASCADE
    index=True,  # ✅ INDEXED
    nullable=False,  # ✅ NOT NULL
)

# Product
tenant_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("tenants.id", ondelete="CASCADE"),  # ✅ CASCADE
    index=True,  # ✅ INDEXED
    nullable=False,  # ✅ NOT NULL
)
```

**Status:** ✅ **RELATIONSHIPS ARE CLEAR AND PROPER**

---

## 🐛 POTENTIAL ISSUES FOUND

### **Issue #1: Inconsistent Tenant Filtering** ⚠️

**FAQ Endpoint:**
```python
@router.get("")
async def list_faqs(
    user: CurrentUser,
    x_tenant_id: Optional[str] = Header(None),  # ⚠️ OPTIONAL
    ...
):
    if user.role == "superadmin":
        if x_tenant_id:
            tenant_uuid = uuid.UUID(x_tenant_id)
        else:
            tenant_uuid = None  # ⚠️ NO FILTER - Returns ALL FAQs
    else:
        tenant_uuid = user.tenant_id
```

**Product Endpoint:**
```python
@router.get("")
async def list_products(
    user: CurrentUser,
    tenant: CurrentTenant,  # ✅ ALWAYS FILTERED
    ...
):
    query = select(Product).where(
        Product.tenant_id == tenant.id,  # ✅ FORCED FILTER
    )
```

**Problem:**
- ❌ FAQ endpoint allows `tenant_uuid = None` for superadmin
- ✅ Product endpoint ALWAYS filters by tenant
- ⚠️ **INCONSISTENT behavior**

**Impact:**
- Superadmin can get ALL FAQs from ALL tenants (might be intended)
- But could cause confusion if expecting tenant-specific data

---

### **Issue #2: Missing Dependency Injection** ⚠️

**FAQ Endpoint:**
```python
# Uses manual tenant resolution
async def list_faqs(
    user: CurrentUser,
    x_tenant_id: Optional[str] = Header(None),
    ...
):
    # Manual logic to determine tenant
    if user.role == "superadmin" and x_tenant_id:
        tenant_uuid = uuid.UUID(x_tenant_id)
    else:
        tenant_uuid = user.tenant_id
```

**Product Endpoint:**
```python
# Uses dependency injection
async def list_products(
    user: CurrentUser,
    tenant: CurrentTenant,  # ✅ Auto-resolved
    ...
):
```

**Problem:**
- ❌ FAQ has manual tenant resolution logic
- ✅ Product uses `CurrentTenant` dependency
- ⚠️ **INCONSISTENT pattern**

**Risk:**
- Manual logic could have bugs
- Harder to maintain
- Different behavior between endpoints

---

### **Issue #3: Stats Endpoint Confusion** ⚠️

**FAQ Stats:**
```python
@router.get("/stats", response_model=FAQStatsResponse, tags=["superadmin"])
async def get_faq_stats(
    db: DBSession,
    user: CurrentUser = require_superadmin,  # ✅ Superadmin only
):
    # Returns stats across ALL tenants
    total_result = await db.execute(select(func.count(TenantFAQ.id)))
    # ...
```

**Product Stats:**
```python
@router.get("/stats", response_model=ProductStatsResponse, tags=["superadmin"])
async def get_product_stats(
    db: DBSession,
    user: CurrentUser = require_superadmin,  # ✅ Superadmin only
):
    # Returns stats across ALL tenants
    total_result = await db.execute(select(func.count(Product.id)))
    # ...
```

**Status:** ✅ **CONSISTENT** - Both are superadmin-only, return global stats

---

### **Issue #4: Data Seeding Inconsistency** ⚠️

**FAQ Seeding:**
```python
# seed_faqs.py - Seeds for ALL tenants
for tenant in tenants:
    # Check if FAQ already exists
    existing = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.tenant_id == tenant.id,
            TenantFAQ.category == category_id
        )
    )
    if not existing.scalar_one_or_none():
        # Create FAQ
```

**Product Seeding:**
```python
# Manual upload via API
# OR seed_products.py (if exists)
```

**Problem:**
- ✅ FAQ has automated seeding script
- ⚠️ Products rely on manual upload or separate script
- ⚠️ **Could lead to missing data**

---

## 🎯 ROOT CAUSE ANALYSIS

### **If User Experienced Issues:**

#### **Scenario 1: "FAQ tidak muncul"**

**Possible Causes:**
1. ❌ FAQ not seeded for that tenant
2. ❌ Wrong tenant_id being used
3. ❌ Superadmin viewing without tenant filter
4. ❌ FAQ is_active = False

**Debug Steps:**
```sql
-- Check if FAQs exist
SELECT tenant_id, category, COUNT(*) 
FROM tenant_faqs 
GROUP BY tenant_id, category;

-- Check specific tenant
SELECT * FROM tenant_faqs 
WHERE tenant_id = 'YOUR_TENANT_ID';
```

---

#### **Scenario 2: "Products tidak muncul"**

**Possible Causes:**
1. ❌ Products not uploaded for that tenant
2. ❌ Products is_active = False
3. ❌ Wrong tenant_id in query
4. ❌ Filter too restrictive (category, price, etc.)

**Debug Steps:**
```sql
-- Check if products exist
SELECT tenant_id, COUNT(*) 
FROM products 
GROUP BY tenant_id;

-- Check specific tenant
SELECT * FROM products 
WHERE tenant_id = 'YOUR_TENANT_ID';
```

---

#### **Scenario 3: "Data tercampur antar tenant"**

**Possible Causes:**
1. ❌ Query missing `WHERE tenant_id = ?`
2. ❌ Superadmin viewing all data without filter
3. ❌ Bug in tenant resolution logic

**Debug Steps:**
```python
# Check endpoint code
# Look for queries WITHOUT tenant_id filter
SELECT * FROM tenant_faqs WHERE tenant_id IS NULL;  # Should be 0
SELECT * FROM products WHERE tenant_id IS NULL;     # Should be 0
```

---

## ✅ VERIFICATION CHECKLIST

### **Database Structure:**
- [x] FAQ table exists with tenant_id ✅
- [x] Product table exists with tenant_id ✅
- [x] Foreign keys properly configured ✅
- [x] Indexes on tenant_id ✅
- [x] Cascade delete configured ✅

### **Endpoint Logic:**
- [x] FAQ endpoint filters by tenant (mostly) ⚠️
- [x] Product endpoint filters by tenant ✅
- [x] Superadmin can view all (intended) ✅
- [x] Tenant admin sees only their data ✅

### **Data Integrity:**
- [ ] Check for orphaned records (no tenant_id)
- [ ] Check for duplicate seeding
- [ ] Check is_active flags
- [ ] Check category consistency

---

## 🔧 RECOMMENDATIONS

### **Priority 1: Standardize Tenant Filtering** 🔴

**Current:**
```python
# FAQ - Manual resolution
if user.role == "superadmin" and x_tenant_id:
    tenant_uuid = uuid.UUID(x_tenant_id)
else:
    tenant_uuid = user.tenant_id
```

**Recommended:**
```python
# Use CurrentTenant dependency consistently
async def list_faqs(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,  # ✅ Use dependency
    ...
):
    query = select(TenantFAQ).where(TenantFAQ.tenant_id == tenant.id)
```

**Benefit:**
- ✅ Consistent behavior
- ✅ Less error-prone
- ✅ Easier to maintain

---

### **Priority 2: Add Data Validation** 🟡

**Add to endpoints:**
```python
@router.get("")
async def list_faqs(...):
    # Validate tenant has data
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    if total == 0:
        logger.warning("Tenant %s has no FAQs", tenant.id)
    
    # ... rest of logic
```

**Benefit:**
- ✅ Better debugging
- ✅ Clear error messages
- ✅ Easier troubleshooting

---

### **Priority 3: Add Database Constraints** 🟡

**Add unique constraint:**
```python
# Prevent duplicate FAQ per tenant per category
__table_args__ = (
    UniqueConstraint('tenant_id', 'category', name='uq_tenant_category'),
)
```

**Benefit:**
- ✅ Prevents duplicate seeding
- ✅ Data integrity
- ✅ Clear error on duplicates

---

## 📊 DEBUGGING GUIDE

### **If FAQ Not Showing:**

```python
# 1. Check database
SELECT COUNT(*) FROM tenant_faqs WHERE tenant_id = 'YOUR_ID';

# 2. Check endpoint
curl http://localhost:8000/api/v1/faq \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Check logs
# Look for: "Tenant admin viewing FAQs for tenant: {uuid}"

# 4. Check response
{
  "faqs": [],  # ← Empty?
  "total": 0
}
```

### **If Products Not Showing:**

```python
# 1. Check database
SELECT COUNT(*) FROM products WHERE tenant_id = 'YOUR_ID';

# 2. Check endpoint
curl http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Check filters
# Remove all query params: ?category=...&min_price=...

# 4. Check response
{
  "products": [],  # ← Empty?
  "total": 0
}
```

---

## 🎯 CONCLUSION

### **Structure:** ✅ **CORRECT**
- Tables properly separated
- Relationships clear
- Indexes in place

### **Implementation:** ⚠️ **MOSTLY CORRECT**
- Minor inconsistencies in tenant filtering
- Some manual logic that could be automated
- No critical bugs found

### **Data:** ❓ **NEEDS VERIFICATION**
- Check if data is seeded properly
- Check for orphaned records
- Check is_active flags

---

## 📝 NEXT STEPS

1. **Verify data exists:**
   ```sql
   SELECT 'FAQs' as type, COUNT(*) FROM tenant_faqs
   UNION ALL
   SELECT 'Products', COUNT(*) FROM products;
   ```

2. **Test endpoints:**
   ```bash
   curl /api/v1/faq
   curl /api/v1/products
   ```

3. **Check logs for errors**

4. **If still issues:**
   - Share specific error message
   - Share endpoint being called
   - Share tenant_id being used

---

**Status:** ✅ **ANALYSIS COMPLETE**  
**Structure:** ✅ **CORRECT**  
**Action:** **VERIFY DATA & TEST ENDPOINTS**

---

**Last Updated:** 2026-03-09  
**Analyzed By:** Backend Team
