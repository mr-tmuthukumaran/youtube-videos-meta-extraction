# youtube_channel_export.py — Usage Guide

## What it does

This script exports YouTube channel and video metadata using the YouTube Data API v3. It produces:

- `channels_metadata.csv` — one row per channel with channel metadata.
- `<channel_name>_videosinfo.csv` — one file per channel with all video metadata.

## What it provides

### channels_metadata.csv
Each row contains:
- `source_input` (original line from input file)
- `channel_id`
- `channel_title`
- `channel_description`
- `channel_published_at`
- `channel_country`
- `channel_view_count`
- `channel_subscriber_count`
- `channel_video_count`

### <channel_name>_videosinfo.csv
Each row contains:
- `source_input`
- `channel_id`
- `channel_title`
- `video_id`
- `video_title`
- `video_description`
- `video_published_at`
- `video_tags` (pipe‑delimited)
- `video_category_id`
- `video_duration`
- `video_definition`
- `video_caption`
- `video_licensed_content`
- `video_projection`
- `video_view_count`
- `video_like_count`
- `video_comment_count`
- `video_favorite_count`

## How to run it

1) Create an input file (one channel per line). Examples of valid lines:
   - `UCxxxxxxxxxxxxxxxxxxxxxx`
   - `https://www.youtube.com/channel/UC...`
   - `https://www.youtube.com/user/SomeUser`
   - `https://www.youtube.com/@SomeHandle`
   - `@SomeHandle`
   - `Some Channel Name`

2) Run the script:

```bash
python3 youtube_channel_export.py --input input.txt --outdir output --api-key YOUR_KEY
```

You can also set the API key with an environment variable:

```bash
export YT_API_KEY="YOUR_KEY"
python3 youtube_channel_export.py --input input.txt --outdir output
```

## Notes

- If a channel can’t be resolved, it is skipped with a warning.
- If a channel has no videos, its `<channel>_videosinfo.csv` is still created with just the header row.
- Share counts are not available in the YouTube Data API and are not included.
