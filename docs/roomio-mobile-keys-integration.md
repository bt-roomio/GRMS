# Roomio Mobile Keys — Integration Guide

**Version:** 1.0  
**Date:** 08.05.2025  
**Confidentiality:** Partner Use Only

---

## Overview

This document describes the Roomio Mobile Keys API, which allows PMS and third-party systems to:
- Retrieve a list of all door lock devices assigned to a property.
- Remotely open doors on behalf of a guest or staff member.

All API calls require two tokens issued by Roomio per integration (see [Authentication](#authentication)).

---

## Base URL

```
https://api.room.io
```

---

## Authentication

Every request must include the following two HTTP headers:

| Header | Description |
|---|---|
| `ClientToken` | Static token that identifies your integration client. Issued once by Roomio. |
| `AccessToken` | Per-property token tied to your hotel's integration record in Roomio. |

If either token is missing or invalid, the API returns:

```
HTTP 401 Unauthorized
```
```json
{
  "detail": "Authentication credentials were not provided."
}
```

> Contact Roomio support to obtain your `ClientToken` and `AccessToken` for each property.

---

## Endpoints

### 1. List Doors

Retrieve all door lock devices (rooms and public spaces) available for the property associated with the provided `AccessToken`.

```
GET /api/v1/services/lockkeys/doors/
```

#### Headers

| Name | Required | Value |
|---|---|---|
| `ClientToken` | Yes | Your client token |
| `AccessToken` | Yes | Your property access token |

#### Sample Request

```http
GET /api/v1/services/lockkeys/doors/ HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK`

Returns an array of door objects. Each object represents either a Room or a Public Space equipped with a door lock device.

```json
[
  {
    "space_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "space_type": "Room",
    "space_name": "101",
    "is_online": true
  },
  {
    "space_id": "a1b2c3d4-0000-0000-0000-000000000002",
    "space_type": "Room",
    "space_name": "102",
    "is_online": true
  },
  {
    "space_id": "a1b2c3d4-0000-0000-0000-000000000010",
    "space_type": "PublicSpace",
    "space_name": "Main Entrance",
    "is_online": true
  }
]
```

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `space_id` | UUID | Unique identifier of the door. Use this value in the Open Door request. |
| `space_type` | string | `"Room"` or `"PublicSpace"` |
| `space_name` | string | Human-readable name (room number or space name) |
| `is_online` | boolean | `true` if the lock device is currently reachable |

#### Error Responses

| HTTP Status | Description |
|---|---|
| `401` | Missing or invalid `ClientToken` / `AccessToken` |

---

### 2. Open Door

Send an unlock command to a specific door lock device. The API waits up to **10 seconds** for a response from the device.

```
POST /api/v1/services/lockkeys/doors/{space_id}/open/
```

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `space_id` | UUID | The `space_id` returned from the **List Doors** endpoint |

#### Headers

| Name | Required | Value |
|---|---|---|
| `ClientToken` | Yes | Your client token |
| `AccessToken` | Yes | Your property access token |

#### Sample Request

```http
POST /api/v1/services/lockkeys/doors/a1b2c3d4-0000-0000-0000-000000000001/open/ HTTP/1.1
Host: api.room.io
ClientToken: <your_client_token>
AccessToken: <your_access_token>
```

#### Response `200 OK` — Success

```json
{
  "device": "38:0c:6e:41:02:80",
  "data": {
    "success": true
  }
}
```

#### Response `200 OK` — Timeout

If the device does not respond within 10 seconds, the API returns HTTP 200 with a timeout payload:

```json
{
  "device": "38:0c:6e:41:02:80",
  "data": {
    "success": false,
    "msg": "Timeout error"
  }
}
```

> Always check `data.success` in the response body to confirm the door was actually opened.

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `device` | string | MAC address of the door lock device |
| `data.success` | boolean | `true` if the door was unlocked successfully |
| `data.msg` | string | Present only on failure. Currently: `"Timeout error"` |

#### Error Responses

| HTTP Status | Description |
|---|---|
| `401` | Missing or invalid `ClientToken` / `AccessToken` |
| `404` | The specified `space_id` was not found |

---

## Integration Flow

```
1. Receive ClientToken and AccessToken from Roomio.
2. Call GET /api/v1/services/lockkeys/doors/ to retrieve the door list.
3. Map each door's space_id to your internal room/space identifier.
4. On check-in / access event: call POST /api/v1/services/lockkeys/doors/{space_id}/open/
5. Verify data.success == true before confirming access to the guest.
```

---

## Support

For credentials, onboarding, or technical questions, contact the Roomio integration team.
