from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.sqlite3"

    @property
    def blobs_dir(self) -> Path:
        return self.data_dir


def load_config() -> AppConfig:
    return AppConfig(data_dir=Path("data"))
