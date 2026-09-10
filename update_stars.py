#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "xishangshui")
TOKEN = os.environ.get("STAR_TOKEN", "").strip()
API_VERSION = "2026-03-10"


def fetch_page(page: int):
    url = (
        f"https://api.github.com/users/{USERNAME}/starred"
        f"?sort=created&direction=desc&per_page=100&page={page}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "github-stars-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {body}") from exc


def fetch_all_stars():
    repos = []
    page = 1
    while True:
        batch = fetch_page(page)
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected GitHub API response")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def anchor(topic: str):
    return topic.lower().replace(" ", "-")


def main():
    repos = fetch_all_stars()
    if not repos:
        print(
            "No starred repositories were returned. "
            "If your GitHub profile is private, create a fine-grained PAT with "
            "Starring: read and save it as the repository secret STAR_TOKEN.",
            file=sys.stderr,
        )
        return 2

    grouped = defaultdict(list)
    for repo in repos:
        topics = repo.get("topics") or ["others"]
        for topic in topics:
            grouped[topic].append(repo)

    topics = sorted(grouped, key=str.lower)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# GitHub Stars",
        "",
        f"> 自动同步 [{USERNAME}](https://github.com/{USERNAME}) 的公开 GitHub Stars，并按仓库 Topic 分类。",
        "",
        f"共 **{len(repos)}** 个项目 · 最后更新：{now}",
        "",
        "## Contents",
        "",
    ]

    for topic in topics:
        lines.append(f"- [{topic}](#{anchor(topic)}) ({len(grouped[topic])})")

    lines.append("")
    for topic in topics:
        lines.extend([f"## {topic}", ""])
        for repo in grouped[topic]:
            name = repo.get("full_name", repo.get("name", "unknown"))
            url = repo.get("html_url", "")
            desc = (repo.get("description") or "").replace("\n", " ").strip()
            if desc:
                lines.append(f"- [{name}]({url}) — {desc}")
            else:
                lines.append(f"- [{name}]({url})")
        lines.append("")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"Generated README.md from {len(repos)} starred repositories across {len(topics)} topics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
