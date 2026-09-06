"""Local JSON projects, atomic replacement, and optimistic revision checks."""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .document import digest, normalize_text, parse


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.projects = root / "projects"
        self.projects.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.warnings = []

    def path(self, ident):
        if not isinstance(ident, str) or not re.fullmatch(r"[a-f0-9]{32}", ident):
            raise ValueError("Invalid project id.")
        return self.projects / (ident + ".json")

    def read(self, ident):
        with self.lock:
            return json.loads(self.path(ident).read_text(encoding="utf-8"))

    def write(self, doc):
        path = self.path(doc["id"])
        temp = path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(doc, ensure_ascii=False))
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)

    def list(self, archived=False):
        with self.lock:
            result = []
            self.warnings = []
            for file in self.projects.glob("*.json"):
                try:
                    doc = json.loads(file.read_text(encoding="utf-8"))
                    if bool(doc.get("archived", False)) != archived:
                        continue
                    row = {k: doc[k] for k in ("id", "title", "updated_at", "revision")}
                    row.update(
                        characters=len(doc.get("text", "")),
                        findings=len((doc.get("report") or {}).get("findings", [])),
                        draft=bool(doc.get("draft")),
                    )
                    result.append(row)
                except (ValueError, KeyError, OSError):
                    self.warnings.append(str(file))
            return sorted(result, key=lambda d: d["updated_at"], reverse=True)

    def create(self, title, text):
        text = normalize_text(text)
        parse(text)
        if not isinstance(title, str) or not title.strip() or len(title) > 150:
            raise ValueError("标题须为 1–150 个字符 / Title must be 1–150 characters.")
        with self.lock:
            doc = {
                "id": uuid.uuid4().hex,
                "title": title.strip(),
                "text": text,
                "revision": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "report": None,
                "reviews": {},
            }
            self.write(doc)
            return doc

    def update(self, ident, text, revision):
        text = normalize_text(text)
        parse(text)
        with self.lock:
            doc = self.read(ident)
            if revision != doc["revision"]:
                raise Conflict("稿件已被修改，请重新打开 / Manuscript changed; reload before saving.")
            if text != doc["text"]:
                self.checkpoint(doc)
                doc.update(
                    text=text, revision=doc["revision"] + 1, updated_at=datetime.now(timezone.utc).isoformat()
                )
            doc.pop("draft", None)
            self.write(doc)
            return doc

    def save_draft(self, ident, text, revision):
        if not isinstance(text, str) or len(text) > 300_000 or "\x00" in text:
            raise ValueError("草稿最多 30 万字符 / Draft limit is 300,000 characters.")
        with self.lock:
            doc = self.read(ident)
            if revision != doc["revision"]:
                raise Conflict("稿件已变化，草稿未覆盖 / Manuscript changed; draft not overwritten.")
            if text == doc["text"]:
                doc.pop("draft", None)
            else:
                doc["draft"] = {
                    "text": text,
                    "base_revision": revision,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }
            self.write(doc)
            return doc

    def checkpoint(self, doc):
        folder = self.root / "history" / doc["id"]
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / f"{doc['revision']:08d}.json"
        if not file.exists():
            snapshot = {k: v for k, v in doc.items() if k != "draft"}
            temp = file.with_suffix(".tmp")
            with temp.open("w", encoding="utf-8") as stream:
                json.dump(snapshot, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(file)

    def history(self, ident):
        self.path(ident)
        result = []
        for file in (self.root / "history" / ident).glob("*.json"):
            try:
                doc = json.loads(file.read_text(encoding="utf-8"))
                result.append(
                    {
                        "revision": doc["revision"],
                        "updated_at": doc["updated_at"],
                        "characters": len(doc["text"]),
                    }
                )
            except (ValueError, KeyError):
                continue
        return sorted(result, key=lambda d: d["revision"], reverse=True)

    def restore(self, ident, snapshot_revision, current_revision):
        self.path(ident)
        if not isinstance(snapshot_revision, int) or snapshot_revision < 1:
            raise ValueError("Invalid revision.")
        snapshot = json.loads(
            (self.root / "history" / ident / f"{snapshot_revision:08d}.json").read_text(encoding="utf-8")
        )
        return self.update(ident, snapshot["text"], current_revision)

    def rename(self, ident, title):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 150:
            raise ValueError("标题须为 1–150 字符 / Title must be 1–150 characters.")
        with self.lock:
            doc = self.read(ident)
            doc["title"] = title.strip()
            self.write(doc)
            return doc

    def archive(self, ident, archived=True):
        with self.lock:
            doc = self.read(ident)
            doc["archived"] = bool(archived)
            self.write(doc)
            return doc

    def save_report(self, ident, report, revision):
        with self.lock:
            doc = self.read(ident)
            if doc["revision"] != revision or report["source_hash"] != digest(doc["text"]):
                raise Conflict(
                    "检查期间稿件发生变化，结果未保存 / Manuscript changed during analysis; result not saved."
                )
            for item in report["findings"]:
                if item["id"] in doc["reviews"]:
                    item.update(doc["reviews"][item["id"]])
            report["revision"] = revision
            doc["report"] = report
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.write(doc)
            return doc

    def review(self, ident, finding_id, status, note, revision):
        if (
            status not in {"pending", "confirmed", "dismissed"}
            or not isinstance(note, str)
            or len(note) > 2000
        ):
            raise ValueError("Invalid review status or note.")
        with self.lock:
            doc = self.read(ident)
            report = doc.get("report")
            if revision != doc["revision"] or not report or report["source_hash"] != digest(doc["text"]):
                raise Conflict("稿件已变化，请重新检查 / Rerun analysis on the current manuscript.")
            item = next((f for f in report["findings"] if f["id"] == finding_id), None)
            if item is None:
                raise ValueError("Finding does not belong to this report.")
            item.update(status=status, note=note)
            doc["reviews"][finding_id] = {"status": status, "note": note}
            self.write(doc)
            return doc
