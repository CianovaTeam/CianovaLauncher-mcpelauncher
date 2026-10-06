import os

import pytest

# Qt offscreen: el módulo debe poder correr en entornos sin display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src import constants as c
from src.gui.tabs.logs_tab import LogsTab
from src.utils.logger import logger

LOG_NAME = "cianovalauncher-20260819120000.log"
OTHER_LOG_NAME = "cianovalauncher-20260818090000.log"
LOG_TEXT = (
    "2026-08-19 12:00:00 - INFO - arranque del launcher\n"
    "2026-08-19 12:00:01 - INFO - listo\n"
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


class MockApp:
    def __init__(self):
        self.config = {
            c.CONFIG_KEY_APPEARANCE: "Dark",
            c.CONFIG_KEY_COLOR_THEME: "blue",
        }


@pytest.fixture
def log_session(tmp_path, monkeypatch):
    """Apunta el directorio de logs y el log actual a un archivo temporal."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    path = log_dir / LOG_NAME
    path.write_text(LOG_TEXT, encoding="utf-8")

    monkeypatch.setattr(logger, "default_log_dir", lambda: str(log_dir))
    monkeypatch.setattr(logger, "_log_file", str(path))
    return log_dir, path


@pytest.fixture
def logs_tab(qapp, log_session):
    tab = LogsTab(None, MockApp())
    tab.resize(500, 400)
    tab.show()
    qapp.processEvents()
    yield tab
    tab._live_timer.stop()
    tab.hide()
    tab.deleteLater()
    qapp.processEvents()


def test_logs_tab_lists_and_shows_current_log(logs_tab):
    assert logs_tab._combo.count() >= 1
    assert logs_tab._combo.currentData() == LOG_NAME
    assert LOG_TEXT.splitlines()[0] in logs_tab._text.toPlainText()
    assert c.t("UI_LOG_LIVE_SESSION") in logs_tab._hint_label.text()
    assert logs_tab._export_btn.text() == c.t("UI_BUTTON_EXPORT_LOG")
    assert logs_tab._user_scrolled_away is False


def test_parse_log_name():
    assert (
        LogsTab._parse_log_name("cianovalauncher-20260819120000.log")
        == "19/08/2026 - 12:00:00"
    )
    assert LogsTab._parse_log_name("random.log") is None
    assert LogsTab._parse_log_name("cianovalauncher-basura.log") is None


def test_read_new_chunk_reads_only_appended_bytes(logs_tab, log_session):
    _, path = log_session

    # El init ya cargó el archivo completo: no debe reenviar nada.
    assert logs_tab._read_new_chunk(LOG_NAME) == ""

    with path.open("a", encoding="utf-8") as f:
        f.write("linea agregada despues\n")

    # La ruta de refresco en vivo agrega solo los bytes nuevos al cuadro.
    logs_tab._load_log(LOG_NAME)
    assert "linea agregada despues" in logs_tab._text.toPlainText()
    assert LOG_TEXT.splitlines()[0] in logs_tab._text.toPlainText()

    # Los offsets ya consumidos no reenvían bytes viejos.
    assert logs_tab._offsets[LOG_NAME] == path.stat().st_size
    assert logs_tab._read_new_chunk(LOG_NAME) == ""


def test_scroll_state_tracks_user_position(logs_tab):
    logs_tab._text.setPlainText("\n".join(f"linea {i}" for i in range(500)))
    sb = logs_tab._text.verticalScrollBar()
    assert sb.maximum() > 0

    logs_tab._on_scroll(sb.maximum())
    assert logs_tab._user_scrolled_away is False

    logs_tab._on_scroll(0)
    assert logs_tab._user_scrolled_away is True


def test_selecting_previous_log_resets_scroll_and_shows_it(logs_tab, log_session):
    log_dir, _ = log_session
    other = log_dir / OTHER_LOG_NAME
    other.write_text("log de la sesion anterior\n", encoding="utf-8")

    logs_tab._refresh_log_list()
    idx = logs_tab._combo.findData(OTHER_LOG_NAME)
    assert idx >= 0

    logs_tab._user_scrolled_away = True
    logs_tab._combo.setCurrentIndex(idx)

    assert logs_tab._user_scrolled_away is False
    assert logs_tab._combo.currentData() == OTHER_LOG_NAME
    assert "log de la sesion anterior" in logs_tab._text.toPlainText()
    assert c.t("UI_LOG_PREV_SESSION") in logs_tab._hint_label.text()
    assert logs_tab._current_log_name == LOG_NAME
