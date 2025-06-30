# API Endpoint Guide

This document describes how to use each API endpoint defined in `app/api/main.py`.
All URLs below assume the API service is reachable at `http://localhost:8086` as
configured in `docker-compose.yaml`.

## POST `/api/v1/user-message`

Sends a user message to the AI and receives the generated reply.

### Request Body
```json
{
  "message": "<your text>"
}
```

### Example
```bash
curl http://localhost:8086/api/v1/user-message \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'
```

### Response
Plain text string containing the AI's response. The same text is saved to the
database together with the original user message.

---

## POST `/api/v1/user-actions`

Receives browsing data (URL, title, page text, etc.) from a Chrome extension.
The data is placed on RabbitMQ so that worker processes can analyze and store
it.

### Request Body Fields
- `url` – visited page URL
- `title` – page title
- `text` – page contents (optional)
- `scrollDepth` or `scroll_depth` – how far the page was scrolled (0.0–1.0)
- `visit_start` – ISO8601 start time
- `visit_end` – ISO8601 end time
- additional custom keys may be included

### Example
```bash
curl http://localhost:8086/api/v1/user-actions \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Example",
    "text": "page text",
    "scrollDepth": 0.5,
    "visit_start": "2024-01-01T00:00:00Z",
    "visit_end": "2024-01-01T00:05:00Z"
  }'
```

### Response
```json
{"status": "queued"}
```

---

## GET `/api/v1/user-messages`

Retrieves conversation history for a user from MySQL.

### Query Parameters
- `user_id` – target user ID (required)
- `limit` – number of messages to return (1–100, default 10)

### Example
```bash
curl 'http://localhost:8086/api/v1/user-messages?user_id=me&limit=5'
```

### Response
JSON array containing message objects:
```json
[
  {"user_id": "me", "message": "..."},
  {"user_id": "ai", "message": "..."}
]
```

---

## WebSocket `/ws`

Establish a WebSocket connection to receive real-time notifications. When
`/send-notification` is called, all connected clients receive a JSON payload.

### Example (JavaScript)
```javascript
const socket = new WebSocket('ws://localhost:8086/ws');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Message:', data.message);
  if (data.audio) {
    // data.audio contains a Base64-encoded WAV file synthesized by VOICEVOX
  }
};
```

---

## POST `/send-notification`

Broadcasts a message to all WebSocket clients. The server attempts to generate
speech audio using VOICEVOX and includes the Base64-encoded data when
successful.

### Request Body
```json
{"message": "text to announce"}
```

### Example
```bash
curl http://localhost:8086/send-notification \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "通知テスト"}'
```

### Response
```json
{"status": "sent"}
```

The WebSocket clients will receive a payload like:
```json
{
  "message": "通知テスト",
  "audio": "<Base64 WAV>" // present when synthesis succeeds
}
```

