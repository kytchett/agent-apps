"""GitHub fetcher using PyGithub."""
from typing import List, Dict
import os
from github import Github


def _build_query(keywords: str = "", language: str = "") -> str:
    parts = []
    if keywords:
        parts.append(keywords)
    if language:
        parts.append(f"language:{language}")
    if not parts:
        return ""
    return " ".join(parts)


def fetch_github(max_results: int = 100, keywords: str = "", language: str = "") -> List[Dict]:
    """Fetch top GitHub repos by stars. Uses search API. Requires GITHUB_TOKEN for higher rate limits."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        gh = Github(token)
    else:
        gh = Github()

    q = _build_query(keywords, language)
    repos = []
    per_page = 30
    fetched = 0

    # If no query provided, search for all repositories sorted by stars (GitHub requires a query; use stars:>0)
    if not q:
        q = "stars:>0"

    search_results = gh.search_repositories(query=q, sort="stars", order="desc")
    for repo in search_results:
        repos.append({
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "description": repo.description,
            "stars": repo.stargazers_count,
            "language": repo.language,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
        })
        fetched += 1
        if fetched >= max_results:
            break

    return repos
