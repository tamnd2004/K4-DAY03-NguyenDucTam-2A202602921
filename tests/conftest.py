import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))

@pytest.fixture
def db_path(tmp_path,monkeypatch):
    path=tmp_path/"hr.db"
    monkeypatch.setenv("HR_DB_PATH",str(path))
    return path
