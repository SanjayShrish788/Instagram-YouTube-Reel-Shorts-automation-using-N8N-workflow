from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class VerseResponse(BaseModel):
    text: str
    reference: str
    source: str


class RenderRequest(BaseModel):
    verse: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    duration: float = Field(default=7.0, ge=6.0, le=8.0)
    music_file: str | None = None
    output_name: str = Field(default="bible_short.mp4")


class RenderResponse(BaseModel):
    success: bool
    output_path: str
    output_url: str
    metadata_path: str
    duration: float
    logs: str


class UploadCheckResponse(BaseModel):
    duplicate: bool
    run_date: str


class UploadRecordRequest(BaseModel):
    verse: str
    reference: str
    output_name: str
    youtube_video_id: str | None = None
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    privacy_status: str = "public"
    status: str = "uploaded"


class MusicFilesResponse(BaseModel):
    files: list[str]
