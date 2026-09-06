"""Durable desktop preferences. Model credentials are deliberately process-only."""

import json
from pathlib import Path

from .providers import Settings


class Preferences:
    def __init__(self, root: Path):
        self.path = root / "preferences.json"
        try:
            self.values = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.values, dict):
                self.values = {}
        except (ValueError, OSError):
            self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, **values):
        self.values.update(values)
        self.values.pop("api_key", None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.values, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def model(self, language):
        raw = self.get("model", {})
        try:
            return Settings(
                provider=raw.get("provider", "rules"),
                base_url=raw.get("base_url", ""),
                model=raw.get("model", ""),
                language=language,
            ).validate()
        except (ValueError, TypeError, AttributeError):
            return Settings(language=language)

    def save_model(self, settings):
        self.set(model={k: getattr(settings, k) for k in ("provider", "base_url", "model")})
