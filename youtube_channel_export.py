#!/usr/bin/env python3
"""Export YouTube channel videos and metadata to CSV files."""

import argparse
import csv
import json
import os
import re
import sys
import time
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen, Request

API_BASE = "https://www.googleapis.com/youtube/v3"

class YouTubeApiError(RuntimeError):
    pass


def http_get(path: str, params: Dict[str, str]) -> Dict:
    url = f"{API_BASE}/{path}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req) as resp:
        data = resp.read().decode("utf-8")
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise YouTubeApiError(f"Invalid JSON from API: {exc}")
    if "error" in payload:
        raise YouTubeApiError(payload["error"].get("message", "API error"))
    return payload


def sanitize_filename(name: str) -> str:
    name = name.strip() or "channel"
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:120]


def read_channels(path: str) -> List[str]:
    channels: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            channels.append(value)
    return channels


def extract_channel_identifier(value: str) -> Tuple[str, str]:
    """Return (kind, identifier). kind in: id, username, query."""
    v = value.strip()

    # Full channel ID
    if v.startswith("UC") and len(v) >= 20:
        return "id", v

    # URLs
    m = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", v)
    if m:
        return "id", m.group(1)

    m = re.search(r"youtube\.com/user/([A-Za-z0-9_-]+)", v)
    if m:
        return "username", m.group(1)

    # Handle or custom URL
    m = re.search(r"youtube\.com/@([A-Za-z0-9_.-]+)", v)
    if m:
        return "query", m.group(1)

    if v.startswith("@"):
        return "query", v[1:]

    m = re.search(r"youtube\.com/c/([A-Za-z0-9_.-]+)", v)
    if m:
        return "query", m.group(1)

    return "query", v


def resolve_channel_id(api_key: str, value: str) -> Optional[str]:
    kind, ident = extract_channel_identifier(value)
    if kind == "id":
        return ident

    if kind == "username":
        payload = http_get(
            "channels",
            {
                "part": "id",
                "forUsername": ident,
                "key": api_key,
            },
        )
        items = payload.get("items", [])
        if items:
            return items[0]["id"]
        return None

    # Fallback to search
    payload = http_get(
        "search",
        {
            "part": "snippet",
            "q": ident,
            "type": "channel",
            "maxResults": "1",
            "key": api_key,
        },
    )
    items = payload.get("items", [])
    if not items:
        return None
    return items[0]["snippet"]["channelId"]


def get_channel_details(api_key: str, channel_id: str) -> Dict:
    payload = http_get(
        "channels",
        {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id,
            "key": api_key,
        },
    )
    items = payload.get("items", [])
    if not items:
        raise YouTubeApiError(f"Channel not found: {channel_id}")
    return items[0]


def iter_uploads_playlist_video_ids(
    api_key: str, uploads_playlist_id: str
) -> Iterable[str]:
    page_token = ""
    while True:
        params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": "50",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        payload = http_get("playlistItems", params)
        for item in payload.get("items", []):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                yield vid
        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break


def chunks(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_videos_details(api_key: str, video_ids: List[str]) -> List[Dict]:
    details: List[Dict] = []
    for batch in chunks(video_ids, 50):
        payload = http_get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(batch),
                "maxResults": "50",
                "key": api_key,
            },
        )
        details.extend(payload.get("items", []))
        time.sleep(0.1)
    return details


def format_tags(tags: Optional[List[str]]) -> str:
    if not tags:
        return ""
    return "|".join(tags)


def write_videos_info(
    out_path: str,
    channel: Dict,
    videos: List[Dict],
    source_input: str,
) -> None:
    header = [
        "source_input",
        "channel_id",
        "channel_title",
        "video_id",
        "video_title",
        "video_description",
        "video_published_at",
        "video_tags",
        "video_category_id",
        "video_duration",
        "video_definition",
        "video_caption",
        "video_licensed_content",
        "video_projection",
        "video_view_count",
        "video_like_count",
        "video_comment_count",
        "video_favorite_count",
    ]

    channel_id = channel.get("id", "")
    channel_title = channel.get("snippet", {}).get("title", "")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for video in videos:
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            content = video.get("contentDetails", {})
            writer.writerow(
                [
                    source_input,
                    channel_id,
                    channel_title,
                    video.get("id", ""),
                    snippet.get("title", ""),
                    snippet.get("description", ""),
                    snippet.get("publishedAt", ""),
                    format_tags(snippet.get("tags")),
                    snippet.get("categoryId", ""),
                    content.get("duration", ""),
                    content.get("definition", ""),
                    content.get("caption", ""),
                    str(content.get("licensedContent", "")),
                    content.get("projection", ""),
                    stats.get("viewCount", ""),
                    stats.get("likeCount", ""),
                    stats.get("commentCount", ""),
                    stats.get("favoriteCount", ""),
                ]
            )


def write_channels_csv(out_path: str, rows: List[Dict[str, str]]) -> None:
    header = [
        "source_input",
        "channel_id",
        "channel_title",
        "channel_description",
        "channel_published_at",
        "channel_country",
        "channel_view_count",
        "channel_subscriber_count",
        "channel_video_count",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export YouTube channel videos and metadata to CSV files."
    )
    parser.add_argument("--input", required=True, help="Path to channels text file")
    parser.add_argument(
        "--outdir", default="output", help="Directory to write CSV files"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("YT_API_KEY", ""),
        help="YouTube Data API key (or set YT_API_KEY env var)",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key required (use --api-key or YT_API_KEY).", file=sys.stderr)
        return 2

    os.makedirs(args.outdir, exist_ok=True)
    channels = read_channels(args.input)
    if not channels:
        print("No channels found in input file.")
        return 1

    channel_rows: List[Dict[str, str]] = []

    for value in channels:
        try:
            channel_id = resolve_channel_id(args.api_key, value)
            if not channel_id:
                print(f"[skip] Could not resolve channel: {value}")
                continue

            channel = get_channel_details(args.api_key, channel_id)
            channel_snippet = channel.get("snippet", {})
            channel_stats = channel.get("statistics", {})
            channel_rows.append(
                {
                    "source_input": value,
                    "channel_id": channel.get("id", ""),
                    "channel_title": channel_snippet.get("title", ""),
                    "channel_description": channel_snippet.get("description", ""),
                    "channel_published_at": channel_snippet.get("publishedAt", ""),
                    "channel_country": channel_snippet.get("country", ""),
                    "channel_view_count": channel_stats.get("viewCount", ""),
                    "channel_subscriber_count": channel_stats.get(
                        "subscriberCount", ""
                    ),
                    "channel_video_count": channel_stats.get("videoCount", ""),
                }
            )
            uploads = (
                channel.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
            channel_title = channel.get("snippet", {}).get("title", "channel")
            filename = sanitize_filename(channel_title)
            videos_info_path = os.path.join(
                args.outdir, f"{filename}_videosinfo.csv"
            )

            videos: List[Dict] = []
            if uploads:
                video_ids = list(iter_uploads_playlist_video_ids(args.api_key, uploads))
                if video_ids:
                    videos = fetch_videos_details(args.api_key, video_ids)

            write_videos_info(videos_info_path, channel, videos, value)
            print(
                f"[ok] Wrote {len(videos)} videos to {videos_info_path}"
            )

        except YouTubeApiError as exc:
            print(f"[error] {value}: {exc}", file=sys.stderr)
        except Exception as exc:  # defensive: keep processing next channels
            print(f"[error] {value}: {exc}", file=sys.stderr)

    channels_csv_path = os.path.join(args.outdir, "channels_metadata.csv")
    write_channels_csv(channels_csv_path, channel_rows)
    print(f"[ok] Wrote {len(channel_rows)} channels to {channels_csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
