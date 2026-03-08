# 🚀 Hugging Face Deployment Checklist

## ✅ Pre-Deployment Checklist

### **1. Environment Variables**

Create `.env` file with production values:

```env
# Database (Update with your Neon/PostgreSQL URL)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/kembang_db

# LLM Providers
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=sk-optional

# Security
JWT_SECRET=your_super_secret_key_change_this
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60

# App Settings
APP_ENV=production
DEBUG=False
CORS_ORIGINS=["https://your-space.hf.space"]

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0
```

---

### **2. Database Setup**

```bash
# Run migrations
uv run alembic upgrade head

# Verify tables created
uv run python -c "from app.db.session import async_session_factory; import asyncio; asyncio.run(async_session_factory())"
```

---

### **3. Seed Sample Data (Optional)**

```bash
# Seed products
uv run python seed_products.py

# Seed superadmin (optional)
uv run python seed_superadmin.py admin@kembang.ai password123
```

---

### **4. Test Locally**

```bash
# Start server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test health endpoint
curl http://localhost:8000/health

# Test API docs
open http://localhost:8000/docs
```

---

### **5. Docker Configuration**

**Check `Dockerfile`:**
- ✅ Python 3.11 slim
- ✅ uv pre-installed
- ✅ Dependencies installed
- ✅ SentenceTransformer model pre-downloaded
- ✅ Non-root user for security
- ✅ Port 7860 exposed (HF requirement)

**Check `docker-compose.yml`:**
- ✅ PostgreSQL with pgvector
- ✅ Redis for caching
- ✅ App depends on db and redis
- ✅ Health checks configured

---

### **6. Hugging Face Space Setup**

1. **Create new Space** at https://huggingface.co/spaces
2. **Select Docker** as SDK
3. **Configure hardware:**
   - CPU Basic (free tier OK)
   - 16GB RAM minimum (for embeddings model)
4. **Add environment variables** in Space settings:
   - `DATABASE_URL`
   - `GROQ_API_KEY`
   - `JWT_SECRET`
   - Other vars from `.env`

---

### **7. Post-Deployment Verification**

After deployment, test these endpoints:

```bash
# Health check
curl https://your-space.hf.space/health

# API docs
open https://your-space.hf.space/docs

# Login test
curl -X POST https://your-space.hf.space/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@kembang.ai", "password": "test123"}'
```

---

## 🐛 Troubleshooting

### **Issue: Database connection error**

```
Solution: Check DATABASE_URL format
- Use postgresql+asyncpg:// prefix
- Ensure SSL mode if required by provider
```

### **Issue: Model loading timeout**

```
Solution: Increase timeout in Dockerfile
- Pre-download models: RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### **Issue: CORS error**

```
Solution: Update CORS_ORIGINS in .env
- Add your HF Space URL: https://your-space.hf.space
```

### **Issue: Out of memory**

```
Solution: Upgrade Space hardware
- Embeddings model needs ~2GB RAM
- Recommend 16GB minimum for production
```

---

## 📊 Monitoring

### **Health Endpoints**

- `GET /health` - Basic health check
- `GET /metrics` - Request metrics

### **Logs**

View logs in Hugging Face Space dashboard:
- Click "Logs" tab
- Filter by ERROR for issues

---

## 🎯 Production Best Practices

1. **Enable auto-scaling** if expecting high traffic
2. **Set up database backups** (Neon does this automatically)
3. **Monitor API usage** via `/metrics` endpoint
4. **Rotate JWT_SECRET** periodically
5. **Use environment-specific configs** (dev/staging/prod)

---

## ✅ Deployment Complete!

When all checks pass, your backend is ready! 🎉

**Next steps:**
- Share Space URL with team
- Test with frontend app
- Monitor usage and errors
- Iterate based on feedback
