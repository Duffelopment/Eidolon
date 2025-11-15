# Eidolon Investigative Toolkit

Eidolon is a local-first malware triage assistant inspired by services like VirusTotal. It runs entirely on your machine, accepts file uploads for heuristic scanning, and visualises the relationships between artifacts using an interactive node graph. The toolkit also provides an API calibration workspace where you can model downstream integrations without sending any network traffic.

## Features

- 🔍 **Heuristic file scanning** – hashes, metadata, and rule-based suspicious pattern detection.
- 🕸️ **Interactive relationship graph** – explore files, hashes, and findings in a force-directed network.
- 🧾 **Persistent scan history** – results are stored in a local SQLite database for offline review.
- 🔌 **API calibration** – capture external service definitions and document how requests should be shaped.

## Getting started

1. Create a Python virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Launch the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open your browser to <http://127.0.0.1:8000>. From here you can upload files for analysis, browse previous scans, and manage API endpoint definitions. All data stays on disk in `eidolon.db` next to the application.

## Project structure

```
app/
├── crud.py              # Database helpers
├── database.py          # SQLAlchemy engine and session management
├── main.py              # FastAPI application factory and routes
├── models.py            # ORM models for scans and API endpoints
├── routers/             # API route modules
├── schemas.py           # Pydantic response models
├── services/            # Domain services (scanning heuristics)
├── static/              # CSS/JS assets for the frontend
└── templates/           # Jinja2 templates for the web UI
```

The default database is SQLite. If you prefer another backend, update `SQLALCHEMY_DATABASE_URL` in `app/database.py`.

## Security considerations

This project performs static, heuristic analysis only—it does not execute the uploaded files. For deeper analysis consider integrating third-party scanners via the API workspace or extending `app/services/scanner.py` with additional logic such as YARA, ClamAV, or sandbox orchestration.

## License

Released under the MIT License.
