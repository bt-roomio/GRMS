# Roomio Rooms & Tags — Integration Guide

**Version:** 1.0
**Date:** 23.06.2026
**Confidentiality:** Partner Use Only

---

## Overview

This document describes the Roomio Rooms & Tags API, which allows PMS and third-party systems to:

- Retrieve the list of rooms of a property.
- Read a room's **tags** — its attributes and latest telemetry exposed as a single unified list.
- Read and update a single tag value (with the change pushed to the physical device).
- Subscribe over WebSocket to receive the same data in real time as it changes.

A **tag** is a single named value of a room device, backed by either a device attribute or its latest telemetry. Both are exposed through one uniform shape: `{ id, key_name, value }`.

All API calls require two tokens issued by Roomio per integration (see [Authentication](#authentication)).

---

## Base URL

```
https://api.room.io
```

WebSocket endpoint:

```
wss://api.room.io/api/ws/v1/services/
```

---

## Authentication

Every request must be authenticated with the following two tokens:

| Token         | Description                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| `ClientToken` | Static token that identifies your integration client. Issued once by Roomio. |
| `AccessToken` | Per-property token tied to your hotel's integration record in Roomio.        |

**REST** — pass both as HTTP headers:

| Header        | Required | Value                      |
| ------------- | -------- | -------------------------- |
| `ClientToken` | Yes      | Your client token          |
| `AccessToken` | Yes      | Your property access token |

**WebSocket** — browsers cannot set custom headers on a WebSocket handshake, so the same two tokens are passed as **query-string parameters** (`client_token`, `access_token`). Native clients may alternatively send them as headers.

If either token is missing or invalid, the REST API returns:

```
HTTP 401 Unauthorized
```

```json
{
  "detail": "Authentication credentials were not provided."
}
```

A WebSocket connection with missing or invalid tokens is **rejected during the handshake** with close code `4401`.

> Contact Roomio support to obtain your `ClientToken` and `AccessToken` for each property.

---

## REST Endpoints

### 1. List Rooms

Retrieve the rooms of the property associated with the provided `AccessToken`. The result is paginated.

```
GET /api/v1/services/rooms/
```

#### Query Parameters

| Name      | Required | Default  | Description                 |
| --------- | -------- | -------- | --------------------------- |
| `page`    | No       | `1`      | Page number (1-based).      |
| `size`    | No       | `50`     | Page size, `1`–`500`.       |
| `sort_by` | No       | `number` | One of `number`, `-number`. |

#### Headers

| Name          | Required | Value                      |
| ------------- | -------- | -------------------------- |
| `ClientToken` | Yes      | Your client token          |
| `AccessToken` | Yes      | Your property access token |

#### Sample Request

```http
GET /api/v1/services/rooms/?page=1&size=50&sort_by=number HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

```json
{
  "count": 2,
  "results": [
    { "id": "3249b092-68b6-4891-80d4-42aee4e1743d", "number": "101" },
    { "id": "8f1c0a2b-1111-4c5d-8e9f-1a2b3c4d5e6f", "number": "102" }
  ]
}
```

#### Response Fields

| Field              | Type    | Description                                                                                   |
| ------------------ | ------- | --------------------------------------------------------------------------------------------- |
| `count`            | integer | Total number of rooms matching the query (across all pages).                                  |
| `results`          | array   | Rooms on the current page.                                                                    |
| `results[].id`     | UUID    | Unique identifier of the room. Use this value as `room_id` in the **List Room Tags** request. |
| `results[].number` | string  | Human-readable room number.                                                                   |

#### Error Responses

| HTTP Status | Description                                      |
| ----------- | ------------------------------------------------ |
| `401`       | Missing or invalid `ClientToken` / `AccessToken` |

---

### 2. List Room Tags

Retrieve a room together with its tags (CLIENT_SCOPE attributes and latest telemetry) as a single unified list.

```
GET /api/v1/services/tags/{room_id}/
```

#### Path Parameters

| Parameter | Type | Description                                        |
| --------- | ---- | -------------------------------------------------- |
| `room_id` | UUID | The `id` returned from the **List Rooms** endpoint |

#### Headers

| Name          | Required | Value                      |
| ------------- | -------- | -------------------------- |
| `ClientToken` | Yes      | Your client token          |
| `AccessToken` | Yes      | Your property access token |

#### Sample Request

```http
GET /api/v1/services/tags/3249b092-68b6-4891-80d4-42aee4e1743d/ HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

```json
{
  "room": { "id": "3249b092-68b6-4891-80d4-42aee4e1743d", "number": "101" },
  "tags": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "key_name": "roomCard",
      "value": true
    },
    {
      "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
      "key_name": "DND Relay",
      "value": 1
    }
  ]
}
```

#### Response Fields

| Field             | Type   | Description                                                                      |
| ----------------- | ------ | -------------------------------------------------------------------------------- |
| `room.id`         | UUID   | Room identifier.                                                                 |
| `room.number`     | string | Room number.                                                                     |
| `tags`            | array  | The room's tags (attributes + latest telemetry combined).                        |
| `tags[].id`       | UUID   | Tag identifier. Use this value as `tag_id` in the **Get / Update Tag** requests. |
| `tags[].key_name` | string | Tag key (e.g. `DND Relay`, `roomCard`).                                          |
| `tags[].value`    | any    | Current value; native JSON type (boolean / number / string / object).            |

#### Error Responses

| HTTP Status | Description                                            |
| ----------- | ------------------------------------------------------ |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`       |
| `404`       | The specified `room_id` was not found for the property |

---

### 3. Get Tag

Retrieve a single tag by its id.

```
GET /api/v1/services/tag/{tag_id}/
```

#### Path Parameters

| Parameter | Type | Description                                        |
| --------- | ---- | -------------------------------------------------- |
| `tag_id`  | UUID | The `id` of a tag returned from **List Room Tags** |

#### Sample Request

```http
GET /api/v1/services/tag/ba0b2f45-8219-42bc-9cb3-c1a83f4311c6/ HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

```json
{
  "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
  "key_name": "DND Relay",
  "value": 1
}
```

#### Error Responses

| HTTP Status | Description                                           |
| ----------- | ----------------------------------------------------- |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`      |
| `404`       | The specified `tag_id` was not found for the property |

---

### 4. Update Tag Value

Change a tag's value. The new value is **pushed to the physical device first** via RPC; it is persisted **only if the device accepts the change**. If the device rejects the command or does not respond within the timeout, the stored value is left unchanged.

```
PUT /api/v1/services/tag/{tag_id}/
```

#### Path Parameters

| Parameter | Type | Description                   |
| --------- | ---- | ----------------------------- |
| `tag_id`  | UUID | The `id` of the tag to update |

#### Headers

| Name           | Required | Value                      |
| -------------- | -------- | -------------------------- |
| `ClientToken`  | Yes      | Your client token          |
| `AccessToken`  | Yes      | Your property access token |
| `Content-Type` | Yes      | `application/json`         |

#### Request Body

| Field   | Type | Required | Description                                                                                                       |
| ------- | ---- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `value` | any  | Yes      | New value as a native JSON type (boolean / number / string / object). Routed to the device-compatible value type. |

#### Sample Request

```http
PUT /api/v1/services/tag/ba0b2f45-8219-42bc-9cb3-c1a83f4311c6/ HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
Content-Type: application/json

{ "value": 1 }
```

#### Response `200 OK` — Applied

The device accepted the change and the new value was persisted.

```json
{
  "tag": {
    "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
    "key_name": "DND Relay",
    "value": 1
  },
  "rpc": { "device": "38:0c:6e:41:02:80", "data": { "success": true } }
}
```

#### Response `502 Bad Gateway` — Not Applied

The device rejected the command or did not respond. The stored value is **unchanged**; inspect `rpc` for the reason.

```json
{
  "tag": {
    "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
    "key_name": "DND Relay",
    "value": 0
  },
  "rpc": {
    "device": "38:0c:6e:41:02:80",
    "data": { "success": false, "msg": "Timeout error" }
  }
}
```

#### Response Fields

| Field | Type   | Description                                                                                 |
| ----- | ------ | ------------------------------------------------------------------------------------------- |
| `tag` | object | The tag after the operation (updated on `200`, unchanged on `502`).                         |
| `rpc` | object | Raw device RPC result. `rpc.data.success` indicates whether the device accepted the change. |

#### Error Responses

| HTTP Status | Description                                                           |
| ----------- | --------------------------------------------------------------------- |
| `400`       | Invalid request body or unsupported value type                        |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`                      |
| `404`       | The specified `tag_id` was not found for the property                 |
| `502`       | Device rejected the change or did not respond; stored value unchanged |

---

## WebSocket API

The WebSocket API streams the same Rooms & Tags data and pushes live updates as values change.

```
wss://api.room.io/api/ws/v1/services/?client_token=<your_client_token>&access_token=<your_access_token>
```

A single connection multiplexes several independent **streams**. Every frame — in both directions — is a JSON object with a `stream` and a `payload`.

### Request envelope

```json
{
  "stream": "<stream_name>",
  "payload": {
    "action": "<action>",
    "request_id": 1,
    "query_params": {}
  }
}
```

| Field                  | Type   | Description                                                         |
| ---------------------- | ------ | ------------------------------------------------------------------- |
| `stream`               | string | Target stream: `rooms`, `room_tags`, or `tag`.                      |
| `payload.action`       | string | Action to perform on the stream (see each stream below).            |
| `payload.request_id`   | any    | Client-chosen correlation id echoed back in every related response. |
| `payload.query_params` | object | Action parameters (paging, `room_id`, `tag_id`, …).                 |

### Response envelope

```json
{
  "stream": "<stream_name>",
  "payload": {
    "errors": [],
    "data": {},
    "action": "<action>",
    "response_status": 200,
    "request_id": 1
  }
}
```

| Field                     | Type    | Description                                             |
| ------------------------- | ------- | ------------------------------------------------------- |
| `payload.errors`          | array   | Empty on success; otherwise a list of error objects.    |
| `payload.data`            | object  | The response body (shape depends on the stream/action). |
| `payload.action`          | string  | The action this message answers.                        |
| `payload.response_status` | integer | HTTP-like status code (`200`, `400`, …).                |
| `payload.request_id`      | any     | The `request_id` from the originating request.          |

> All `subscribe` push messages reuse the original `request_id`, so a client can route updates to the right subscription.

---

### Stream: `rooms`

Paginated list of rooms — the WebSocket equivalent of **List Rooms**.

| Action        | `query_params`                           | Description                                                              |
| ------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| `list`        | `page`, `size`, `sort_by` (all optional) | Returns one page once.                                                   |
| `subscribe`   | `page`, `size`, `sort_by` (all optional) | Returns the page, then re-sends it whenever a room on that page changes. |
| `unsubscribe` | —                                        | Stops updates for the given `request_id`.                                |

#### Example — `list`

Request:

```json
{
  "stream": "rooms",
  "payload": {
    "action": "list",
    "request_id": 1,
    "query_params": { "page": 1, "size": 50 }
  }
}
```

Response:

```json
{
  "stream": "rooms",
  "payload": {
    "errors": [],
    "data": {
      "count": 2,
      "results": [
        { "id": "3249b092-68b6-4891-80d4-42aee4e1743d", "number": "101" },
        { "id": "8f1c0a2b-1111-4c5d-8e9f-1a2b3c4d5e6f", "number": "102" }
      ]
    },
    "action": "list",
    "response_status": 200,
    "request_id": 1
  }
}
```

#### Example — `subscribe` / `unsubscribe`

```json
{
  "stream": "rooms",
  "payload": { "action": "subscribe", "request_id": 2, "query_params": {} }
}
```

```json
{ "stream": "rooms", "payload": { "action": "unsubscribe", "request_id": 2 } }
```

The initial response and every subsequent push carry `action: "subscribe"` and the same `request_id` (`2`), with `data` shaped exactly like the `list` response.

---

### Stream: `room_tags`

A room together with its tags — the WebSocket equivalent of **List Room Tags**.

| Action        | `query_params`       | Description                                                                                |
| ------------- | -------------------- | ------------------------------------------------------------------------------------------ |
| `list`        | `room_id` (required) | Returns `{ room, tags }` once.                                                             |
| `subscribe`   | `room_id` (required) | Returns `{ room, tags }`, then re-sends it whenever any tag of the room's devices changes. |
| `unsubscribe` | —                    | Stops updates for the given `request_id`.                                                  |

#### Example — `subscribe`

Request:

```json
{
  "stream": "room_tags",
  "payload": {
    "action": "subscribe",
    "request_id": 3,
    "query_params": { "room_id": "3249b092-68b6-4891-80d4-42aee4e1743d" }
  }
}
```

Response (and every later push):

```json
{
  "stream": "room_tags",
  "payload": {
    "errors": [],
    "data": {
      "room": { "id": "3249b092-68b6-4891-80d4-42aee4e1743d", "number": "101" },
      "tags": [
        {
          "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
          "key_name": "roomCard",
          "value": true
        },
        {
          "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
          "key_name": "DND Relay",
          "value": 1
        }
      ]
    },
    "action": "subscribe",
    "response_status": 200,
    "request_id": 3
  }
}
```

---

### Stream: `tag`

A single tag — the WebSocket equivalent of **Get Tag**.

| Action        | `query_params`      | Description                                                              |
| ------------- | ------------------- | ------------------------------------------------------------------------ |
| `retrieve`    | `tag_id` (required) | Returns the tag once.                                                    |
| `subscribe`   | `tag_id` (required) | Returns the tag, then re-sends it whenever **this** tag's value changes. |
| `unsubscribe` | —                   | Stops updates for the given `request_id`.                                |

#### Example — `subscribe`

Request:

```json
{
  "stream": "tag",
  "payload": {
    "action": "subscribe",
    "request_id": 4,
    "query_params": { "tag_id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6" }
  }
}
```

Response (and every later push):

```json
{
  "stream": "tag",
  "payload": {
    "errors": [],
    "data": {
      "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
      "key_name": "DND Relay",
      "value": 1
    },
    "action": "subscribe",
    "response_status": 200,
    "request_id": 4
  }
}
```

> Updating a tag value is **REST-only** (`PUT /api/v1/services/tag/{tag_id}/`). The `tag` WebSocket stream is read/subscribe only; any value written via REST is reflected to active subscribers automatically.

---

## Integration Flow

```
1. Receive ClientToken and AccessToken from Roomio.
2. Call GET /api/v1/services/rooms/ to retrieve the room list.
3. For a room, call GET /api/v1/services/tags/{room_id}/ to read its tags.
4. To change a value: PUT /api/v1/services/tag/{tag_id}/ with { "value": ... }
   and verify the response is 200 (rpc.data.success == true) before trusting the change.
5. For live data: open wss://api.room.io/api/ws/v1/services/?client_token=...&access_token=...
   and subscribe to the rooms / room_tags / tag streams as needed.
```

---

## Support

For credentials, onboarding, or technical questions, contact the Roomio integration team.
