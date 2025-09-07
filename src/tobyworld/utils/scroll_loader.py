# src/tobyworld/utils/scroll_loader.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Iterable, Tuple, Any
import re
import json
import time
from datetime import datetime

# ── Markdown / filename cleaners (kept local to avoid cross-module deps)
_MD_HEADING = re.compile(r"^\s*#{1,6}\s*")
_MD_INLINE  = re.compile(r"[*_`~]+")
_PREFIX_CODE = re.compile(r"^(?:[A-Za-z]{1,5}_?)?\d{2,4}\s*[–-]\s*", re.UNICODE)
_IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_LINK_MD = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

SUPPORTED_EXTS = {".md", ".markdown", ".mdx", ".txt"}

def _clean_md_line(s: str) -> str:
    s = (s or "").strip()
    s = _MD_HEADING.sub("", s).strip()
    s = _PREFIX_CODE.sub("", s).strip()
    s = _MD_INLINE.sub("", s).strip()
    s = _IMG_MD.sub("", s)
    s = _LINK_MD.sub(r"\1", s)
    s = re.sub(r"\.md(?:x|own|arkdown)?$", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Returns (meta, body). Front-matter supports YAML (subset) or JSON between --- blocks.
    If JSON is detected (first non-space char is {), we parse as JSON; otherwise a tiny YAML subset.
    """
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    raw = m.group(1).strip()
    body = text[m.end():]
    if not raw:
        return {}, body

    # Try JSON first (strict), then a super-light YAML (key: value, no nesting)
    if raw.lstrip().startswith("{"):
        try:
            return json.loads(raw), body
        except Exception:
            pass

    meta: Dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # bools / numbers / lists (comma-separated) quick parse
        if v.lower() in {"true", "false"}:
            meta[k] = (v.lower() == "true")
        elif re.fullmatch(r"-?\d+(\.\d+)?", v or ""):
            meta[k] = float(v) if "." in v else int(v)
        elif "," in v:
            meta[k] = [p.strip() for p in v.split(",") if p.strip()]
        else:
            meta[k] = v
    return meta, body

def _parse_timestamp(meta: Dict[str, Any], fallback_path: Optional[Path]) -> float:
    # Priority: meta.timestamp, meta.date, file mtime
    for key in ("timestamp", "date", "updated_at", "created_at"):
        v = meta.get(key)
        if not v:
            continue
        # accept float / int epoch
        if isinstance(v, (int, float)):
            return float(v)
        # try ISO date/time
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(str(v), fmt)
                return dt.timestamp()
            except Exception:
                continue
        # final attempt: datetime.fromisoformat (py3.12 safe)
        try:
            return datetime.fromisoformat(str(v)).timestamp()
        except Exception:
            pass
    if fallback_path:
        try:
            return float(fallback_path.stat().st_mtime)
        except Exception:
            return 0.0
    return 0.0

def _first_heading(body: str) -> Optional[str]:
    for ln in body.splitlines():
        raw = ln.strip()
        if raw.startswith("#"):
            return _clean_md_line(raw)
    return None

def _natural_title(path: Path, body: str, meta_title: Optional[str]) -> str:
    if meta_title:
        return _clean_md_line(str(meta_title))
    h = _first_heading(body)
    if h:
        return h
    stem = path.stem
    stem = _PREFIX_CODE.sub("", stem)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem or path.name

@dataclass
class ScrollRow:
    id: str
    text: str
    meta: Dict[str, Any]

def read_scroll(path: Path) -> ScrollRow:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        raw = ""
    fm, body = _parse_frontmatter(raw)
    title = _natural_title(path, body, fm.get("title"))
    ts = _parse_timestamp(fm, path)
    lang = fm.get("lang") or fm.get("language")
    tags = fm.get("tags") if isinstance(fm.get("tags"), list) else (fm.get("tags") or [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    meta: Dict[str, Any] = {
        "path": str(path),
        "title": title,
        "timestamp": float(ts),
    }
    if lang:
        meta["lang"] = lang
    if tags:
        meta["tags"] = tags
    # include any extra fm keys (non-conflicting)
    for k, v in fm.items():
        if k not in meta:
            meta[k] = v

    return ScrollRow(id=str(path), text=body, meta=meta)

def iter_scroll_paths(base: Path) -> Iterable[Path]:
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            yield p

def load_scroll_index(root: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """
    Public API: returns a list of dicts shaped like:
      { "id": str, "text": str, "meta": {"path": str, "title": str, "timestamp": float, ...} }
    """
    base = Path(root) if root else (Path(__file__).resolve().parents[2] / "lore-scrolls")
    base.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for p in sorted(iter_scroll_paths(base)):
        row = read_scroll(p)
        rows.append({"id": row.id, "text": row.text, "meta": row.meta})
    return rows

# Optional lightweight caching index for long-running processes (server, jobs)
class ScrollIndex:
    def __init__(self, root: Optional[Path | str] = None):
        self.root = Path(root) if root else (Path(__file__).resolve().parents[2] / "lore-scrolls")
        self._cache: Dict[str, float] = {}   # path -> last_mtime
        self._rows: List[Dict[str, Any]] = []
        self.rebuild()

    def rebuild(self) -> int:
        self._rows.clear()
        self._cache.clear()
        count = 0
        for p in iter_scroll_paths(self.root):
            try:
                st = p.stat()
                self._cache[str(p)] = float(st.st_mtime)
            except Exception:
                self._cache[str(p)] = 0.0
            row = read_scroll(p)
            self._rows.append({"id": row.id, "text": row.text, "meta": row.meta})
            count += 1
        # deterministic order
        self._rows.sort(key=lambda r: (-(r["meta"].get("timestamp") or 0.0), r["meta"].get("title", "")))
        return count

    def maybe_refresh(self) -> int:
        """Check mtimes and refresh only changed/added files. Returns number of changed files."""
        changed = 0
        current_paths = {str(p): p for p in iter_scroll_paths(self.root)}
        # detect removed
        known_paths = set(self._cache.keys())
        removed = known_paths - set(current_paths.keys())
        if removed:
            self._rows = [r for r in self._rows if r["id"] not in removed]
            for rp in removed:
                self._cache.pop(rp, None)
            changed += len(removed)

        # detect added/modified
        for sp, p in current_paths.items():
            try:
                mtime = float(p.stat().st_mtime)
            except Exception:
                mtime = 0.0
            if sp not in self._cache or self._cache[sp] != mtime:
                self._cache[sp] = mtime
                row = read_scroll(p)
                # replace or append
                found = False
                for i, r in enumerate(self._rows):
                    if r["id"] == sp:
                        self._rows[i] = {"id": row.id, "text": row.text, "meta": row.meta}
                        found = True
                        break
                if not found:
                    self._rows.append({"id": row.id, "text": row.text, "meta": row.meta})
                changed += 1

        if changed:
            self._rows.sort(key=lambda r: (-(r["meta"].get("timestamp") or 0.0), r["meta"].get("title", "")))
        return changed

    @property
    def rows(self) -> List[Dict[str, Any]]:
        return self._rows[:]
