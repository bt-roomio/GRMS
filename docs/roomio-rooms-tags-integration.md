# Roomio Rooms & Tags — Integration Guide

**Version:** 1.1
**Date:** 07.10.2026
**Confidentiality:** Partner Use Only

---

## Overview

This document describes the Roomio Rooms & Tags API, which allows PMS and third-party systems to:

- Retrieve the room types and the rooms of a property.
- Read a room's **tags** — its attributes and latest telemetry exposed as a single unified list, each with its tag type and allowed values.
- Read and update a single tag value (with the change pushed to the physical device).
- Subscribe over WebSocket to receive the same data in real time as it changes.

A **tag** is a single named value of a room device, backed by either a device attribute or its latest telemetry. Both are exposed through one uniform shape: `{ id, key_name, value, updated_at }`; room tag lists add `tag_type` and `tag_ranges`.

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

### 1. List Room Types

Retrieve the room types of the property associated with the provided `AccessToken`. The result is paginated.

```
GET /api/v1/services/room-types/
```

#### Query Parameters

| Name      | Required | Default | Description               |
| --------- | -------- | ------- | ------------------------- |
| `page`    | No       | `1`     | Page number (1-based).    |
| `size`    | No       | `50`    | Page size, `1`–`500`.     |
| `sort_by` | No       | `title` | One of `title`, `-title`. |

#### Headers

| Name          | Required | Value                      |
| ------------- | -------- | -------------------------- |
| `ClientToken` | Yes      | Your client token          |
| `AccessToken` | Yes      | Your property access token |

#### Sample Request

```http
GET /api/v1/services/room-types/?page=1&size=50&sort_by=title HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

```json
{
  "count": 2,
  "results": [
    { "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "title": "Deluxe" },
    { "id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f", "title": "Standard" }
  ]
}
```

#### Response Fields

| Field             | Type    | Description                                                                               |
| ----------------- | ------- | ----------------------------------------------------------------------------------------- |
| `count`           | integer | Total number of room types (across all pages).                                            |
| `results`         | array   | Room types on the current page.                                                           |
| `results[].id`    | UUID    | Room type identifier. Use this value as `room_type` to filter the **List Rooms** request. |
| `results[].title` | string  | Room type name.                                                                           |

#### Error Responses

| HTTP Status | Description                                      |
| ----------- | ------------------------------------------------ |
| `400`       | Invalid query parameter                          |
| `401`       | Missing or invalid `ClientToken` / `AccessToken` |

---

### 2. List Rooms

Retrieve the rooms of the property associated with the provided `AccessToken`, optionally filtered by room type. The result is paginated.

```
GET /api/v1/services/rooms/
```

#### Query Parameters

| Name        | Required | Default  | Description                                                             |
| ----------- | -------- | -------- | ----------------------------------------------------------------------- |
| `page`      | No       | `1`      | Page number (1-based).                                                  |
| `size`      | No       | `50`     | Page size, `1`–`500`.                                                   |
| `sort_by`   | No       | `number` | One of `number`, `-number`.                                             |
| `room_type` | No       | —        | Room type `id` (from **List Room Types**); only its rooms are returned. |

#### Headers

| Name          | Required | Value                      |
| ------------- | -------- | -------------------------- |
| `ClientToken` | Yes      | Your client token          |
| `AccessToken` | Yes      | Your property access token |

#### Sample Request

```http
GET /api/v1/services/rooms/?page=1&size=50&sort_by=number&room_type=0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

```json
{
  "count": 2,
  "results": [
    {
      "id": "3249b092-68b6-4891-80d4-42aee4e1743d",
      "number": "101",
      "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
      "type_name": "Standard"
    },
    {
      "id": "8f1c0a2b-1111-4c5d-8e9f-1a2b3c4d5e6f",
      "number": "102",
      "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
      "type_name": "Standard"
    }
  ]
}
```

#### Response Fields

| Field                 | Type           | Description                                                                                   |
| --------------------- | -------------- | --------------------------------------------------------------------------------------------- |
| `count`               | integer        | Total number of rooms matching the query (across all pages).                                  |
| `results`             | array          | Rooms on the current page.                                                                    |
| `results[].id`        | UUID           | Unique identifier of the room. Use this value as `room_id` in the **List Room Tags** request. |
| `results[].number`    | string         | Human-readable room number.                                                                   |
| `results[].type_id`   | UUID \| null   | Id of the room's type; `null` if the room has no type.                                        |
| `results[].type_name` | string \| null | Title of the room's type; `null` if the room has no type.                                     |

#### Error Responses

| HTTP Status | Description                                              |
| ----------- | -------------------------------------------------------- |
| `400`       | Invalid query parameter (e.g. `room_type` is not a UUID) |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`         |

---

### 3. List Room Tags

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
  "room": {
    "id": "3249b092-68b6-4891-80d4-42aee4e1743d",
    "number": "101",
    "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
    "type_name": "Standard"
  },
  "tags": [
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "key_name": "roomCard",
      "value": true,
      "updated_at": "2026-10-07T09:12:44.512000Z",
      "tag_type": null,
      "tag_ranges": null
    },
    {
      "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
      "key_name": "DND Relay",
      "value": 1,
      "updated_at": "2026-10-07T09:15:02.031000Z",
      "tag_type": "DND",
      "tag_ranges": [0, 1]
    }
  ]
}
```

#### Response Fields

| Field               | Type           | Description                                                                                                                               |
| ------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `room.id`           | UUID           | Room identifier.                                                                                                                          |
| `room.number`       | string         | Room number.                                                                                                                              |
| `room.type_id`      | UUID \| null   | Id of the room's type; `null` if the room has no type.                                                                                    |
| `room.type_name`    | string \| null | Title of the room's type; `null` if the room has no type.                                                                                 |
| `tags`              | array          | The room's tags (attributes + latest telemetry combined).                                                                                 |
| `tags[].id`         | UUID           | Tag identifier. Use this value as `tag_id` in the **Get / Update Tag** requests.                                                          |
| `tags[].key_name`   | string         | Tag key (e.g. `DND Relay`, `roomCard`).                                                                                                   |
| `tags[].value`      | any            | Current value; native JSON type (boolean / number / string / object).                                                                     |
| `tags[].updated_at` | datetime       | When the value was last written, ISO 8601 (UTC).                                                                                          |
| `tags[].tag_type`   | string \| null | Tag type name; `null` if the tag is not mapped to a tag type in Roomio.                                                                   |
| `tags[].tag_ranges` | array \| null  | Allowed values of the tag: any JSON values, a string `"low-high"` is a numeric range (bounds included); `null` when `tag_type` is `null`. |

> `tag_type` and `tag_ranges` come from the tag mapping of the tag's device — configured in Roomio, or reported by the device itself (the Roomio configuration takes precedence). Both are `null` for a tag without a mapping. **Get Tag** and the `tag` stream do not include them.

#### Error Responses

| HTTP Status | Description                                            |
| ----------- | ------------------------------------------------------ |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`       |
| `404`       | The specified `room_id` was not found for the property |

---

### 4. Get Tag

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
  "value": 1,
  "updated_at": "2026-10-07T09:15:02.031000Z"
}
```

The fields are the same as in `tags[]` of **List Room Tags**.

#### Error Responses

| HTTP Status | Description                                           |
| ----------- | ----------------------------------------------------- |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`      |
| `404`       | The specified `tag_id` was not found for the property |

---

### 5. Update Tag Value

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

| Field   | Type | Required | Description                                                                                                                           |
| ------- | ---- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `value` | any  | Yes      | New value as a native JSON type (boolean / number / string / object); `null` is rejected. Routed to the device-compatible value type. |

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
    "value": 1,
    "updated_at": "2026-10-07T09:20:11.204000Z"
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
    "value": 0,
    "updated_at": "2026-10-07T09:15:02.031000Z"
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
| `tag` | object | The tag after the operation (value and `updated_at` updated on `200`, unchanged on `502`).  |
| `rpc` | object | Raw device RPC result. `rpc.data.success` indicates whether the device accepted the change. |

#### Error Responses

| HTTP Status | Description                                                           |
| ----------- | --------------------------------------------------------------------- |
| `400`       | Invalid request body, `null` value or unsupported value type          |
| `401`       | Missing or invalid `ClientToken` / `AccessToken`                      |
| `404`       | The specified `tag_id` was not found for the property                 |
| `502`       | Device rejected the change or did not respond; stored value unchanged |

---

## WebSocket API

The WebSocket API serves the same Rooms & Tags data and pushes live updates of tag values as they change.

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
| `payload.query_params` | object | Action parameters (paging, `room_type`, `room_id`, `tag_id`, …).    |

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

> Subscriptions are available on the `room_tags` and `tag` streams. All `subscribe` push messages reuse the original `request_id`, so a client can route updates to the right subscription.

---

### Stream: `rooms`

Paginated list of rooms — the WebSocket equivalent of **List Rooms**. The stream is request/response only and has no `subscribe`.

| Action | `query_params`                                        | Description            |
| ------ | ----------------------------------------------------- | ---------------------- |
| `list` | `page`, `size`, `sort_by`, `room_type` (all optional) | Returns one page once. |

| Parameter   | Default  | Description                                                         |
| ----------- | -------- | ------------------------------------------------------------------- |
| `page`      | `1`      | Page number (1-based).                                              |
| `size`      | `15`     | Page size.                                                          |
| `sort_by`   | `number` | One of `number`, `-number`; any other value falls back to `number`. |
| `room_type` | —        | Room type `id`; only its rooms are returned.                        |

#### Example — `list`

Request:

```json
{
  "stream": "rooms",
  "payload": {
    "action": "list",
    "request_id": 1,
    "query_params": {
      "page": 1,
      "size": 50,
      "room_type": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f"
    }
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
        {
          "id": "3249b092-68b6-4891-80d4-42aee4e1743d",
          "number": "101",
          "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
          "type_name": "Standard"
        },
        {
          "id": "8f1c0a2b-1111-4c5d-8e9f-1a2b3c4d5e6f",
          "number": "102",
          "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
          "type_name": "Standard"
        }
      ]
    },
    "action": "list",
    "response_status": 200,
    "request_id": 1
  }
}
```

---

### Stream: `room_tags`

A room together with its tags — the WebSocket equivalent of **List Room Tags**; `data` has the same shape as that REST response.

| Action        | `query_params`       | Description                                                                                                              |
| ------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `list`        | `room_id` (required) | Returns `{ room, tags }` once.                                                                                           |
| `subscribe`   | `room_id` (required) | Returns `{ room, tags }`, then re-sends the whole payload whenever any tag or tag mapping of the room's devices changes. |
| `unsubscribe` | —                    | Stops updates for the given `request_id`.                                                                                |

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
      "room": {
        "id": "3249b092-68b6-4891-80d4-42aee4e1743d",
        "number": "101",
        "type_id": "0f6c1d2e-3a4b-4c5d-8e9f-1a2b3c4d5e6f",
        "type_name": "Standard"
      },
      "tags": [
        {
          "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
          "key_name": "roomCard",
          "value": true,
          "updated_at": "2026-10-07T09:12:44.512000Z",
          "tag_type": null,
          "tag_ranges": null
        },
        {
          "id": "ba0b2f45-8219-42bc-9cb3-c1a83f4311c6",
          "key_name": "DND Relay",
          "value": 1,
          "updated_at": "2026-10-07T09:15:02.031000Z",
          "tag_type": "DND",
          "tag_ranges": [0, 1]
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
      "value": 1,
      "updated_at": "2026-10-07T09:15:02.031000Z"
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
2. Optionally call GET /api/v1/services/room-types/ to retrieve the room types.
3. Call GET /api/v1/services/rooms/ (optionally ?room_type={id}) to retrieve the room list.
4. For a room, call GET /api/v1/services/tags/{room_id}/ to read its tags.
5. To change a value: PUT /api/v1/services/tag/{tag_id}/ with { "value": ... }
   and verify the response is 200 (rpc.data.success == true) before trusting the change.
6. For live data: open wss://api.room.io/api/ws/v1/services/?client_token=...&access_token=...
   and subscribe to the room_tags / tag streams as needed (the rooms stream supports list only).
```

---

## Support

For credentials, onboarding, or technical questions, contact the Roomio integration team.
