# Bible Shorts On Render

## 1) Architecture summary
- `bible-render-api` (FastAPI + FFmpeg, Docker on Render):
   - Generates 1080x1920 Bible Shorts, black background, centered white serif verse text.
   - Chooses music from `/data/music` first, falls back to generated calm beat if empty.
   - Stores output MP4 + metadata JSON in `/data/output`.
   - Stores logs/idempotency state in `/data/state.db` (SQLite).
   - Exposes endpoints:
      - `GET /health`
      - `GET /verses/random`
      - `GET /music-files`
      - `GET /uploads/check`
      - `POST /render`
      - `POST /record-upload`
      - `GET /files/{file}`

- `bible-shorts-n8n` (self-hosted n8n on Render):
   - Manual + cron trigger.
   - Pulls verse from render API.
   - Reads available `/data/music` file list via render API.
   - Builds title/description/tags.
   - Dedup check (same verse/reference same UTC date).
   - Calls render API, downloads MP4, uploads directly to YouTube via YouTube node.
   - Records upload back to render API.

- Persistent storage:
   - Render Disk mounted at `/data` on render API service.
   - n8n disk mounted at `/home/node/.n8n` for workflow/credentials persistence.

## 2) render.yaml
Blueprint file is in `render.yaml` and defines both services with env vars + persistent disks.

## 3) Service code files (FastAPI + FFmpeg renderer)
- Render API root: `render-service/`
- API app entrypoint: `render-service/app/main.py`
- Render logic: `render-service/app/renderer.py`
- Verse provider (online/local): `render-service/app/verse_provider.py`
- SQLite layer: `render-service/app/db.py`
- Config/env: `render-service/app/config.py`
- Pydantic models: `render-service/app/models.py`
- Init script (creates `/data` folders + DB): `render-service/scripts/init_data.py`
- Seed script (sample verse/music): `render-service/scripts/seed_data.py`
- Docker image: `render-service/Dockerfile`
- Startup command: `render-service/start.sh`
- Python dependencies: `render-service/requirements.txt`

## 4) n8n workflow JSON
- Workflow export: `n8n/workflows/bible-shorts-render.json`
- Includes:
   - Manual trigger
   - Cron trigger
   - Verse + music list retrieval
   - Payload and SEO metadata generation
   - Duplicate check
   - Render call
   - Download rendered MP4
   - YouTube upload node
   - Upload record callback

## 5) YouTube upload node/credential setup steps
1. In Google Cloud Console:
    - Enable `YouTube Data API v3`.
    - Create OAuth Client credentials.
    - Add redirect URI from n8n YouTube credential screen.
2. In n8n:
    - Create credential `YouTube OAuth2`.
    - Authorize with your target channel account.
3. In workflow `Upload to YouTube` node:
    - Confirm credential name is exactly `YouTube OAuth2`.
    - Ensure `binaryProperty` is `data`.
4. Ensure description contains `#Shorts` (already set in payload builder).

## 6) Local test commands
From project root:

```bash
# Render API local
cd render-service
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_data.py
python scripts/seed_data.py
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

```bash
# Health check
curl http://localhost:10000/health
```

```bash
# Render one short (example)
curl -X POST http://localhost:10000/render \
   -H "Content-Type: application/json" \
   -H "x-api-key: change-me" \
   -d '{"verse":"Be still, and know that I am God.","reference":"Psalm 46:10","duration":7,"output_name":"local_test.mp4"}'
```

## 7) Deployment commands
1. Push this repo to GitHub.
2. In Render dashboard: `New +` -> `Blueprint` -> select repo.
3. Apply `render.yaml`.
4. Set secret env vars:
    - `RENDER_API_KEY_INTERNAL`
    - `N8N_ENCRYPTION_KEY`
    - `RENDER_API_BASE`
    - `OUTPUT_BASE_URL`
    - `N8N_HOST`
    - `N8N_EDITOR_BASE_URL`
    - `WEBHOOK_URL`
5. Deploy both services.
6. Import `n8n/workflows/bible-shorts-render.json` in n8n.
7. Configure `YouTube OAuth2` credential and run manual trigger.

## 8) Troubleshooting section
- `401 Invalid API key`:
   - Ensure n8n env `RENDER_API_KEY_INTERNAL` matches render API env value.
- `ffmpeg not found` in `/health`:
   - Confirm render API service is using `render-service/Dockerfile` and deployed latest image.
- Duplicate uploads skipped unexpectedly:
   - Check `/data/state.db` uploads table for same verse/reference on current UTC date.
- YouTube upload fails auth:
   - Reconnect `YouTube OAuth2` credential in n8n.
   - Verify redirect URI matches Google Cloud OAuth client.
- Music missing:
   - Upload files into `/data/music` on render API disk or use fallback generated beat.
- Text overflow:
   - Renderer already wraps aggressively; tune in `render-service/app/renderer.py` (`wrap_for_mobile`, `estimate_verse_font_size`).

## Repository structure
```text
.
├── .env.example
├── render.yaml
├── README.md
├── n8n/
│   ├── Dockerfile
│   └── workflows/
│       └── bible-shorts-render.json
└── render-service/
      ├── Dockerfile
      ├── requirements.txt
      ├── start.sh
      ├── app/
      │   ├── __init__.py
      │   ├── config.py
      │   ├── db.py
      │   ├── main.py
      │   ├── models.py
      │   ├── renderer.py
      │   └── verse_provider.py
      ├── scripts/
      │   ├── init_data.py
      │   └── seed_data.py
      └── data/
            └── verses.json
```
