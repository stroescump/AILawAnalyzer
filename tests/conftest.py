import sys
from pathlib import Path


def pytest_configure() -> None:
    # Ensure `import app...` works without installing the package.
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
