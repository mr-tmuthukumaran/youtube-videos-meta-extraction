# youtube_channel_export.py — How It Works

This script reads a list of YouTube channels from a text file, resolves each to a channel ID, fetches channel metadata and video metadata via the YouTube Data API v3, and writes:

- `channels_metadata.csv` (all channels + their metadata)
- One per‑channel video CSV: `<channel_name>_videosinfo.csv`

## Step‑by‑step flow

1) **Read input list**
   - `read_channels()` loads the input file and collects non‑empty, non‑comment lines.
   - Each line can be a channel ID (`UC...`), a channel URL, a user URL, a handle (`@...`), or a plain channel name.

2) **Resolve each channel to a channel ID**
   - `extract_channel_identifier()` parses the input string and returns a resolution strategy:
     - `id` for channel IDs or `youtube.com/channel/...`
     - `username` for `youtube.com/user/...`
     - `query` for handles (`@...`), `youtube.com/@...`, `youtube.com/c/...`, or plain names
   - `resolve_channel_id()` then calls the appropriate API endpoint (see “API Calls” below) to get the channel ID.

3) **Fetch channel metadata**
   - `get_channel_details()` calls the `channels` API and requests:
     - `snippet` (title, description, publishedAt, country)
     - `contentDetails` (includes the uploads playlist ID)
     - `statistics` (view/subscriber/video counts)
   - A row is appended to the in‑memory `channel_rows` list for final CSV output.

4) **Find the channel’s uploads playlist**
   - The uploads playlist ID lives at:
     - `channel.contentDetails.relatedPlaylists.uploads`

5) **List all video IDs from the uploads playlist**
   - `iter_uploads_playlist_video_ids()` calls the `playlistItems` API in a loop, using `nextPageToken` until all items are retrieved.

6) **Fetch video metadata in batches**
   - `fetch_videos_details()` calls the `videos` API with up to 50 IDs per request.
   - For each video, it collects:
     - `snippet` (title, description, tags, category, publishedAt)
     - `contentDetails` (duration, definition, captions, licensedContent, projection)
     - `statistics` (view/like/comment/favorite counts)

7) **Write per‑channel video CSV**
   - `write_videos_info()` writes `<channel_name>_videosinfo.csv` with one row per video.
   - The file is always created; if the channel has no videos, it will contain only the header row.

8) **Write global channel CSV**
   - After processing all channels, `write_channels_csv()` writes `channels_metadata.csv` with one row per channel.

## API calls used (YouTube Data API v3)

All calls use base URL: `https://www.googleapis.com/youtube/v3`

1) **Resolve username to channel ID**
   - Endpoint: `channels`
   - Params:
     - `part=id`
     - `forUsername=<username>`
     - `key=<API_KEY>`

2) **Resolve channel by search (handles / custom URLs / names)**
   - Endpoint: `search`
   - Params:
     - `part=snippet`
     - `q=<query>`
     - `type=channel`
     - `maxResults=1`
     - `key=<API_KEY>`
   - The script uses `items[0].snippet.channelId` from the response.

3) **Fetch channel details**
   - Endpoint: `channels`
   - Params:
     - `part=snippet,contentDetails,statistics`
     - `id=<channel_id>`
     - `key=<API_KEY>`

4) **List uploads playlist items (video IDs)**
   - Endpoint: `playlistItems`
   - Params:
     - `part=contentDetails`
     - `playlistId=<uploads_playlist_id>`
     - `maxResults=50`
     - `pageToken=<token>` (when present)
     - `key=<API_KEY>`

5) **Fetch video details (batched)**
   - Endpoint: `videos`
   - Params:
     - `part=snippet,contentDetails,statistics`
     - `id=<comma_separated_video_ids>` (up to 50)
     - `maxResults=50`
     - `key=<API_KEY>`

## Output schema

### channels_metadata.csv
Columns:
- `source_input`
- `channel_id`
- `channel_title`
- `channel_description`
- `channel_published_at`
- `channel_country`
- `channel_view_count`
- `channel_subscriber_count`
- `channel_video_count`

### <channel>_videosinfo.csv
Columns:
- `source_input`
- `channel_id`
- `channel_title`
- `video_id`
- `video_title`
- `video_description`
- `video_published_at`
- `video_tags`
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

## Notes

- The script throttles video detail requests slightly (`time.sleep(0.1)`) to reduce rate‑limit risk.
- Share counts are not available in the YouTube Data API and are not included.
- Tags are joined with `|` in the `video_tags` column.
