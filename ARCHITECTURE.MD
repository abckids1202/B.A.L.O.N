# Architecture

```text
Vercel React frontend
        |
        | HTTPS / JSON
        v
Render FastAPI backend
        |
        v
Service layer -> domain modules -> SQLite demo database
```

The frontend does not load models, open SQLite, or run optimization directly. It calls FastAPI endpoints only.
