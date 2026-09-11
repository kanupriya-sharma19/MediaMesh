# MediaMesh React frontend

## Run

From this directory:

```powershell
npm install
npm run dev
```

The Vite development server runs at `http://localhost:5173`. Set `VITE_API_URL` when the API is not at `http://localhost:8000`:

```text
VITE_API_URL=http://localhost:8000
```

The frontend uses HTTP-only cookies for authentication and never stores session tokens in local storage.
