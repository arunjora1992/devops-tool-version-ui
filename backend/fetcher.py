import asyncio
import os
import re
import time
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

_cache: dict = {}
_cache_ts: float = 0.0

RC_PATTERN = re.compile(r"(alpha|beta|rc|dev|nightly|preview|snapshot|test)", re.IGNORECASE)


def _github_headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "devops-dashboard/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _is_stable(tag: str, prerelease: bool = False) -> bool:
    if prerelease:
        return False
    return not RC_PATTERN.search(tag)


def _parse_tag(tag: str, transform: Optional[str]) -> Optional[str]:
    """Clean raw tag name to a display version string."""
    if transform == "postgres":
        # REL_17_0 → 17.0, REL_16_4 → 16.4
        m = re.match(r"REL_(\d+)_(\d+)$", tag)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        m = re.match(r"REL_(\d+)_(\d+)_(\d+)$", tag)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        return None
    if transform == "mysql":
        # mysql-8.4.2 → 8.4.2 (legacy, now using Docker Hub)
        m = re.match(r"mysql-(\d+\.\d+\.\d+)$", tag)
        return m.group(1) if m else None
    if transform == "docker_engine":
        # docker-v29.4.1 → 29.4.1; skip client/ and api/ tags
        if tag.startswith(("client/", "api/")):
            return None
        m = re.match(r"^(?:docker-)?v?(\d+\.\d+\.\d+)$", tag)
        return m.group(1) if m else None
    if transform == "nifi":
        # rel/nifi-2.9.0 → 2.9.0; skip support/ and other prefixes
        if tag.startswith("support/"):
            return None
        m = re.match(r"rel/nifi-(\d+\.\d+\.\d+)$", tag)
        return m.group(1) if m else None
    if transform == "nginx":
        # release-1.26.2 → 1.26.2
        m = re.match(r"release-(\d+\.\d+\.\d+)$", tag)
        return m.group(1) if m else None
    if transform == "kafka":
        # 3.8.0 or 3.8.0-rc1 — just use semver-looking tags
        m = re.match(r"^(\d+\.\d+\.\d+)$", tag)
        return m.group(1) if m else None
    # Default: strip leading 'v'
    return tag.lstrip("v") or None


class GitHubError(Exception):
    pass


def _check_github_response(r: httpx.Response, repo: str) -> list[dict]:
    if r.status_code == 403 or r.status_code == 429:
        msg = r.json().get("message", "Rate limited") if r.headers.get("content-type", "").startswith("application/json") else "Rate limited"
        raise GitHubError(f"GitHub API rate limit exceeded for {repo}. Set GITHUB_TOKEN env var to increase limits. ({msg})")
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise GitHubError(f"Unexpected GitHub response for {repo}: {data.get('message', str(data)[:80])}")
    return data


async def _fetch_github_releases(client: httpx.AsyncClient, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases?per_page=40"
    try:
        r = await client.get(url, headers=_github_headers(), timeout=15, follow_redirects=True)
        return _check_github_response(r, repo)
    except GitHubError:
        raise
    except Exception as exc:
        logger.warning("releases fetch failed for %s: %s", repo, exc)
        raise GitHubError(f"Network error fetching {repo}: {exc}")


async def _fetch_github_tags(client: httpx.AsyncClient, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/tags?per_page=60"
    try:
        r = await client.get(url, headers=_github_headers(), timeout=15, follow_redirects=True)
        return _check_github_response(r, repo)
    except GitHubError:
        raise
    except Exception as exc:
        logger.warning("tags fetch failed for %s: %s", repo, exc)
        raise GitHubError(f"Network error fetching {repo}: {exc}")


async def _fetch_dockerhub_tags(client: httpx.AsyncClient, repo: str) -> list[dict]:
    """Fetch tags from Docker Hub (no auth needed for public images)."""
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=50&ordering=last_updated"
    try:
        r = await client.get(url, timeout=15, follow_redirects=True)
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as exc:
        raise GitHubError(f"Docker Hub fetch failed for {repo}: {exc}")


async def fetch_tool(client: httpx.AsyncClient, tool: dict) -> dict:
    source = tool["source"]
    result = {
        "name": tool["name"],
        "category": tool["category"],
        "icon": tool.get("icon", ""),
        "homepage": tool.get("homepage", ""),
        "status": "ok",
        "latest": None,
        "previous": None,
    }

    if source == "static":
        versions = tool.get("versions", [])
        if versions:
            result["latest"] = {"version": versions[0]["version"], "date": versions[0]["release_date"], "url": tool.get("homepage", "")}
        if len(versions) > 1:
            result["previous"] = {"version": versions[1]["version"], "date": versions[1]["release_date"], "url": tool.get("homepage", "")}
        return result

    transform = tool.get("tag_transform")
    stable_entries: list[dict] = []

    if source == "github_releases":
        releases = await _fetch_github_releases(client, tool["repo"])
        for rel in releases:
            tag = rel.get("tag_name", "")
            if not _is_stable(tag, rel.get("prerelease", False)):
                continue
            display = _parse_tag(tag, transform)
            if not display:
                continue
            stable_entries.append({
                "version": display,
                "date": (rel.get("published_at") or "")[:10],
                "url": rel.get("html_url", ""),
            })
            if len(stable_entries) >= 2:
                break

    elif source == "github_tags":
        tags = await _fetch_github_tags(client, tool["repo"])
        for t in tags:
            tag = t.get("name", "")
            if not _is_stable(tag):
                continue
            display = _parse_tag(tag, transform)
            if not display:
                continue
            stable_entries.append({
                "version": display,
                "date": "",
                "url": f"https://github.com/{tool['repo']}/releases/tag/{tag}",
            })
            if len(stable_entries) >= 2:
                break

    elif source == "dockerhub":
        dh_tags = await _fetch_dockerhub_tags(client, tool["repo"])
        semver_re = re.compile(r"^\d+\.\d+\.\d+$")
        candidates = []
        for t in dh_tags:
            tag = t.get("name", "")
            if not semver_re.match(tag):
                continue
            if RC_PATTERN.search(tag):
                continue
            candidates.append({
                "version": tag,
                "date": (t.get("last_updated") or "")[:10],
                "url": f"https://hub.docker.com/_/{tool['repo'].split('/')[-1]}/tags",
            })
        # sort by version descending so latest major wins
        candidates.sort(
            key=lambda x: tuple(int(n) for n in x["version"].split(".")),
            reverse=True,
        )
        stable_entries = candidates[:2]

    if not stable_entries:
        result["status"] = "error"
        result["error"] = "No stable releases found (all releases filtered as pre-release)"
        return result

    result["latest"] = stable_entries[0]
    if len(stable_entries) > 1:
        result["previous"] = stable_entries[1]

    return result


async def fetch_all(force: bool = False) -> dict:
    global _cache, _cache_ts

    now = time.time()
    if not force and _cache and (now - _cache_ts) < CACHE_TTL:
        return _cache

    from tools import TOOLS  # local import to avoid circular

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_tool(client, tool) for tool in TOOLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    tools_data = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            tools_data.append({
                "name": TOOLS[i]["name"],
                "category": TOOLS[i]["category"],
                "icon": TOOLS[i].get("icon", ""),
                "homepage": TOOLS[i].get("homepage", ""),
                "status": "error",
                "error": str(res),
                "latest": None,
                "previous": None,
            })
        else:
            tools_data.append(res)

    _cache = {
        "tools": tools_data,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "cache_ttl_seconds": CACHE_TTL,
    }
    _cache_ts = now
    return _cache
