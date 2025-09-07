from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional
import json, time, threading, re

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "learning"
DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)

@dataclass
class LearningEvent:
    ts: float
    user_id: str
    route_symbol: str
    query: str
    answer_preview: str
    used_doc_ids: List[str]
    used_doc_titles: List[str]
    tone_score: float
    extra: Dict[str, Any]

class LearningStore:
    """
    Minimal, append-only JSONL store + compact topic/doc counters.
    Safe for single-process use; coarse-grained file lock via threading.Lock.
    """
    def __init__(self, root: Optional[str | Path] = None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.counters_path = self.root / "counters.json"
        self._lock = threading.Lock()
        # lazy-load counters
        self._counters: Dict[str, Any] = self._load_json(self.counters_path) or {
            "topics": {},   # {"toby": {"count": 12, "last_ts": ...}, ...}
            "docs": {},     # {"path/to/doc.md": {"count": 4, "last_ts": ...}, ...}
            "routes": {},   # {"🪞": 10, "🍃": 3, ...}
        }

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return None
        return None

    def _dump_json(self, path: Path, obj: Any):
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    @staticmethod
    def _topics_from_query(q: str) -> List[str]:
        # crude topic extraction: lowercase keywords (we’ll swap for better later)
        ql = (q or "").lower()
        tokens = re.findall(r"[a-z0-9]{3,}", ql)
        # keep a small set of informative tokens
        stop = {"what","who","how","the","and","for","you","are","tobyworld","about","with","from"}
        return [t for t in tokens if t not in stop][:6]

    def record(self, ev: LearningEvent):
        with self._lock:
            # 1) append event
            with self.events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")

            # 2) update counters
            now = ev.ts
            # route counter
            self._counters["routes"][ev.route_symbol] = int(self._counters["routes"].get(ev.route_symbol, 0)) + 1
            # doc counters
            for did, title in zip(ev.used_doc_ids, ev.used_doc_titles):
                dslot = self._counters["docs"].setdefault(did, {"count": 0, "last_ts": 0.0, "title": title})
                dslot["count"] = int(dslot["count"]) + 1
                dslot["last_ts"] = max(float(dslot.get("last_ts", 0.0)), now)
                if not dslot.get("title"):
                    dslot["title"] = title
            # topic counters
            for t in self._topics_from_query(ev.query):
                tslot = self._counters["topics"].setdefault(t, {"count": 0, "last_ts": 0.0})
                tslot["count"] = int(tslot["count"]) + 1
                tslot["last_ts"] = max(float(tslot.get("last_ts", 0.0)), now)

            # 3) persist counters
            self._dump_json(self.counters_path, self._counters)

    # quick read APIs for later Resonance/Lucidity modules
    def top_topics(self, n: int = 20) -> List[Dict[str, Any]]:
        items = [
            {"topic": k, "count": v.get("count", 0), "last_ts": v.get("last_ts", 0.0)}
            for k, v in self._counters.get("topics", {}).items()
        ]
        items.sort(key=lambda x: (-x["count"], -x["last_ts"]))
        return items[:n]

    def doc_stats(self, doc_id: str) -> Dict[str, Any]:
        return self._counters.get("docs", {}).get(doc_id, {"count": 0, "last_ts": 0.0, "title": ""})

    def route_stats(self) -> Dict[str, int]:
        return dict(self._counters.get("routes", {}))
