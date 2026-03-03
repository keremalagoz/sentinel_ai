import json
from pathlib import Path

from src.core.cleaner import get_cleaner


def test_cleanup_removes_empty_chat_records(tmp_path):
    root = Path(__file__).resolve().parents[2]
    chat_path = root / "temp" / "chat_history.json"
    chat_path.parent.mkdir(parents=True, exist_ok=True)

    backup = chat_path.read_text(encoding="utf-8") if chat_path.exists() else None

    try:
        sample = [
            {
                "id": "filled_1",
                "title": "filled",
                "date": "2026-03-03 12:00",
                "messages": [{"text": "x", "is_user": True}],
            },
            {
                "id": "empty_1",
                "title": "Untitled",
                "date": "2026-03-03 12:01",
                "messages": [],
            },
        ]
        chat_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

        deleted = get_cleaner().cleanup_old_sessions(days=3650)
        assert deleted >= 1

        result = json.loads(chat_path.read_text(encoding="utf-8"))
        ids = {row["id"] for row in result}
        assert "filled_1" in ids
        assert "empty_1" not in ids
    finally:
        if backup is None:
            if chat_path.exists():
                chat_path.unlink()
        else:
            chat_path.write_text(backup, encoding="utf-8")
