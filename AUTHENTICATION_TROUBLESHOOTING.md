# Authentication Troubleshooting Guide

## Quick Reference

**Credentials**:
- Username: `Nisarg13031`
- Password: `123456789`
- Email: `nisarg13031@nisarghunter.com`

**Backend**: `http://localhost:8000`
**Frontend**: `http://localhost:5173`

---

## Common Issues & Solutions

### Issue 1: "Authentication failed. Check credentials."
**Cause**: Wrong username/password or database user not found

**Solution**:
```powershell
# Verify user exists
.venv\Scripts\python.exe
>>> from backend.database.session import AsyncSessionLocal
>>> from backend.services.auth_service import AuthService
>>> import asyncio
>>> 
>>> async def check_user():
...     async with AsyncSessionLocal() as db:
...         svc = AuthService(db)
...         user = await svc.get_by_username("Nisarg13031")
...         print(f"User found: {user}")
...         if user:
...             print(f"  ID: {user.id}")
...             print(f"  Email: {user.email}")
...             print(f"  Active: {user.is_active}")
... 
>>> asyncio.run(check_user())
```

### Issue 2: Backend not responding (http://localhost:8000 connection refused)

**Solution**:
```powershell
# Check if backend is running
netstat -tuln | findstr 8000

# If not running, start it
.venv\Scripts\python.exe -m uvicorn backend.main:create_app --host 0.0.0.0 --port 8000

# If port is in use, kill the process
$Process = Get-Process | Where-Object { $_.ProcessName -like "*python*" }
Stop-Process -Id $Process.Id -Force
```

### Issue 3: Frontend cannot reach backend (CORS error)

**Check**: `vite.config.ts` proxy configuration
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false,
  }
}
```

**Solution**:
- Ensure backend CORS allows `*` (for development)
- Check backend `.env` has correct settings
- Restart both frontend and backend

### Issue 4: Database errors (table not found)

**Solution**: Reinitialize database
```powershell
# Delete old database
Remove-Item nisarghunter.db -ErrorAction SilentlyContinue

# Recreate and seed
.venv\Scripts\python.exe -c "
import asyncio
from backend.database.session import init_db
from backend.services.auth_service import AuthService
from backend.database.session import AsyncSessionLocal

async def setup():
    await init_db()
    async with AsyncSessionLocal() as db:
        svc = AuthService(db)
        user = await svc.register_user(
            username='Nisarg13031',
            email='nisarg13031@nisarghunter.com',
            password='123456789'
        )
        print(f'User created: {user.username}')

asyncio.run(setup())
"
```

### Issue 5: Token expired / 401 Unauthorized

**Expected**: JWT tokens last 8 hours
**Solution**: Login again to get new token

---

## Development Commands

### Clear Cache & Rebuild
```powershell
# Backend
Remove-Item -Recurse .venv
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# Frontend
cd webapp
Remove-Item -Recurse node_modules
npm install
```

### Check Logs

**Backend logs** (in same terminal as running server)
- Shows request logs, errors, SQL queries

**Frontend logs** (in browser console)
- Press `F12` to open DevTools
- Check Console and Network tabs

### Test API Endpoint

```powershell
# Login
$body = @{
    username = "Nisarg13031"
    password = "123456789"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
  -Method Post -ContentType "application/json" -Body $body

# Get current user (with token)
$token = "your_access_token_here"
Invoke-RestMethod -Uri "http://localhost:8000/api/auth/me" `
  -Headers @{"Authorization" = "Bearer $token"} `
  -Method Get
```

---

## Performance Tips

1. **Frontend**: Clear browser cache if CSS/JS not updating
   - Hard refresh: `Ctrl+Shift+R`
   - Or clear cache in DevTools settings

2. **Backend**: Use `--no-reload` flag for production
   ```powershell
   .venv\Scripts\python.exe -m uvicorn backend.main:create_app --host 0.0.0.0 --port 8000
   ```

3. **Database**: SQLite is fine for development, but use PostgreSQL for production
   - Update `DATABASE_URL` in `.env`

---

## Security Checklist for Production

- [ ] Change `SECRET_KEY` in `.env` to a strong random value
- [ ] Set `DEBUG=false` in `.env`
- [ ] Change CORS origins from `*` to specific domains
- [ ] Use environment-specific password (not `123456789`)
- [ ] Enable HTTPS/SSL
- [ ] Set up proper database backups
- [ ] Configure rate limiting
- [ ] Enable Redis for session management
- [ ] Set strong JWT expiration times
- [ ] Use environment variables for sensitive data

---

## Quick Fixes

```powershell
# Kill all Python processes
Get-Process -Name python | Stop-Process -Force

# Clear all Node processes
Get-Process -Name node | Stop-Process -Force

# Reinstall dependencies
cd webapp
npm cache clean --force
npm install

# Check Python version
python --version  # Should be 3.10+

# Check Node version
node --version  # Should be 16+
npm --version
```

---

## Contact & Support

If issues persist:
1. Check error messages in console/terminal
2. Review `.env` configuration
3. Verify all services are running
4. Try complete restart of both backend and frontend
5. Check network connectivity (firewall, proxies)
