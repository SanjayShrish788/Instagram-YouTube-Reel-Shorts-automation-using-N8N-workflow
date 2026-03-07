import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse

from .config import settings
from .db import has_uploaded_today, init_db, record_render, record_upload
from .models import (
    HealthResponse,
    MusicFilesResponse,
    RenderRequest,
    RenderResponse,
    UploadCheckResponse,
    UploadRecordRequest,
    VerseResponse,
)
from .renderer import render_short, safe_output_name
from .verse_provider import get_random_verse


app = FastAPI(title="Bible Render API", version="1.0.0")


def utc_date_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.on_event("startup")
def on_startup() -> None:
    settings.music_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.state_db)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if shutil.which(settings.ffmpeg_binary) is None:
        raise HTTPException(status_code=500, detail="ffmpeg not found in PATH")
    return HealthResponse(status="ok", service=settings.service_name)


@app.get("/verses/random", response_model=VerseResponse, dependencies=[Depends(require_api_key)])
def random_verse(source: str = Query(default="auto")) -> VerseResponse:
    text, reference, used_source = get_random_verse(
        source=source or settings.verse_source,
        bible_api_base=settings.bible_api_base,
        local_path=settings.local_verses_path,
    )
    return VerseResponse(text=text, reference=reference, source=used_source)


@app.get("/music-files", response_model=MusicFilesResponse, dependencies=[Depends(require_api_key)])
def music_files() -> MusicFilesResponse:
    files = [
        file.name
        for file in settings.music_dir.iterdir()
        if file.is_file() and file.suffix.lower() in {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg"}
    ]
    return MusicFilesResponse(files=sorted(files))


@app.get("/uploads/check", response_model=UploadCheckResponse, dependencies=[Depends(require_api_key)])
def upload_check(verse: str = Query(...), reference: str = Query(...)) -> UploadCheckResponse:
    run_date = utc_date_str()
    duplicate = has_uploaded_today(settings.state_db, verse.strip(), reference.strip(), run_date)
    return UploadCheckResponse(duplicate=duplicate, run_date=run_date)


@app.post("/render", response_model=RenderResponse, dependencies=[Depends(require_api_key)])
def render(payload: RenderRequest) -> RenderResponse:
    run_date = utc_date_str()

    output_name = safe_output_name(payload.output_name)
    metadata_path = settings.output_dir / f"{Path(output_name).stem}.json"

    try:
        output_path, logs, used_music = render_short(
            ffmpeg_binary=settings.ffmpeg_binary,
            output_dir=settings.output_dir,
            tmp_dir=settings.tmp_dir,
            music_dir=settings.music_dir,
            verse=payload.verse,
            reference=payload.reference,
            duration=payload.duration,
            requested_music_file=payload.music_file,
            output_name=output_name,
        )

        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "run_date": run_date,
            "verse": payload.verse,
            "reference": payload.reference,
            "duration": payload.duration,
            "music_file": used_music,
            "output_name": output_name,
            "output_path": str(output_path),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        record_render(
            db_path=settings.state_db,
            run_date=run_date,
            verse=payload.verse,
            reference=payload.reference,
            output_name=output_name,
            output_path=str(output_path),
            metadata_path=str(metadata_path),
            duration=payload.duration,
            music_file=used_music,
            status="success",
            error_message=None,
        )

    except Exception as exc:
        record_render(
            db_path=settings.state_db,
            run_date=run_date,
            verse=payload.verse,
            reference=payload.reference,
            output_name=output_name,
            output_path=str(settings.output_dir / output_name),
            metadata_path=str(metadata_path),
            duration=payload.duration,
            music_file=payload.music_file,
            status="error",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}")

    output_url = f"/files/{output_name}"
    if settings.output_base_url:
        output_url = f"{settings.output_base_url.rstrip('/')}/files/{output_name}"

    return RenderResponse(
        success=True,
        output_path=str(output_path),
        output_url=output_url,
        metadata_path=str(metadata_path),
        duration=payload.duration,
        logs=logs,
    )


@app.post("/record-upload", dependencies=[Depends(require_api_key)])
def record_upload_endpoint(payload: UploadRecordRequest) -> dict:
    run_date = utc_date_str()
    record_upload(
        db_path=settings.state_db,
        run_date=run_date,
        verse=payload.verse,
        reference=payload.reference,
        output_name=safe_output_name(payload.output_name),
        youtube_video_id=payload.youtube_video_id,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        privacy_status=payload.privacy_status,
        status=payload.status,
    )
    return {"ok": True}


@app.get("/files/{file_name}", dependencies=[Depends(require_api_key)])
def get_file(file_name: str) -> FileResponse:
    safe_name = Path(file_name).name
    file_path = settings.output_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=safe_name, media_type="video/mp4")
