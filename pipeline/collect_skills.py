"""Skill Radar collector.

Builds the census behind ``/skills`` (contract: ``docs/ideas/agent-skill-radar.md``).

Three measured facts shape this module:

1. **GitHub code search is not a census.** ``filename:SKILL.md`` reports a
   saturated ``total_count`` and caps at 1,000 files, and it missed every
   canonical skill repo. Discovery here is a union of repo searches instead.
2. **Topic tags anti-correlate with traction.** The biggest skill repos carry no
   topics, so the momentum sweep exists to catch them and topics only catch
   small tagged repos.
3. **Raw ``SKILL.md`` counts are inflated.** One skill is vendored once per
   harness directory (``.claude/``, ``.agents/``, ``.cursor/`` ...), so the unit
   is ``(repo, skill name)`` with the copy count kept as portability evidence.

The module never ranks by absolute stars. Traction is a family property
(renamed ports are how this ecosystem distributes) and ``fork_ratio`` is the
adoption proxy, because installing a skill means copying it into your tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "skills.yaml"
DATA_DIR = ROOT / "data" / "skills"
HISTORY_DIR = DATA_DIR / "history"
ETAG_PATH = ROOT / "data" / "cache" / "skills_etags.json"
# Bump whenever the inventory shape changes: cached tree payloads are reused on
# a 304, so a schema bump must invalidate them or old fields survive forever.
SCHEMA_VERSION = 3

# Layout segments observed in the wild. A skill vendored per harness produces one
# SKILL.md per segment, which is why copies are metadata and not rows.
LAYOUT_SEGMENTS = {
    "skills",
    ".agents",
    ".agent",
    ".claude",
    ".cursor",
    ".devin",
    ".dsh",
    ".openclaw",
    ".kiro",
    ".codex",
    ".opencode",
    ".pi",
    "plugins",
    "plugin",
    "packages",
    ".github",
    "docs",
}

LOCALE_RE = re.compile(r"(?:^|/)([a-z]{2}-[A-Z]{2}|ja|zh|ko|de|fr|es|pt|ru)(?:/|$)")
# Only an explicit pointer joins a family. A shared name never does, because
# `pstack` also matches a 2012 C stack-trace tool.
DERIVATION_RE = re.compile(
    r"(port(ed)? of|derived from|fork(ed)? of|based on|adapted from|inspired by|"
    r"translated for|version of|via)\s+\S",
    re.I,
)
FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|\Z)", re.S)


# --------------------------------------------------------------------------- #
# small utilities
# --------------------------------------------------------------------------- #


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_date(now: datetime | None = None) -> str:
    return (now or utc_now()).date().isoformat()


def load_config(path: Path | None = None) -> dict[str, Any]:
    with open(path or CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    if not isinstance(cfg, dict):
        raise ValueError("skills config must be a mapping")
    return cfg


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Any) -> None:
    """Atomic write, so a killed run never leaves a truncated artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def slugify(text: str, limit: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug or "unknown")[:limit]


def parse_dt(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_latest_history(today: date | None = None) -> dict[str, Any]:
    """Newest history snapshot at or before today, so a board run on a quiet
    day still has a velocity baseline."""
    today = today or utc_now().date()
    try:
        files = sorted(HISTORY_DIR.glob("*.json"))
    except OSError:
        return {}
    for path in reversed(files):
        if path.stem <= today.isoformat():
            return read_json(path, {}) or {}
    return {}


# --------------------------------------------------------------------------- #
# GitHub client
# --------------------------------------------------------------------------- #


def github_token() -> str | None:
    for key in ("SKILLS_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value.strip()
    try:  # convenience for local runs; CI passes GITHUB_TOKEN explicitly
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=20, check=False
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


class GitHubClient:
    """REST client with conditional requests.

    GitHub does not charge a 304 against the primary rate limit, so polling the
    known repo set every 6h is close to free. Search has its own bucket and is
    paced separately.
    """

    def __init__(
        self,
        token: str,
        cfg: dict[str, Any] | None = None,
        etag_path: Path | None = None,
        session: requests.Session | None = None,
    ) -> None:
        limits = (cfg or {}).get("limits", {})
        self.timeout = float(limits.get("request_timeout_seconds", 25))
        self.search_gap = float(limits.get("search_min_interval_seconds", 2.2))
        self.core_gap = float(limits.get("core_min_interval_seconds", 0.25))
        self.retries = int(limits.get("max_retries", 3))
        self.etag_path = etag_path or ETAG_PATH
        self.etags: dict[str, dict[str, str]] = read_json(self.etag_path, {}) or {}
        self.dirty = False
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "llm-digest-skill-radar",
            }
        )
        self._last = {"search": 0.0, "core": 0.0}
        self.requests_made = 0
        self.not_modified = 0

    def _pace(self, kind: str) -> None:
        gap = self.search_gap if kind == "search" else self.core_gap
        wait = gap - (time.time() - self._last[kind])
        if wait > 0:
            time.sleep(wait)
        self._last[kind] = time.time()

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        kind: str = "core",
        conditional: bool = True,
    ) -> tuple[Any, bool]:
        """Return ``(payload, not_modified)``. Payload is None on failure."""
        url = path if path.startswith("http") else f"https://api.github.com{path}"
        etag_key = url + ("?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items())) if params else "")
        headers: dict[str, str] = {}
        if conditional:
            stored = self.etags.get(etag_key)
            if stored:
                headers["If-None-Match"] = stored["etag"]
        for attempt in range(self.retries + 1):
            self._pace(kind)
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt >= self.retries:
                    print(f"skills_github_error kind={kind} detail={type(exc).__name__}")
                    return None, False
                time.sleep(2 * (attempt + 1))
                continue
            self.requests_made += 1
            if resp.status_code == 304:
                self.not_modified += 1
                return None, True
            if resp.status_code in (403, 429):
                remaining = resp.headers.get("x-ratelimit-remaining")
                reset = resp.headers.get("x-ratelimit-reset")
                if remaining == "0" and reset:
                    wait = max(1, int(reset) - int(time.time()) + 2)
                    print(f"skills_github_ratelimit kind={kind} sleep={min(wait, 120)}")
                    time.sleep(min(wait, 120))
                    continue
                if attempt >= self.retries:
                    print(f"skills_github_blocked kind={kind} status=403")
                    return None, False
                time.sleep(20)
                continue
            if resp.status_code == 422:
                print(f"skills_github_invalid_query path={path}")
                return None, False
            if resp.status_code >= 500:
                if attempt >= self.retries:
                    print(f"skills_github_error kind={kind} status={resp.status_code}")
                    return None, False
                time.sleep(3 * (attempt + 1))
                continue
            if resp.status_code != 200:
                print(f"skills_github_error kind={kind} status={resp.status_code}")
                return None, False
            etag = resp.headers.get("etag")
            if etag and conditional:
                self.etags[etag_key] = {"etag": etag, "at": utc_now().isoformat()}
                self.dirty = True
            return resp.json(), False
        return None, False

    def save_etags(self) -> None:
        if self.dirty:
            write_json(self.etag_path, self.etags)
            self.dirty = False

    def repo(self, full_name: str) -> dict[str, Any] | None:
        # Not conditional: stars and push times change constantly, so an ETag
        # here would only suppress the snapshot the velocity model depends on.
        payload, _ = self.get(f"/repos/{full_name}", conditional=False)
        return payload

    def tree(
        self, full_name: str, branch: str | None, conditional: bool = True
    ) -> list[dict[str, Any]] | None:
        if not branch:
            return None
        payload, not_modified = self.get(
            f"/repos/{full_name}/git/trees/{branch}",
            params={"recursive": "1"},
            conditional=conditional,
        )
        if not_modified or not isinstance(payload, dict):
            return None
        tree = payload.get("tree")
        return tree if isinstance(tree, list) else None

    def search_repos(self, query: str, max_pages: int = 3, per_page: int = 100) -> list[dict[str, Any]]:
        """Enumerate a repo-search query, tolerated against the 1,000 cap."""
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            payload, _ = self.get(
                "/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page, "page": page},
                kind="search",
                conditional=False,
            )
            if not isinstance(payload, dict):
                break
            items = payload.get("items") or []
            for item in items:
                name = item.get("full_name")
                if name and name not in seen:
                    seen.add(name)
                    out.append(item)
            if len(items) < per_page:
                break
        return out


# --------------------------------------------------------------------------- #
# skill files: path shape, frontmatter, dedupe
# --------------------------------------------------------------------------- #


def is_skill_path(path: str) -> bool:
    """Exact basename match.

    ``path.endswith("skill.md")`` also matches ``verification-skill.md``, which
    inflated inventory by 6-7% on the calibration repos.
    """
    if not path:
        return False
    return path.rsplit("/", 1)[-1].lower() == "skill.md"


def skill_name_from_path(path: str, repo_name: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2 and parts[-2].strip():
        return parts[-2].strip()
    return repo_name.rsplit("/", 1)[-1]


PREFERRED_LAYOUTS = {"skills", "plugins", "plugin"}


def layout_of(path: str) -> str:
    """Where the skill lives, ignoring pure container dirs.

    ``docs/ja-JP/skills/x/SKILL.md`` is a locale mirror of the ``skills`` copy,
    not a new ``docs`` layout, so a real layout wins over a container segment.
    """
    parts = path.split("/")[:-1]
    for part in parts:
        if part in PREFERRED_LAYOUTS:
            return part
        if part.startswith(".") and len(part) > 1:
            return part
    for part in parts:
        if part in LAYOUT_SEGMENTS:
            return part
    # Skills stored at the repo root (``autoplan/SKILL.md``) are root layout, not
    # a new layout per skill directory. Getting this wrong made one repo report
    # fifty distinct "layouts" and inflated every breadth/breadth-based score.
    return "root"


def is_excluded_path(path: str, exclude_parts: Iterable[str]) -> bool:
    """Test fixtures and vendored copies are not skills.

    `gstack` ships `test/fixtures/context-bill/tree-a/alpha/SKILL.md`, which is
    inventory noise, not a skill a reader can use.
    """
    wanted = {part.lower() for part in exclude_parts or ()}
    if not wanted:
        return False
    return any(part.lower() in wanted for part in path.split("/")[:-1])


def locale_of(path: str) -> str | None:
    match = LOCALE_RE.search(path)
    return match.group(1) if match else None


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """YAML frontmatter, with block scalars expanded.

    ``description: |-`` parses to empty under a naive regex, which put four
    sample skills in "unmatched" for no real reason.
    """
    if not text:
        return None
    stripped = text.lstrip("\ufeff").lstrip("\r\n")
    match = FM_RE.match(stripped)
    if not match:
        return None
    block = match.group(1)
    try:
        meta = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    name = meta.get("name")
    description = meta.get("description")
    return {
        "name": name.strip() if isinstance(name, str) else None,
        "description": description.strip() if isinstance(description, str) else None,
        "meta": meta,
        "body": stripped[match.end():],
    }


def dedupe_skills(entries: Iterable[dict[str, Any]], repo_name: str) -> list[dict[str, Any]]:
    """Collapse the per-harness/per-locale copies of one skill into one record."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        name = skill_name_from_path(entry["path"], repo_name)
        groups[name.strip().lower()].append(entry)

    records: list[dict[str, Any]] = []
    for key, group in groups.items():
        ordered = sorted(
            group,
            key=lambda item: (
                bool(locale_of(item["path"])),          # canonical locale first
                layout_rank(layout_of(item["path"])),    # canonical layout first
                len(item["path"]),                       # then shortest path
            ),
        )
        canonical = ordered[0]
        # Store only what the pipeline and the pages use. Paths, shas, and
        # per-copy layout lists were ~80% of the 6.5 MB census and nothing reads
        # them after enumeration; copy count is the part that matters.
        records.append(
            {
                "name": skill_name_from_path(canonical["path"], repo_name),
                "copies": len(group),
            }
        )
    return sorted(records, key=lambda record: record["name"].lower())


def slim_repo_skills(repos: dict[str, dict[str, Any]]) -> None:
    """Normalize cached inventories to the compact shape.

    A schema bump or an older artifact can still carry per-skill paths and shas;
    dropping them here keeps the committed census small without waiting for the
    next tree change.
    """
    for repo in repos.values():
        skills = repo.get("skills") or []
        if skills and any(set(skill) - {"name", "copies"} for skill in skills):
            repo["skills"] = [
                {"name": skill.get("name"), "copies": int(skill.get("copies") or 1)}
                for skill in skills
            ]


def layout_rank(layout: str) -> int:
    """Prefer the plain ``skills/`` copy when a repo vendors several."""
    if layout == "skills":
        return 0
    if layout == "root":
        return 1
    if layout.startswith("."):
        return 2
    return 3


def skill_name_set(skills: Iterable[dict[str, Any]]) -> set[str]:
    return {str(skill.get("name", "")).strip().lower() for skill in skills if skill.get("name")}


def containment(a: set[str], b: set[str]) -> float:
    """Share of the smaller inventory present in the larger one.

    Jaccard punishes a port that adds skills; containment does not, which is why
    it identifies `pstack` ports at 0.90-1.00 while Jaccard on descriptions was
    useless.
    """
    if not a or not b:
        return 0.0
    smaller = min(len(a), len(b))
    return len(a & b) / smaller if smaller else 0.0


# --------------------------------------------------------------------------- #
# capability + lens
# --------------------------------------------------------------------------- #


def strip_harness(text: str, harness_tokens: Iterable[str]) -> str:
    lowered = text or ""
    for token in sorted(harness_tokens, key=len, reverse=True):
        lowered = re.sub(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", " ", lowered, flags=re.I)
    return re.sub(r"\s+", " ", lowered).strip()


def classify_capability(name: str, description: str, taxonomy: list[dict[str, Any]],
                        harness_tokens: Iterable[str] = ()) -> tuple[str | None, float]:
    """Keyword fallback. Returns ``(slug, matched_keywords)``.

    Skill names are kebab-case (``code-review``) while taxonomy keywords are
    phrases (``code review``), so separators are normalized before matching.
    """
    raw = f"{name} {description or ''}".lower().replace("-", " ").replace("_", " ")
    text = strip_harness(raw, harness_tokens).lower()
    if not text:
        return None, 0.0
    best: tuple[str | None, float] = (None, 0.0)
    for bucket in taxonomy:
        # Word boundaries, not substring: "memo" matched "memory" and "paper"
        # matched "paperclip", which put a forensic skill in docs-files and a
        # bundled-clipboard skill in research.
        hits = sum(
            1
            for keyword in bucket.get("keywords") or []
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])", text)
        )
        if hits <= 0:
            continue
        audience = float(bucket.get("audience", 0.5))
        score = hits + audience  # tie-break towards the more on-lens capability
        if score > best[1]:
            best = (str(bucket["slug"]), float(hits))
    return best


def lens_tier(audience: float, lens_cfg: dict[str, Any]) -> str:
    if audience >= float(lens_cfg.get("core_min", 0.8)):
        return "core"
    if audience >= float(lens_cfg.get("adjacent_min", 0.5)):
        return "adjacent"
    return "off"


def capability_weight(cfg: dict[str, Any], slug: str | None) -> float:
    for bucket in cfg.get("capabilities", {}).get("taxonomy") or []:
        if bucket.get("slug") == slug:
            return float(bucket.get("audience", 0.0))
    return 0.0


def assign_capabilities(
    skills: list[dict[str, Any]],
    cfg: dict[str, Any],
    cache: dict[str, Any] | None = None,
    llm_assigner=None,
) -> tuple[Counter, dict[str, Any]]:
    """Assign one primary capability per skill; keywords, LLM cache first."""
    taxonomy = cfg.get("capabilities", {}).get("taxonomy") or []
    harness_tokens = cfg.get("capabilities", {}).get("harness_tokens") or []
    cache = cache if cache is not None else {}
    counts: Counter = Counter()
    pending: list[dict[str, Any]] = []

    for skill in skills:
        text_key = hashlib.sha256(
            f"{skill.get('name','')}|{skill.get('description','')}".encode("utf-8")
        ).hexdigest()[:16]
        cached = cache.get(text_key)
        if cached and cached.get("capability"):
            slug, source = cached["capability"], cached.get("source", "llm")
        else:
            slug, hits = classify_capability(
                skill.get("name", ""), skill.get("description", ""), taxonomy, harness_tokens
            )
            source = "keywords" if slug else "none"
            if not slug and llm_assigner:
                pending.append({"key": text_key, "skill": skill})
        skill["capability"] = slug
        skill["capability_source"] = source
        skill["lens"] = lens_tier(capability_weight(cfg, slug), cfg.get("capabilities", {}).get("lens", {}))
        counts[slug or "uncategorized"] += 1

    if pending and llm_assigner:
        for key, result in llm_assigner(pending).items():
            cache[key] = {"capability": result, "source": "llm", "at": utc_now().isoformat()}
        for item in pending:
            assigned = cache.get(item["key"], {}).get("capability")
            if assigned:
                item["skill"]["capability"] = assigned
                item["skill"]["capability_source"] = "llm"
                item["skill"]["lens"] = lens_tier(
                    capability_weight(cfg, assigned), cfg.get("capabilities", {}).get("lens", {})
                )
                counts["uncategorized"] -= 1
                counts[assigned] += 1

    return counts, cache


def openrouter_assigner(cfg: dict[str, Any]):
    """Return a batched, taxonomy-constrained classifier, or None.

    Deliberately small: one chat completion per batch, the taxonomy enum in the
    prompt, JSON out. ``judge.py`` is a scoring client, not a generic completion
    helper, so the call lives here with the same cache discipline.
    """
    llm_cfg = (cfg.get("capabilities", {}).get("llm") or {})
    model = (llm_cfg.get("model") or "").strip()
    api_key = os.environ.get((llm_cfg.get("api_key_env") or "OPENROUTER_API_KEY"), "")
    if not llm_cfg.get("enabled") or not model or not api_key:
        return None
    slugs = [bucket["slug"] for bucket in cfg.get("capabilities", {}).get("taxonomy") or []]
    batch_size = int(llm_cfg.get("batch_size", 40))
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def assigner(pending: list[dict[str, Any]]) -> dict[str, str]:
        results: dict[str, str] = {}
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            items = [
                {"i": idx, "skill": item["skill"].get("name"), "description": (item["skill"].get("description") or "")[:500]}
                for idx, item in enumerate(batch)
            ]
            prompt = (
                "Assign exactly one capability slug to each agent skill. "
                f"Allowed slugs: {', '.join(slugs)}. "
                "Answer with JSON only: {\"assignments\":[{\"i\":0,\"slug\":\"...\"}]}"
            )
            try:
                resp = session.post(
                    f"{(llm_cfg.get('base_url') or '').rstrip('/')}/chat/completions",
                    json={
                        "model": model,
                        "temperature": 0,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": json.dumps(items)},
                        ],
                    },
                    timeout=90,
                )
                if resp.status_code != 200:
                    print(f"skills_capability_llm_failed status={resp.status_code}")
                    continue
                content = resp.json()["choices"][0]["message"]["content"]
                match = re.search(r"\{.*\}", content, re.S)
                payload = json.loads(match.group(0)) if match else {}
                for entry in payload.get("assignments") or []:
                    idx = int(entry.get("i", -1))
                    slug = entry.get("slug")
                    if 0 <= idx < len(batch) and slug in slugs:
                        results[batch[idx]["key"]] = slug
            except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
                print(f"skills_capability_llm_failed detail={type(exc).__name__}")
        return results

    return assigner


# --------------------------------------------------------------------------- #
# families
# --------------------------------------------------------------------------- #


def explicit_family_target(
    repo_name: str,
    repo: dict[str, Any],
    repos: dict[str, dict[str, Any]],
    stopwords: Iterable[str] = (),
    min_len: int = 3,
) -> str | None:
    """A repo that this one explicitly says it came from.

    Needed because `gstack` ports rename or strip their skill dirs, so content
    overlap is 0 even though the port is real. Matching is deliberately strict:
    plain substring matching merged `morluto/rea` with anything whose description
    contained "rea" (inside "create", "already"), and matched the word "skills"
    as a repo name.
    """
    text = (repo.get("description") or "").lower()
    if not text.strip():
        return None
    blocked = {str(word).lower() for word in stopwords}
    derived = bool(DERIVATION_RE.search(text))
    strong: str | None = None
    loose: list[str] = []
    for other in sorted(repos):
        if other == repo_name:
            continue
        owner, _, short = other.lower().partition("/")
        if len(short) < min_len or short in blocked:
            continue
        if f"{owner}/{short}" in text:
            strong = strong or other
            continue
        if not derived:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(short)}(?![a-z0-9])", text):
            loose.append(other)
    if strong:
        return strong
    return max(loose, key=lambda name: repos[name].get("stars") or 0) if loose else None


def build_families(
    repos: dict[str, dict[str, Any]],
    threshold: float = 0.30,
    min_skills: int = 3,
    max_created_gap_days: int = 450,
    min_shared: int = 3,
    max_inventory_ratio: float = 4.0,
    stopwords: Iterable[str] = (),
    min_reference_len: int = 3,
) -> dict[str, Any]:
    """Cluster repos that are the same concept.

    Membership is content overlap (shared skill names) or an explicit pointer.
    A shared name never suffices: ``pstack`` is also a 2012 C stack-trace tool.
    """
    names = sorted(repos)
    parent = {name: name for name in names}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    skill_sets = {name: skill_name_set(repos[name].get("skills") or []) for name in names}
    name_tokens = {name: short_name_tokens(name, stopwords) for name in names}

    for i, left in enumerate(names):
        set_left = skill_sets[left]
        if len(set_left) < min_skills:
            continue
        created_left = parse_dt(repos[left].get("created_at"))
        for right in names[i + 1:]:
            set_right = skill_sets[right]
            if len(set_right) < min_skills:
                continue
            if not (name_tokens[left] & name_tokens[right]):
                continue
            shared = len(set_left & set_right)
            # A three-skill repo is a subset of almost anything, so containment
            # alone would fold the whole ecosystem into a mega-collection.
            # Require real overlap and comparable inventory sizes.
            if shared < min_shared or containment(set_left, set_right) < threshold:
                continue
            if max(len(set_left), len(set_right)) > max_inventory_ratio * min(len(set_left), len(set_right)):
                continue
            created_right = parse_dt(repos[right].get("created_at"))
            if created_left and created_right and abs((created_left - created_right).days) > max_created_gap_days:
                continue
            union(left, right)

    # Explicit pointers join repos whose skills were renamed (gstack ports) or
    # that ship no skill files at all (plugin wrappers). Content overlap is not
    # required for these, because a wrapper's inventory is legitimately empty.
    for name in names:
        target = explicit_family_target(
            name, repos[name], repos, stopwords=stopwords, min_len=min_reference_len
        )
        if target:
            union(name, target)

    clusters: dict[str, list[str]] = defaultdict(list)
    for name in names:
        clusters[find(name)].append(name)

    families: dict[str, Any] = {}
    for members in clusters.values():
        lead = max(members, key=lambda name: (repos[name].get("stars") or 0, name))
        family_id = slugify(lead)
        families[family_id] = {
            "id": family_id,
            "lead": lead,
            "members": sorted(members, key=lambda name: -(repos[name].get("stars") or 0)),
            "stars": sum(int(repos[name].get("stars") or 0) for name in members),
            "forks": sum(int(repos[name].get("forks") or 0) for name in members),
            "unique_skills": len({skill for name in members for skill in skill_sets[name]}),
            "created_at": min(
                (repos[name].get("created_at") for name in members if repos[name].get("created_at")),
                default=None,
            ),
            "pushed_at": max(
                (repos[name].get("pushed_at") for name in members if repos[name].get("pushed_at")),
                default=None,
            ),
            "practitioner": lead.split("/", 1)[0],
        }
    return families


def strict_ports(
    family: dict[str, Any],
    repos: dict[str, dict[str, Any]],
    stopwords: Iterable[str] = (),
    threshold: float = 0.30,
) -> list[str]:
    """Members that really re-implement the lead.

    Union-find chains through explicit pointers, so a family can collect a repo
    that only mentions the concept. Ports are counted against the lead: shared
    name token, content overlap, or a direct pointer at the lead.
    """
    lead = family.get("lead")
    lead_repo = repos.get(lead) or {}
    lead_skills = skill_name_set(lead_repo.get("skills") or [])
    lead_tokens = short_name_tokens(lead or "", stopwords)
    ports: list[str] = []
    for member in family.get("members") or []:
        if member == lead or member not in repos:
            continue
        member_skills = skill_name_set(repos[member].get("skills") or [])
        shares_name = bool(lead_tokens & short_name_tokens(member, stopwords))
        shares_content = containment(lead_skills, member_skills) >= threshold
        points_at_lead = explicit_family_target(
            member, repos[member], {lead: lead_repo}, stopwords=stopwords
        ) == lead
        if shares_name or shares_content or points_at_lead:
            ports.append(member)
    return ports


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #


def discovery_queries(cfg: dict[str, Any], family_names: Iterable[str] = ()) -> list[tuple[str, str]]:
    """``(channel, query)`` pairs. Every channel is best-effort recall."""
    discovery = cfg.get("discovery") or {}
    queries: list[tuple[str, str]] = []

    momentum = discovery.get("momentum") or {}
    since = momentum.get("created_after")
    for band in momentum.get("bands") or []:
        queries.append(("momentum", f"created:>{since} {band}"))
    if not momentum.get("bands") and since:
        queries.append(("momentum", f"created:>{since} stars:>={int(momentum.get('min_stars', 300))}"))

    for topic in discovery.get("topics") or []:
        queries.append(("topic", f"topic:{topic} stars:>={int(discovery.get('topic_min_stars', 20))}"))

    for name in dict.fromkeys(family_names):
        if len(name) >= 4:
            queries.append(("family", f"{name} in:name"))
    return queries


def candidate_pool(
    client: GitHubClient, cfg: dict[str, Any], family_names: Iterable[str] = ()
) -> dict[str, set[str]]:
    discovery = cfg.get("discovery") or {}
    pages = {
        "momentum": int((discovery.get("momentum") or {}).get("max_pages_per_band", 10)),
        "topic": int(discovery.get("max_pages_per_topic", 3)),
        "family": int((discovery.get("family") or {}).get("max_pages", 3)),
    }
    pool: dict[str, dict[str, Any]] = {}

    def add(name: str, channel: str, stars: int = 0) -> None:
        entry = pool.setdefault(name, {"channels": set(), "stars": 0})
        entry["channels"].add(channel)
        entry["stars"] = max(entry["stars"], int(stars or 0))

    for channel, query in discovery_queries(cfg, family_names):
        for item in client.search_repos(query, max_pages=pages.get(channel, 3)):
            name = item.get("full_name")
            if name:
                add(name, channel, item.get("stargazers_count") or 0)
    for seed in discovery.get("seed_repos") or []:
        add(seed, "seed")
    return pool


def short_name_tokens(full_name: str, stopwords: Iterable[str] = ()) -> set[str]:
    """Distinctive tokens of a repo's short name.

    Content overlap alone merged unrelated repos, because a handful of skill
    names (`plan`, `review`, `test`) appear everywhere. Requiring a shared name
    token before trusting content overlap is how `pstack`/`pstack-claude` cluster
    while `anthropics/skills` does not absorb `morluto/rea`.
    """
    short = full_name.rsplit("/", 1)[-1].lower()
    blocked = {str(word).lower() for word in stopwords}
    return {token for token in re.split(r"[-_.]", short) if len(token) >= 4 and token not in blocked}


HARNESS_SUFFIX_RE = re.compile(
    r"-(claude|codex|pi|cursor|copilot|gemini|hermes|openclaw|port|skills?|plugin|t3|omp|dsh|zcode|team)$",
    re.I,
)


def family_sweep_names(repos: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    """Names worth a ``<name> in:name`` sweep, most substantial first.

    Uses the whole short repo name, not every hyphen token: splitting turned
    `Egonex-AI/Understand-Anything` into `understand` and `anything` and spent a
    search on each. A trailing harness suffix is stripped, because that is the
    shape of a port (`pstack-claude` -> `pstack`).
    """
    family_cfg = (cfg.get("discovery") or {}).get("family") or {}
    stopwords = {str(word).lower() for word in family_cfg.get("stopwords") or []}
    max_names = int(family_cfg.get("max_names", 20))
    scored: dict[str, float] = {}
    for name, repo in repos.items():
        short = name.rsplit("/", 1)[-1].lower()
        token = HARNESS_SUFFIX_RE.sub("", short)
        if len(token) < 4 or token in stopwords:
            continue
        inventory = len({str(skill.get("name", "")).lower() for skill in repo.get("skills") or []})
        if not inventory:
            continue
        score = log_scale(repo.get("stars") or 0) * math.sqrt(inventory)
        scored[token] = max(scored.get(token, 0.0), score)
    return [token for token, _ in sorted(scored.items(), key=lambda item: -item[1])[:max_names]]


# --------------------------------------------------------------------------- #
# collection
# --------------------------------------------------------------------------- #


def normalize_repo(item: dict[str, Any]) -> dict[str, Any]:
    owner = (item.get("owner") or {}).get("login") or (item.get("full_name") or "/").split("/")[0]
    return {
        "id": item.get("id"),
        "full_name": item.get("full_name"),
        "owner": owner,
        "description": (item.get("description") or "").strip(),
        "stars": int(item.get("stargazers_count") or 0),
        "forks": int(item.get("forks_count") or 0),
        "open_issues": int(item.get("open_issues_count") or 0),
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")),
        "license": (item.get("license") or {}).get("spdx_id"),
        "topics": item.get("topics") or [],
        "default_branch": item.get("default_branch"),
    }


def inventory_from_tree(
    tree: list[dict[str, Any]], repo_name: str, max_skills: int,
    exclude_parts: Iterable[str] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    entries = [
        {"path": entry.get("path", ""), "sha": entry.get("sha")}
        for entry in tree
        if is_skill_path(entry.get("path", ""))
        and not is_excluded_path(entry.get("path", ""), exclude_parts)
    ]
    records = dedupe_skills(entries, repo_name)
    meta = {
        "skill_files": len(entries),
        "unique_skills": len(records),
        # Layout and locale stay at the repo level: they describe how the repo
        # ships, and the per-copy detail is not worth the bytes.
        "layouts": sorted({layout_of(entry["path"]) for entry in entries}),
        "locales": sorted({loc for loc in (locale_of(entry["path"]) for entry in entries) if loc}),
        "truncated": len(records) > max_skills,
    }
    return records[:max_skills], meta


def collect(cfg: dict[str, Any], client: GitHubClient, limit: int | None = None,
            now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    today = utc_date(now)
    previous = read_json(DATA_DIR / "repos.json", {}) or {}
    previous_repos = previous.get("repos") or {}
    # A schema change invalidates cached inventories, because a 304 reuses them.
    same_schema = previous.get("schema_version") == SCHEMA_VERSION
    history = read_json(HISTORY_DIR / f"{today}.json", {}) or {}

    pool = candidate_pool(client, cfg, family_names=previous.get("family_names") or [])
    max_repos = int((cfg.get("discovery") or {}).get("max_repos_per_run", 1200))
    # Multi-channel repos first: those are the ones two independent sweeps agree on.
    ordered = sorted(
        pool, key=lambda name: (-len(pool[name]["channels"]), -pool[name]["stars"], name)
    )[: limit or max_repos]

    filters = cfg.get("filters") or {}
    max_skills = int((cfg.get("discovery") or {}).get("max_skills_per_repo", 400))
    repos: dict[str, dict[str, Any]] = {}
    skipped = Counter()

    for index, full_name in enumerate(ordered, 1):
        cached = previous_repos.get(full_name) or {}
        meta = client.repo(full_name)
        if meta is None:
            skipped["unavailable"] += 1
            if cached:
                cached.setdefault("first_seen", today)
                cached.setdefault("skills", [])
                repos[full_name] = cached
            continue

        record = normalize_repo(meta)
        if filters.get("exclude_archived", True) and record["archived"]:
            skipped["archived"] += 1
            continue
        if filters.get("exclude_forks", True) and record["fork"]:
            skipped["fork"] += 1
            continue

        record["first_seen"] = cached.get("first_seen") or today
        record["last_seen"] = today
        record["discovered_via"] = sorted(
            set(cached.get("discovered_via") or []) | set((pool.get(full_name) or {}).get("channels") or [])
        )
        tree = client.tree(full_name, record.get("default_branch"), conditional=same_schema)
        if tree is not None:
            skills, inventory = inventory_from_tree(
                tree, full_name, max_skills,
                exclude_parts=(cfg.get("filters") or {}).get("exclude_path_parts") or [],
            )
            record.update(inventory)
            record["skills"] = skills
            record["inventory_at"] = today
        else:
            # 304: the tree is unchanged, so the cached inventory is current.
            record["skills"] = cached.get("skills") or []
            record["skill_files"] = cached.get("skill_files", len(record["skills"]))
            record["unique_skills"] = cached.get("unique_skills", len(record["skills"]))
            record["layouts"] = cached.get("layouts") or []
            record["truncated"] = cached.get("truncated", False)
            record["inventory_at"] = cached.get("inventory_at", today)
        repos[full_name] = record

        if index % 50 == 0:
            print(f"skills_collect_progress repos={index} total={len(ordered)}")

    families = rebuild_artifacts(repos, cfg, now=now, history=history)
    skills = [dict(skill, repo=name, repo_id=repos[name].get("id"))
              for name, repo in repos.items() for skill in repo.get("skills") or []]
    inventory = sum(int(repo.get("unique_skills") or 0) for repo in repos.values())
    print(
        f"skills_collect_ok repos={len(repos)} skills={len(skills)} inventory={inventory} "
        f"families={len(families)} skipped={dict(skipped)} "
        f"requests={client.requests_made} not_modified={client.not_modified}"
    )
    return {"repos": repos, "families": families, "skills": skills, "generated_at": now.isoformat()}


def rebuild_artifacts(
    repos: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
    now: datetime | None = None,
    history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute families and rewrite artifacts without touching the network.

    Split out of ``collect`` so family/ranking tuning does not require a 20-minute
    GitHub run: ``rebuild`` replays the stored census offline.
    """
    now = now or utc_now()
    today = utc_date(now)
    slim_repo_skills(repos)
    repos = prune_repos(repos, now, cfg)
    prune_history(now, cfg)
    families_cfg = (cfg.get("discovery") or {}).get("family") or {}
    families = build_families(
        repos,
        threshold=float(families_cfg.get("min_shared_skills", 0.30)),
        min_skills=int(families_cfg.get("min_skills_to_compare", 3)),
        max_created_gap_days=int(families_cfg.get("max_created_gap_days", 450)),
        max_inventory_ratio=float(families_cfg.get("max_inventory_ratio", 4.0)),
        stopwords=families_cfg.get("stopwords") or [],
        min_reference_len=int(families_cfg.get("min_reference_len", 3)),
    )
    family_names = family_sweep_names(repos, cfg)

    if history is not None:
        for name in repos:
            history[name] = {
                "stars": repos[name].get("stars", 0),
                "forks": repos[name].get("forks", 0),
                "skills": repos[name].get("unique_skills", 0),
            }
        write_json(HISTORY_DIR / f"{today}.json", history)

    write_json(
        DATA_DIR / "repos.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "family_names": sorted(set(family_names)),
            "repos": repos,
        },
    )
    write_json(
        DATA_DIR / "families.json",
        {"schema_version": SCHEMA_VERSION, "generated_at": now.isoformat(), "families": families},
    )
    return families


# --------------------------------------------------------------------------- #
# board
# --------------------------------------------------------------------------- #


def prune_repos(repos: dict[str, dict[str, Any]], now: datetime,
                cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Drop repos nobody has seen in a while.

    Without this the census is append-only: a repo discovered once stays in the
    committed artifact forever even after it drops out of every sweep.
    """
    keep_days = int(((cfg.get("discovery") or {}).get("retention_days") or 45))
    cutoff = (now.date() - timedelta(days=keep_days)).isoformat()
    return {
        name: repo for name, repo in repos.items()
        if (repo.get("last_seen") or repo.get("first_seen") or "") >= cutoff
    }


def prune_history(now: datetime, cfg: dict[str, Any], keep_days: int | None = None) -> int:
    """Keep a bounded number of daily star snapshots.

    Velocity needs a 7-day baseline; the shelf decay window needs a few weeks.
    Everything older is history for its own sake and would grow the repo forever.
    """
    keep_days = keep_days or int(((cfg.get("discovery") or {}).get("history_retention_days") or 90))
    cutoff = (now.date() - timedelta(days=keep_days)).isoformat()
    removed = 0
    try:
        for path in HISTORY_DIR.glob("*.json"):
            if path.stem < cutoff:
                path.unlink()
                removed += 1
    except OSError:
        pass
    return removed


def log_scale(value: float, floor: float = 1.0) -> float:
    return math.log10(max(float(value or 0), floor))


def percentile_map(values: dict[str, float]) -> dict[str, float]:
    """Rank-normalize to 0..1 so units (stars vs days) are comparable."""
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1])
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}  # the only candidate is the best by definition
    total = len(ordered) - 1
    # Ties share their average rank. Without this, twelve practitioners with
    # 0 ports spread across the whole 0..1 range by dict order, which is how
    # 0-port entries outranked ones with real ports.
    ranks: dict[float, list[int]] = defaultdict(list)
    for index, (_, value) in enumerate(ordered):
        ranks[value].append(index)
    percentiles: dict[str, float] = {}
    for key, value in ordered:
        positions = ranks[value]
        percentiles[key] = sum(positions) / len(positions) / total
    return percentiles


def velocity(history: dict[str, Any], full_name: str, now: datetime, days: int = 7) -> float | None:
    """Star delta over the trailing window, from dated snapshots.

    ``history`` is ``{date: {full_name: {stars, forks, skills}}}``. The baseline
    is the newest snapshot at or before the target date, so a missed run on a
    quiet day does not zero the whole board.
    """
    dates = sorted(history or {})
    if not dates:
        return None
    today = now.date().isoformat()
    current_dates = [key for key in dates if key <= today]
    if not current_dates:
        return None
    current = (history[current_dates[-1]] or {}).get(full_name)
    if not current:
        return None
    target = (now.date() - timedelta(days=days)).isoformat()
    baseline_dates = [key for key in dates if key <= target]
    if not baseline_dates:
        return None
    baseline = (history[baseline_dates[-1]] or {}).get(full_name)
    if not baseline:
        return None
    return float(current.get("stars", 0)) - float(baseline.get("stars", 0))


def family_records(
    repos: dict[str, dict[str, Any]],
    families: dict[str, Any],
    history: dict[str, Any],
    cfg: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    penalties = (cfg.get("ranking") or {}).get("penalties") or {}
    aggregated_threshold = int((cfg.get("filters") or {}).get("aggregated_inventory_threshold", 200))
    stale_days = int(((cfg.get("ranking") or {}).get("shelf") or {}).get("stale_days", 90))
    spread_window = int(((cfg.get("ranking") or {}).get("rising") or {}).get("family_spread_window_days", 30))

    leads: dict[str, int] = Counter()
    for family in families.values():
        leads[family["practitioner"]] += 1

    records: list[dict[str, Any]] = []
    for family in families.values():
        members = [repos[name] for name in family["members"] if name in repos]
        if not members:
            continue
        lead = repos[family["lead"]]
        unique_skills = len({skill["name"].lower() for member in members for skill in member.get("skills") or []})
        stars = sum(int(member.get("stars") or 0) for member in members)
        forks = sum(int(member.get("forks") or 0) for member in members)
        pushed = parse_dt(family.get("pushed_at"))
        if unique_skills == 0:
            continue  # a pointer list or plugin wrapper is a family reference, not a card
        created = parse_dt(family.get("created_at"))
        age_days = (now - created).days if created else None
        idle_days = (now - pushed).days if pushed else None
        recent_ports = [
            member for member in members
            if member.get("full_name") != family["lead"]
            and (created_at := parse_dt(member.get("created_at")))
            and (now - created_at).days <= spread_window
        ]
        lead_created = parse_dt(lead.get("created_at"))
        new_lead = bool(lead_created and (now - lead_created).days <= spread_window)
        capability_counts = Counter(
            skill.get("capability")
            for member in members
            for skill in member.get("skills") or []
            if skill.get("capability")
        )
        vel = 0.0
        has_velocity = False
        for member in members:
            member_velocity = velocity(history, member["full_name"], now)
            if member_velocity is not None:
                vel += member_velocity
                has_velocity = True
        strict_members = strict_ports(
            family, repos, stopwords=(cfg.get("discovery") or {}).get("family", {}).get("stopwords") or []
        )
        licenses = {member.get("license") for member in members}
        record = {
            "id": family["id"],
            "lead": family["lead"],
            "practitioner": family["practitioner"],
            "members": family["members"],
            "member_count": len(family["members"]),
            "ports": len(strict_members),
            "stars": stars,
            "forks": forks,
            "fork_ratio": round(forks / stars, 4) if stars else 0.0,
            "unique_skills": unique_skills,
            "capabilities": sorted(capability_counts),
            "dominant_capability": capability_counts.most_common(1)[0][0] if capability_counts else None,
            "layouts": sorted({layout for member in members for layout in member.get("layouts") or []}),
            "age_days": age_days,
            "idle_days": idle_days,
            "velocity_7d": vel if has_velocity else None,
            "recent_ports": len(recent_ports),
            "new_lead": new_lead,
            "first_seen": min((member.get("first_seen") or "9999") for member in members),
            "aggregated": unique_skills >= aggregated_threshold,
            "no_license": not any(lic and lic != "NOASSERTION" for lic in licenses),
            "stale": bool(idle_days is not None and idle_days > stale_days),
            "practitioner_setups": leads[family["practitioner"]],
        }
        record["lens"] = family_lens_tier(members, cfg)
        record["penalty"] = round(
            (penalties.get("no_license", 0) if record["no_license"] else 0)
            + (penalties.get("aggregated_inventory", 0) if record["aggregated"] else 0)
            + (penalties.get("stale", 0) if record["stale"] else 0),
            4,
        )
        records.append(record)
    return records


def novelty_score(first_seen: str | None, now: datetime) -> float:
    parsed = parse_dt(first_seen)
    if not parsed:
        return 0.0
    return 1.0 / (1.0 + max(0, (now - parsed).days))


def apply_shelf_hysteresis(
    previous: Iterable[str], scores: dict[str, float], eligible: Iterable[str],
    entry: float = 0.35, margin: float = 0.05,
) -> set[str]:
    """Enter at ``entry``, leave only below ``entry - margin``.

    Without the margin the reference shelf fills with whatever is currently
    rising and empties again as that fades, so "reference" stops meaning
    anything.
    """
    previous_set = set(previous or ())
    kept: set[str] = set()
    for record_id in eligible:
        score = float(scores.get(record_id, 0.0))
        if record_id in previous_set:
            if score >= entry - margin:
                kept.add(record_id)
        elif score >= entry:
            kept.add(record_id)
    return kept


def normalized_scores(records: list[dict[str, Any]], weights: dict[str, float],
                      features: dict[str, dict[str, float]]) -> dict[str, float]:
    percentiles = {name: percentile_map(values) for name, values in features.items()}
    scores: dict[str, float] = {}
    for record in records:
        key = record["id"]
        scores[key] = round(
            sum(float(weights.get(name, 0)) * percentiles.get(name, {}).get(key, 0.0) for name in features)
            - record.get("penalty", 0.0),
            4,
        )
    return scores


def rank_board(repo_artifacts: dict[str, Any], cfg: dict[str, Any], now: datetime | None = None,
               llm_assigner=None) -> dict[str, Any]:
    now = now or utc_now()
    today = utc_date(now)
    repos = repo_artifacts.get("repos") or {}
    families = repo_artifacts.get("families") or {}
    history = load_latest_history(now.date())

    # Assign here rather than trusting the caller: a board grouped by capability
    # is meaningless if the artifacts were written without labels.
    skills = [skill for repo in repos.values() for skill in repo.get("skills") or []]
    cache_path = DATA_DIR / "capability_cache.json"
    cache = read_json(cache_path, {}) or {}
    _, cache = assign_capabilities(skills, cfg, cache=cache, llm_assigner=llm_assigner)
    write_json(cache_path, cache)

    records = family_records(repos, families, history, cfg, now)
    # The lens gate is an admission gate, not a ranking weight: a marketing-skill
    # bundle must not win 'testing' because it also ships a test helper.
    off_lens = [record["id"] for record in records if record.get("lens") == "off"]
    records = [record for record in records if record.get("lens") != "off"]
    if not records:
        return {"schema_version": SCHEMA_VERSION, "generated_at": now.isoformat(), "lanes": {}, "capabilities": []}

    ranking = cfg.get("ranking") or {}
    rising_cfg, shelf_cfg, practitioner_cfg = (
        ranking.get("rising") or {}, ranking.get("shelf") or {}, ranking.get("practitioners") or {}
    )

    rising_scores = normalized_scores(
        records,
        rising_cfg.get("weights") or {},
        {
            "velocity": {record["id"]: float(record.get("velocity_7d") or 0) for record in records},
            "family_spread": {record["id"]: float(record.get("recent_ports") or 0) for record in records},
            "family_momentum": {record["id"]: log_scale(record["stars"]) / math.sqrt(max(1, record["unique_skills"]))
                                for record in records},
            "novelty": {record["id"]: novelty_score(record.get("first_seen"), now) for record in records},
        },
    )

    fork_cap = float(shelf_cfg.get("fork_ratio_cap", 0.25))
    shelf_eligible = [
        record for record in records
        if record.get("age_days") is None or record["age_days"] >= int(shelf_cfg.get("min_age_days", 30))
        or (record["stars"] >= int(shelf_cfg.get("min_stars", 1000))
            and record["fork_ratio"] >= float(shelf_cfg.get("min_fork_ratio", 0.04)))
    ]
    shelf_scores = normalized_scores(
        shelf_eligible,
        shelf_cfg.get("weights") or {},
        {
            "adoption": {record["id"]: log_scale(record["stars"] + record["forks"]) for record in shelf_eligible},
            "fork_ratio": {record["id"]: min(record["fork_ratio"], fork_cap) for record in shelf_eligible},
            "durability": {record["id"]: float(min(record.get("age_days") or 0, 730)) for record in shelf_eligible},
            # Cap the inventory term: one repo shipped 18,980 SKILL.md files and
            # would top the shelf on size alone.
            "breadth": {record["id"]: min(record["unique_skills"], 50)
                        + 2 * len(record["layouts"]) + record["ports"]
                        for record in shelf_eligible},
            "practitioner": {record["id"]: record.get("practitioner_setups", 0) for record in shelf_eligible},
        },
    )

    practitioner_scores = normalized_scores(
        records,
        practitioner_cfg.get("weights") or {},
        {
            "port_count": {record["id"]: float(record["ports"]) for record in records},
            "aggregate_adoption": {record["id"]: log_scale(record["stars"]) for record in records},
            "breadth": {record["id"]: min(record["unique_skills"], 50) for record in records},
            "recency": {record["id"]: float(max(0, 365 - (record.get("idle_days") or 365))) for record in records},
        },
    )

    # Hysteresis: a shelf entry leaves only after its score decays past the margin,
    # so a quiet week does not empty the reference shelf.
    state_path = DATA_DIR / "state.json"
    state = read_json(state_path, {}) or {}
    margin = float((ranking.get("hysteresis") or {}).get("shelf_exit_margin", 0.05))
    previous_shelf = set((state.get("shelf") or {}).keys())
    shelf_members = apply_shelf_hysteresis(
        previous_shelf,
        shelf_scores,
        [record["id"] for record in shelf_eligible],
        entry=float(shelf_cfg.get("min_score", 0.35)),
        margin=margin,
    )
    state["shelf"] = {
        record_id: {"score": shelf_scores.get(record_id, 0.0), "at": today}
        for record_id in shelf_members
    }
    write_json(state_path, state)

    by_id = {record["id"]: record for record in records}
    rising_pool = [
        record for record in records
        if record["id"] not in shelf_members
        and record["id"] in rising_scores
        and (record.get("velocity_7d") is not None or record.get("recent_ports") or record.get("new_lead"))
    ]
    rising = sorted(
        (record["id"] for record in rising_pool), key=lambda record_id: -rising_scores[record_id]
    )[: int(rising_cfg.get("size", 12))]
    shelf = sorted(shelf_members, key=lambda record_id: -shelf_scores.get(record_id, 0.0))[: int(shelf_cfg.get("size", 24))]
    practitioners = sorted(practitioner_scores, key=lambda record_id: -practitioner_scores[record_id])[
        : int(practitioner_cfg.get("size", 12))
    ]

    def lane_entry(record_id: str, score: float, lane: str) -> dict[str, Any]:
        record = dict(by_id[record_id])
        record["score"] = round(float(score), 4)
        record["lane"] = lane
        record["reason"] = reason_string(record, lane)
        return record

    # Capability groups require name-level evidence: at least
    # `capabilities.min_matching_skills` skills in the family whose *name* says so.
    # This is the deterministic gate that replaced the per-group "provisional"
    # caveat. It removes the finance skill whose text mentioned "coverage" from
    # memory-context, and a single stray "onboarding" from codebase-navigation.
    taxonomy = cfg.get("capabilities", {}).get("taxonomy") or []
    harness_tokens = cfg.get("capabilities", {}).get("harness_tokens") or []
    min_matches = int((cfg.get("capabilities") or {}).get("min_matching_skills", 2))

    buckets: dict[str, list[tuple[int, dict[str, Any], list[dict[str, Any]]]]] = defaultdict(list)
    for record in shelf_eligible:
        if record.get("aggregated"):
            continue
        for capability in record["capabilities"]:
            matches = capability_name_matches(repos, record, capability, taxonomy, harness_tokens)
            if len(matches) >= min_matches:
                buckets[capability].append((len(matches), record, matches))

    capability_order = sorted(
        buckets,
        key=lambda capability: (
            -capability_weight(cfg, capability),
            -max(shelf_scores.get(record["id"], 0.0) for _, record, _ in buckets[capability]),
        ),
    )
    capabilities: list[dict[str, Any]] = []
    used_families: set[str] = set()
    for capability in capability_order:
        tier = lens_tier(capability_weight(cfg, capability), cfg.get("capabilities", {}).get("lens", {}))
        if tier == "off":
            continue
        # Strongest evidence first (most name-matching skills), then shelf score.
        # Focus beats volume: a 5-skill repo with 2 matching skills is a better
        # answer than a 400-skill bundle with 4. This is what surfaces vendor
        # collections (microsoft/azure-skills, openai/codex-security) over dumps.
        ranked = sorted(
            buckets[capability],
            key=lambda item: (
                -(item[0] / max(1, item[1].get("unique_skills") or 1)),
                -item[0],
                -shelf_scores.get(item[1]["id"], 0.0),
            ),
        )
        available = [
            item for item in ranked
            if item[1]["id"] not in used_families and not item[1].get("aggregated")
        ]
        if not available:
            continue
        _, representative, matches = available[0]
        used_families.add(representative["id"])
        entry = lane_entry(representative["id"], shelf_scores.get(representative["id"], 0.0), "shelf")
        entry["skill"] = matches[0]
        alternates = []
        for _, record, record_matches in available[1:3]:
            alternate = lane_entry(record["id"], shelf_scores.get(record["id"], 0.0), "shelf")
            alternate["skill"] = record_matches[0]
            alternates.append(alternate)
        capabilities.append(
            {
                "capability": capability,
                "lens": tier,
                "representative": entry,
                "alternates": alternates,
            }
        )

    board = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "lanes": {
            "rising": [lane_entry(record_id, rising_scores[record_id], "rising") for record_id in rising],
            "shelf": [lane_entry(record_id, shelf_scores.get(record_id, 0.0), "shelf") for record_id in shelf],
            "practitioners": [
                {
                    "practitioner": by_id[record_id]["practitioner"],
                    "setup": by_id[record_id]["lead"],
                    "family": record_id,
                    "ports": by_id[record_id]["ports"],
                    "stars": by_id[record_id]["stars"],
                    "unique_skills": by_id[record_id]["unique_skills"],
                    "score": practitioner_scores[record_id],
                }
                for record_id in practitioners
            ],
        },
        "capabilities": capabilities,
        "counts": {
            "records": len(records),
            "off_lens_excluded": len(off_lens),
            "capabilities": len(capabilities),
            "shelf": len(shelf),
            "rising": len(rising),
        },
    }
    write_json(DATA_DIR / "latest.json", board)
    print(
        f"skills_board_ok records={len(records)} capabilities={len(capabilities)} "
        f"shelf={len(shelf)} rising={len(rising)} practitioners={len(practitioners)}"
    )
    return board


def family_lens_tier(members: list[dict[str, Any]], cfg: dict[str, Any]) -> str:
    """Lens of a bundle, by share of its skills.

    Using the best single skill made a marketing bundle "core" because it shipped
    one test helper. A family is core only when most of what it ships is core.
    """
    lens_cfg = cfg.get("capabilities", {}).get("lens", {})
    weights = [
        capability_weight(cfg, skill.get("capability"))
        for member in members
        for skill in member.get("skills") or []
        if skill.get("capability")
    ]
    if not weights:
        return "off"
    core_share = sum(1 for weight in weights if weight >= float(lens_cfg.get("core_min", 0.8))) / len(weights)
    adjacent_share = sum(1 for weight in weights if weight >= float(lens_cfg.get("adjacent_min", 0.5))) / len(weights)
    if core_share >= 0.5:
        return "core"
    if adjacent_share >= 0.5:
        return "adjacent"
    return "off"


def capability_name_matches(
    repos: dict[str, dict[str, Any]],
    record: dict[str, Any],
    capability: str,
    taxonomy: list[dict[str, Any]],
    harness_tokens: Iterable[str],
) -> list[dict[str, Any]]:
    """Skills in the family whose *name* evidences the capability.

    Name-only on purpose: it is deterministic and testable, and it is what lets
    the board ship without a per-group caveat. Bodies are never stored, so a
    description-based check would be guesswork.
    """
    matches = []
    for member in record.get("members") or []:
        for skill in (repos.get(member) or {}).get("skills") or []:
            slug, _ = classify_capability(skill.get("name") or "", "", taxonomy, harness_tokens)
            if slug == capability:
                matches.append({"name": skill.get("name"), "repo": member})
    return sorted(matches, key=lambda skill: (skill.get("repo") or "", skill.get("name") or ""))


def reason_string(record: dict[str, Any], lane: str) -> str:
    if lane == "rising":
        parts = []
        if record.get("velocity_7d"):
            parts.append(f"+{int(record['velocity_7d'])} stars in 7d")
        if record.get("recent_ports"):
            parts.append(f"{record['recent_ports']} port repos started this month")
        if record.get("new_lead") or not parts:
            first_seen = record.get("first_seen") or "recently"
            parts.append(f"first seen {first_seen}")
        return " · ".join(parts)
    if record.get("ports"):
        return f"{record['ports']} independent ports · {record['stars']} stars combined"
    return f"{record['unique_skills']} skills · {record['stars']} stars"


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Skill Radar collector")
    parser.add_argument(
        "command", choices=["collect", "board", "rebuild", "run"], nargs="?", default="run"
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--limit", type=int, default=None, help="cap repos processed (debug)")
    parser.add_argument("--skip-llm", action="store_true", help="keywords only")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if os.environ.get("SKILLS_OFFLINE") == "1":
        print("skills_collect_skipped reason=SKILLS_OFFLINE")
        return 0

    token = github_token()
    if not token:
        print("skills_collect_failed reason=no_github_token")
        return 1
    if args.command in ("rebuild", "board"):
        payload = read_json(DATA_DIR / "repos.json", {}) or {}
        repos = payload.get("repos") or {}
        if not repos:
            print("skills_rebuild_failed reason=no_repos_artifact")
            return 1
        if args.command == "rebuild":
            families = rebuild_artifacts(repos, cfg)
            print(f"skills_rebuild_ok repos={len(repos)} families={len(families)}")
        else:
            families = (read_json(DATA_DIR / "families.json", {}) or {}).get("families") or {}
        rank_board(
            {"repos": repos, "families": families},
            cfg,
            llm_assigner=None if args.skip_llm else openrouter_assigner(cfg),
        )
        return 0

    client = GitHubClient(token, cfg)
    collect(cfg, client, limit=args.limit)
    client.save_etags()
    if args.command == "run":
        rank_board(
            {
                "repos": (read_json(DATA_DIR / "repos.json", {}) or {}).get("repos") or {},
                "families": (read_json(DATA_DIR / "families.json", {}) or {}).get("families") or {},
            },
            cfg,
            llm_assigner=None if args.skip_llm else openrouter_assigner(cfg),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
