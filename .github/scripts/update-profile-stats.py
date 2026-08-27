#!/usr/bin/env python3
"""Generate reliable, repository-local GitHub profile SVG cards."""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
API_ROOT = "https://api.github.com"
USERNAME = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "mrphatom"
DATE_TEXT = datetime.now(timezone.utc).strftime("%d %b %Y")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def github_get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{API_ROOT}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mrphatom-profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def text(x: int, y: int, value: Any, *, fill: str, size: int, weight: str = "400", anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{esc(value)}</text>'
    )


def card_shell(width: int, height: int, accent: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<rect width="100%" height="100%" rx="18" fill="#0d1117" stroke="#30363d"/>',
        f'<rect x="1" y="1" width="{width - 2}" height="4" rx="2" fill="{accent}"/>',
    ]


def finish(lines: list[str]) -> str:
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_profile_stats(profile: dict[str, Any]) -> str:
    public_repos = profile.get("public_repos", 0)
    followers = profile.get("followers", 0)
    following = profile.get("following", 0)
    lines = card_shell(760, 190, "#14f195")
    lines.extend([
        '<title id="title">Public GitHub profile snapshot</title>',
        f'<desc id="desc">{esc(public_repos)} public repositories, {esc(followers)} followers, and {esc(following)} following.</desc>',
        text(28, 38, "PUBLIC PROFILE / SNAPSHOT", fill="#f0f6fc", size=14, weight="700"),
        text(28, 61, "GitHub-visible activity · refreshed daily", fill="#8b949e", size=12),
        '<line x1="28" y1="79" x2="732" y2="79" stroke="#21262d"/>',
    ])
    for x, value, label, color in (
        (28, public_repos, "PUBLIC REPOS", "#14f195"),
        (285, followers, "FOLLOWERS", "#4cc9f0"),
        (520, following, "FOLLOWING", "#a78bfa"),
    ):
        lines.append(text(x, 134, value, fill=color, size=30, weight="800"))
        lines.append(text(x, 159, label, fill="#c9d1d9", size=12))
    lines.append(text(28, 181, f"UPDATED {DATE_TEXT.upper()} BY GITHUB ACTIONS · PUBLIC DATA", fill="#6e7681", size=10))
    return finish(lines)


def render_language_mix(language_bytes: dict[str, int]) -> str:
    ranked = sorted(((name, int(value)) for name, value in language_bytes.items() if value), key=lambda item: item[1], reverse=True)
    total = sum(value for _, value in ranked) or 1
    top = ranked[:6]
    other_bytes = sum(value for _, value in ranked[6:])
    if other_bytes:
        top.append(("Other", other_bytes))

    colors = {
        "TypeScript": "#3178c6",
        "Python": "#3776ab",
        "HTML": "#e34c26",
        "JavaScript": "#f1e05a",
        "CSS": "#563d7c",
        "Rust": "#dea584",
        "C#": "#178600",
        "Solidity": "#aa6746",
        "Other": "#6e7681",
    }
    lines = card_shell(760, 250, "#4cc9f0")
    lines.extend([
        '<title id="title">Public repository language mix</title>',
        '<desc id="desc">Language shares are calculated from public repository code bytes and refreshed daily.</desc>',
        text(28, 38, "LANGUAGE MIX", fill="#f0f6fc", size=14, weight="700"),
        text(28, 61, "Public repositories · measured by code bytes · refreshed daily", fill="#8b949e", size=12),
    ])
    bar_x, bar_y, bar_width, bar_height = 28, 83, 704, 14
    lines.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="7" fill="#21262d"/>')
    cursor = bar_x
    for index, (name, value) in enumerate(top):
        width = bar_width - (cursor - bar_x) if index == len(top) - 1 else round(bar_width * value / total)
        if width <= 0:
            continue
        radius = 7 if index == 0 or index == len(top) - 1 else 0
        lines.append(f'<rect x="{cursor}" y="{bar_y}" width="{width}" height="{bar_height}" rx="{radius}" fill="{colors.get(name, "#6e7681")}"/>')
        cursor += width

    legend = top[:6]
    positions = [(36, 130), (270, 130), (492, 130), (36, 166), (270, 166), (492, 166)]
    for (name, value), (cx, cy) in zip(legend, positions):
        pct = value / total * 100
        label_x = cx + 14
        pct_x = label_x + (120 if len(name) > 8 else 102)
        lines.append(f'<circle cx="{cx}" cy="{cy - 4}" r="5" fill="{colors.get(name, "#6e7681")}"/>')
        lines.append(text(label_x, cy, name, fill="#c9d1d9", size=12))
        lines.append(text(pct_x, cy, f"{pct:.1f}%", fill="#14f195", size=12))
    lines.extend([
        '<line x1="28" y1="198" x2="732" y2="198" stroke="#21262d"/>',
        text(28, 222, "UPDATED DAILY BY GITHUB ACTIONS · PUBLIC REPOSITORY LANGUAGE BYTES", fill="#6e7681", size=10),
    ])
    return finish(lines)


def render_activity(events: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for event in events:
        kind = str(event.get("type", "Other"))
        counts[kind] = counts.get(kind, 0) + 1
    total = len(events)
    push = counts.get("PushEvent", 0)
    create = counts.get("CreateEvent", 0)
    delete = counts.get("DeleteEvent", 0)
    collaboration = sum(counts.get(kind, 0) for kind in ("PullRequestEvent", "ForkEvent", "ReleaseEvent"))
    shown = push + create + delete + collaboration
    other = max(total - shown, 0)
    latest = DATE_TEXT
    rows = [("Push", push, "#14f195"), ("Create", create, "#4cc9f0"), ("Delete", delete, "#f97316"), ("PR / Fork / Release", collaboration, "#a78bfa")]
    if other:
        rows.append(("Other", other, "#6e7681"))
    max_value = max((value for _, value, _ in rows), default=1) or 1

    card_height = 310 if not other else 334
    lines = card_shell(760, card_height, "#a78bfa")
    lines.extend([
        '<title id="title">Recent public GitHub activity</title>',
        f'<desc id="desc">The latest {esc(total)} public GitHub events, sampled {esc(latest)}.</desc>',
        text(28, 38, "RECENT PUBLIC ACTIVITY", fill="#f0f6fc", size=14, weight="700"),
        text(28, 61, f"Latest {total} public events · refreshed daily", fill="#8b949e", size=12),
    ])
    metric_cards = [(28, total, "EVENTS IN WINDOW", "#a78bfa", 145), (188, push, "PUSH EVENTS", "#14f195", 145), (348, create, "CREATE EVENTS", "#4cc9f0", 145), (508, latest, "LATEST EVENT DATE", "#f0f6fc", 224)]
    for x, value, label, color, width in metric_cards:
        lines.append(f'<rect x="{x}" y="82" width="{width}" height="56" rx="10" fill="#161b22" stroke="#21262d"/>')
        lines.append(text(x + 16, 108, value, fill=color, size=24, weight="800"))
        lines.append(text(x + 16, 127, label, fill="#8b949e", size=10))

    lines.append(text(28, 170, "EVENT BREAKDOWN", fill="#c9d1d9", size=11))
    start_y = 194
    for index, (label, value, color) in enumerate(rows):
        y = start_y + index * 24
        width = round(520 * value / max_value) if value else 0
        lines.append(text(28, y, label, fill="#8b949e", size=11))
        lines.append(f'<rect x="115" y="{y - 10}" width="520" height="12" rx="6" fill="#21262d"/>')
        if width:
            lines.append(f'<rect x="115" y="{y - 10}" width="{width}" height="12" rx="6" fill="{color}"/>')
        lines.append(text(650, y, value, fill=color, size=11))
    footer_y = start_y + len(rows) * 24 + 4
    lines.append(text(28, footer_y, "SCOPE: PUBLIC EVENTS ONLY · SOURCE: GITHUB API · UPDATED DAILY", fill="#6e7681", size=10))
    return finish(lines)


def main() -> None:
    profile = github_get(f"/users/{USERNAME}")
    repositories = github_get(f"/users/{USERNAME}/repos", {"per_page": "100", "type": "owner", "sort": "updated"})
    languages: dict[str, int] = {}
    for repository in repositories:
        if repository.get("fork"):
            continue
        repo_languages = github_get(repository["languages_url"].replace(API_ROOT, ""))
        for name, value in repo_languages.items():
            languages[name] = languages.get(name, 0) + int(value)
    events = github_get(f"/users/{USERNAME}/events/public", {"per_page": "100"})

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "profile-stats.svg").write_text(render_profile_stats(profile), encoding="utf-8")
    (ASSETS / "language-mix.svg").write_text(render_language_mix(languages), encoding="utf-8")
    (ASSETS / "activity-overview.svg").write_text(render_activity(events), encoding="utf-8")
    print(f"Updated profile cards for {USERNAME}: {len(repositories)} public repositories, {len(events)} public events.")


if __name__ == "__main__":
    main()
