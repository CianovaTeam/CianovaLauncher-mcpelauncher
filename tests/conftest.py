import sys
import os
import json
import tempfile
import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture(scope="session", autouse=True)
def init_logger():
    from src.utils.logger import logger
    tmpdir = tempfile.mkdtemp()
    logger.init(log_dir=tmpdir)


@pytest.fixture
def tmp_config():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump({}, tmp)
    tmp.close()
    from src.core.config_manager import ConfigManager
    cm = ConfigManager(config_file=tmp.name)
    yield cm, tmp.name
    os.unlink(tmp.name)
