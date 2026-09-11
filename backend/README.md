# MediaMesh API

## Run

From the repository root after installing `backend/requirements.txt`:

```powershell
cd backend
uvicorn main:app --reload
```

The API listens at `http://localhost:8000`. Set `MEDIAMESH_DB_PATH` to choose a different SQLite database location. The default is `backend/data/mm.db`, which is local application state and should not be committed.

The API enables credentialed CORS for Vite at `http://localhost:5173` and `http://127.0.0.1:5173`.
