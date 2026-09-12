# MediaMesh API

## Run

From the repository root after installing `backend/requirements.txt`:

```powershell
cd backend
uvicorn main:app --reload
```

The API listens at `http://localhost:8000`. Set the server-side `DATABASE_URL` in the root `.env` to the Supabase PostgreSQL connection string before starting. Runtime persistence has no SQLite fallback.

The API enables credentialed CORS for Vite at `http://localhost:5173` and `http://127.0.0.1:5173`.
