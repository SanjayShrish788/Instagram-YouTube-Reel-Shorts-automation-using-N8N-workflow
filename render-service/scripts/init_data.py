from pathlib import Path

from app.config import settings
from app.db import init_db


def main() -> None:
    for directory in (settings.data_root, settings.music_dir, settings.output_dir, settings.tmp_dir):
        directory.mkdir(parents=True, exist_ok=True)

    init_db(settings.state_db)
    print(f"Initialized data directories under: {settings.data_root}")
    print(f"Initialized sqlite DB: {settings.state_db}")


if __name__ == "__main__":
    main()
