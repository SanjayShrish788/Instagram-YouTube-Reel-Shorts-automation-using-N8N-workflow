from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "bible-render-api"
    data_root: Path = Path("/data")
    state_db: Path = Path("/data/state.db")

    internal_api_key: str = Field(default="change-me", alias="RENDER_API_KEY_INTERNAL")
    verse_source: str = Field(default="auto", alias="VERSE_SOURCE")
    bible_api_base: str = Field(default="https://bible-api.com", alias="BIBLE_API_BASE")

    min_duration: float = 6.0
    max_duration: float = 8.0

    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"

    output_base_url: str = Field(default="", alias="OUTPUT_BASE_URL")

    @property
    def music_dir(self) -> Path:
        return self.data_root / "music"

    @property
    def output_dir(self) -> Path:
        return self.data_root / "reels"

    @property
    def tmp_dir(self) -> Path:
        return self.data_root / "tmp"

    @property
    def local_verses_path(self) -> Path:
        return self.data_root / "verses.json"


settings = Settings()
