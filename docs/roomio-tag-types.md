# Roomio Tag Types — API Guide

**Version:** 1.0
**Date:** 07.10.2026
**Scope:** Hoteza integration

---

## Overview

Tag types describe which device tags a property exposes to Hoteza and which values each of them may take. This guide covers:

- **Tag type groups** — a tenant's catalog of groups used to organise tag types.
- **Tag types** — a tenant's catalog of tag types. Each type belongs to a group and carries a list of allowed **range values**.
- **Device tag types** — the list of tags of a specific device, each mapped to a tag type and a subset of its range values. Stored on the device as the `TAG_TYPES` attribute (`SERVER_SCOPE`).
- **Tag types in room tags** — the partner Rooms & Tags API shows each room tag together with its `tag_type` and `tag_ranges`.

```
TagTypeGroup 1 ──< TagType 1 ──< TagRange (range_value)
                      │
                      │ referenced by name / range_value
                      ▼
Device ── AttributeKv(SERVER_SCOPE, key = "TAG_TYPES") = [ { tag_section, tag_sub_section, tag_name, tag_type, tag_ranges }, ... ]   ← this API
       └─ AttributeKv(CLIENT_SCOPE, key = "TAG_TYPES") = [ ... ]                                                                 ← reported by the device
                      │
                      │ matched to the device's tags (SERVER_SCOPE wins)
                      ▼
GET /api/v1/services/tags/{room_id}/  →  tags[] { id, key_name, value, updated_at, tag_type, tag_ranges }
```

All data is **tenant-scoped**: a user sees and changes only the objects of their own tenant. An object of another tenant is reported as `404`.

---

## Base URL

```
https://api.room.io/api/v1/services/
```

| Endpoint                        | Methods                |
| ------------------------------- | ---------------------- |
| `tag-type-groups/`              | `GET`, `POST`          |
| `tag-type-groups/{id}/`         | `GET`, `PUT`, `DELETE` |
| `tag-types/`                    | `GET`, `POST`          |
| `tag-types/{id}/`               | `GET`, `PUT`, `DELETE` |
| `device/{device_id}/tag-types/` | `GET`, `POST`, `PUT`   |

---

## Authentication & Permissions

Requests are authenticated with a Roomio user JWT:

```
Authorization: Bearer <access_token>
```

Each method additionally requires a Django permission of the user:

| Endpoint                        | `GET`                        | `POST`                      | `PUT`                          | `DELETE`                       |
| ------------------------------- | ---------------------------- | --------------------------- | ------------------------------ | ------------------------------ |
| `tag-type-groups/…`             | `services.view_tagtypegroup` | `services.add_tagtypegroup` | `services.change_tagtypegroup` | `services.delete_tagtypegroup` |
| `tag-types/…`                   | `services.view_tagtype`      | `services.add_tagtype`      | `services.change_tagtype`      | `services.delete_tagtype`      |
| `device/{device_id}/tag-types/` | `shuttle.view_attributelist` | `shuttle.add_attributelist` | `shuttle.add_attributelist`    | —                              |

| HTTP Status | Description                            |
| ----------- | -------------------------------------- |
| `401`       | Missing or invalid JWT                 |
| `403`       | The user lacks the required permission |

---

## Common Conventions

### Pagination & list parameters

List endpoints (`GET tag-type-groups/`, `GET tag-types/`) are paginated and return:

```json
{ "count": 12, "results": [] }
```

| Name      | Default | Description                                          |
| --------- | ------- | ---------------------------------------------------- |
| `page`    | `1`     | Page number (1-based).                               |
| `size`    | `50`    | Page size, `1`–`500`.                                |
| `search`  | —       | Case-insensitive substring filter by `name`.         |
| `sort_by` | `name`  | One of `name`, `-name`, `created_at`, `-created_at`. |

### Names

`name` is unique per tenant, both for groups and for tag types. A duplicate is rejected with `400`:

```json
{ "name": ["A tag type with this name already exists."] }
```

### Range values

A range value is **any JSON value**: string, number, boolean, `null`, object or array — e.g. `"15-25"`, `30`, `true`, `null`, `{"min": 16, "max": 30}`.

Values are compared **with their JSON type**: `"1"`, `1` and `true` are three different values. Duplicates in a request are collapsed into one.

A string `"low-high"` of two numbers (e.g. `"0-100"`, `"15.5-30"`, `"-10--2"`) is a **numeric range**; a device tag may select a part of it (see [Allowed range values](#allowed-range-values)).

### Timestamps

`created_at` / `updated_at` are ISO 8601 date-times, e.g. `"2026-10-06T07:46:12.345678Z"`.

---

## Tag Type Groups

### Object

```json
{
  "id": "5d1f0c7e-2b3a-4c4d-8e5f-6a7b8c9d0e1f",
  "name": "Climate",
  "tenant": "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc",
  "created_at": "2026-10-06T07:46:12.345678Z",
  "updated_at": "2026-10-06T07:46:12.345678Z"
}
```

| Field        | Type     | Description                    |
| ------------ | -------- | ------------------------------ |
| `id`         | UUID     | Group identifier.              |
| `name`       | string   | Group name, unique per tenant. |
| `tenant`     | UUID     | Owning tenant.                 |
| `created_at` | datetime | Creation time.                 |
| `updated_at` | datetime | Last change time.              |

### 1. List Tag Type Groups

```
GET /api/v1/services/tag-type-groups/?search=cli&sort_by=name&page=1&size=50
```

Response `200 OK` — paginated list of group objects.

### 2. Create Tag Type Group

```
POST /api/v1/services/tag-type-groups/
```

| Field  | Type   | Required | Description                    |
| ------ | ------ | -------- | ------------------------------ |
| `name` | string | Yes      | Group name, unique per tenant. |

```json
{ "name": "Climate" }
```

Response `201 Created` — the group object.

### 3. Retrieve Tag Type Group

```
GET /api/v1/services/tag-type-groups/{id}/
```

Response `200 OK` — the group object.

### 4. Update Tag Type Group

```
PUT /api/v1/services/tag-type-groups/{id}/
```

Same body as **Create**. Response `200 OK` — the updated group object.

### 5. Delete Tag Type Group

```
DELETE /api/v1/services/tag-type-groups/{id}/
```

Response `204 No Content`.

A group that still has tag types cannot be deleted — delete or move its tag types first:

```
HTTP 409 Conflict
```

```json
{ "detail": "The tag type group still has tag types and cannot be deleted." }
```

### Errors

| HTTP Status | Description                                  |
| ----------- | -------------------------------------------- |
| `400`       | Invalid body or duplicate `name`             |
| `404`       | Group not found or belongs to another tenant |
| `409`       | `DELETE` of a group that still has tag types |

---

## Tag Types

### Object

```json
{
  "id": "746a159e-412e-4d01-8d60-249640b13d6a",
  "name": "Temperature",
  "tenant": "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc",
  "group": { "id": "5d1f0c7e-2b3a-4c4d-8e5f-6a7b8c9d0e1f", "name": "Climate" },
  "tag_ranges": ["15-25", 30, true, null],
  "created_at": "2026-10-06T07:50:01.000000Z",
  "updated_at": "2026-10-06T07:50:01.000000Z"
}
```

| Field        | Type     | Description                              |
| ------------ | -------- | ---------------------------------------- |
| `id`         | UUID     | Tag type identifier.                     |
| `name`       | string   | Tag type name, unique per tenant.        |
| `tenant`     | UUID     | Owning tenant.                           |
| `group`      | object   | The group: `{ id, name }`.               |
| `tag_ranges` | array    | Allowed range values, in creation order. |
| `created_at` | datetime | Creation time.                           |
| `updated_at` | datetime | Last change time.                        |

### 1. List Tag Types

```
GET /api/v1/services/tag-types/?search=temp&group={group_id}&sort_by=name&page=1&size=50
```

Besides the common list parameters, accepts `group` (UUID) to filter by tag type group.

Response `200 OK` — paginated list of tag type objects.

### 2. Create Tag Type

```
POST /api/v1/services/tag-types/
```

| Field        | Type   | Required | Description                                           |
| ------------ | ------ | -------- | ----------------------------------------------------- |
| `name`       | string | Yes      | Tag type name, unique per tenant.                     |
| `group`      | UUID   | Yes      | Id of one of the tenant's tag type groups.            |
| `tag_ranges` | array  | Yes      | **Non-empty** list of range values (any JSON values). |

```json
{
  "name": "Temperature",
  "group": "5d1f0c7e-2b3a-4c4d-8e5f-6a7b8c9d0e1f",
  "tag_ranges": ["15-25", 30, true, null]
}
```

Response `201 Created` — the tag type object.

### 3. Retrieve Tag Type

```
GET /api/v1/services/tag-types/{id}/
```

Response `200 OK` — the tag type object.

### 4. Update Tag Type

```
PUT /api/v1/services/tag-types/{id}/
```

Same body as **Create**; all fields are required. `tag_ranges` **replaces** the current list as a whole:

- values present before and in the request are kept;
- new values are added;
- values missing from the request are removed.

Response `200 OK` — the updated tag type object.

> Device `TAG_TYPES` attributes reference tag types by `name` and ranges by value. Renaming a tag type or removing a range value does **not** update attributes already saved on devices.

### 5. Delete Tag Type

```
DELETE /api/v1/services/tag-types/{id}/
```

Response `204 No Content`. The type's range values are deleted with it.

### Errors

| HTTP Status | Description                                                            |
| ----------- | ---------------------------------------------------------------------- |
| `400`       | Invalid body, duplicate `name`, unknown `group`, or empty `tag_ranges` |
| `404`       | Tag type not found or belongs to another tenant                        |

---

## Device Tag Types

The tags of one device, each mapped to a tag type. The whole list is kept in a single device attribute:

| `AttributeKv` field | Value                         |
| ------------------- | ----------------------------- |
| `entity`            | the device (`device_id`)      |
| `attribute_type`    | `SERVER_SCOPE`                |
| `attribute_key`     | `TAG_TYPES`                   |
| `json_v`            | the list, exactly as returned |

Being `SERVER_SCOPE`, the attribute is **not** sent to the device. This API reads and writes only the `SERVER_SCOPE` attribute; a `TAG_TYPES` reported by the device in `CLIENT_SCOPE` is used only by the room tags (see [Tag Types in Room Tags](#tag-types-in-room-tags)).

### Entry

```json
{
  "tag_section": "ATTRIBUTE",
  "tag_sub_section": "CLIENT_SCOPE",
  "tag_name": "targetTemperature",
  "tag_type": "Temperature",
  "tag_ranges": ["15-25", 30]
}
```

| Field             | Type           | Required        | Description                                                                                                                            |
| ----------------- | -------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `tag_section`     | string         | Yes             | `ATTRIBUTE` or `TELEMETRY` — where the device tag lives.                                                                               |
| `tag_sub_section` | string \| null | For `ATTRIBUTE` | Attribute scope: `SERVER_SCOPE`, `CLIENT_SCOPE` or `SHARED_SCOPE`. For `TELEMETRY` it is **ignored** (any value) and stored as `null`. |
| `tag_name`        | string         | Yes             | Key of the device tag (attribute key or telemetry key).                                                                                |
| `tag_type`        | string         | Yes             | **Name** of one of the tenant's tag types.                                                                                             |
| `tag_ranges`      | array          | Yes             | Values from that tag type's `tag_ranges` only (see **Allowed range values**). May be empty. Duplicates are collapsed.                  |

### 1. Get Device Tag Types

```
GET /api/v1/services/device/{device_id}/tag-types/
```

| Parameter   | Type | Description                    |
| ----------- | ---- | ------------------------------ |
| `device_id` | UUID | A device of the user's tenant. |

Response `200 OK` — the saved list, or `[]` if it has never been set.

```json
[
  {
    "tag_section": "ATTRIBUTE",
    "tag_sub_section": "CLIENT_SCOPE",
    "tag_name": "targetTemperature",
    "tag_type": "Temperature",
    "tag_ranges": ["15-25", 30]
  },
  {
    "tag_section": "TELEMETRY",
    "tag_sub_section": null,
    "tag_name": "humidity",
    "tag_type": "Humidity",
    "tag_ranges": ["30-60"]
  }
]
```

### 2. Set Device Tag Types

`POST` and `PUT` behave the same.

```
POST | PUT /api/v1/services/device/{device_id}/tag-types/
Content-Type: application/json
```

The body is the **complete list** of entries; it replaces the stored list as a whole. Send `[]` to clear it.

```json
[
  {
    "tag_section": "ATTRIBUTE",
    "tag_sub_section": "CLIENT_SCOPE",
    "tag_name": "targetTemperature",
    "tag_type": "Temperature",
    "tag_ranges": ["15-25", 30, "15-25"]
  },
  {
    "tag_section": "TELEMETRY",
    "tag_name": "humidity",
    "tag_type": "Humidity",
    "tag_ranges": ["30-60"]
  }
]
```

Response `200 OK` — the list as stored (normalized: duplicates collapsed, `tag_sub_section` of `TELEMETRY` entries set to `null`). For the request above it equals the `GET` example.

#### Validation

| Case                                                             | Result                                                                   |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `tag_section` is not `ATTRIBUTE` / `TELEMETRY`                   | `400` `{"tag_section": ["\"X\" is not a valid choice."]}`                |
| `ATTRIBUTE` without `tag_sub_section`                            | `400` `{"tag_sub_section": ["This field is required."]}`                 |
| `ATTRIBUTE` with `tag_sub_section: null`                         | `400` `{"tag_sub_section": ["Required for an ATTRIBUTE tag."]}`          |
| `ATTRIBUTE` with an unknown scope                                | `400` `{"tag_sub_section": ["\"X\" is not a valid choice."]}`            |
| `TELEMETRY` with any / no `tag_sub_section`                      | accepted, stored as `null`                                               |
| `tag_type` is not a tag type name of the tenant                  | `400` `{"tag_type": ["Object with name=X does not exist."]}`             |
| a `tag_ranges` value is not allowed by that tag type (see below) | `400` `{"tag_ranges": ["Ranges do not belong to the tag type: [...]."]}` |

#### Allowed range values

A `tag_ranges` value is accepted only if it comes from the entry's own tag type:

- it equals one of the type's range values (compared with JSON type: `"30"`, `30` and `true` differ), or
- it is a numeric range `"low-high"`, a number or a numeric string that lies **within** one of the type's numeric ranges `"low-high"` (bounds included).

A reversed range is read as ordered: `"50-10"` is `10–50`. Bounds may be negative: `"-5-10"` is `-5–10`, `"-10--2"` is `-10–-2`. The value is stored exactly as sent.

| Type `tag_ranges` | Value        | Result                           |
| ----------------- | ------------ | -------------------------------- |
| `["0-100"]`       | `"0-100"`    | accepted (equal)                 |
| `["0-100"]`       | `"10-50"`    | accepted, stored as `"10-50"`    |
| `["0-100"]`       | `30`, `"30"` | accepted                         |
| `["0-100"]`       | `"50-10"`    | accepted (read as `10–50`)       |
| `["0-100"]`       | `"0-150"`    | `400` — exceeds the range        |
| `["0-100"]`       | `"250"`      | `400`                            |
| `[true, false]`   | `0`          | `400` — booleans are not numbers |

Errors are returned per entry, in request order, e.g. `[{}, {"tag_type": [...]}]` when only the second entry is invalid. Nothing is saved if any entry is invalid.

### Errors

| HTTP Status | Description                                   |
| ----------- | --------------------------------------------- |
| `400`       | Invalid body (see **Validation**)             |
| `404`       | Device not found or belongs to another tenant |

---

## Tag Types in Room Tags

The partner Rooms & Tags API — `GET /api/v1/services/tags/{room_id}/` and the `room_tags` WebSocket stream (see `roomio-rooms-tags-integration.md`) — adds two fields to **every** room tag:

| Field        | Type           | Description                                                    |
| ------------ | -------------- | -------------------------------------------------------------- |
| `tag_type`   | string \| null | `tag_type` of the matching entry; `null` if there is no match. |
| `tag_ranges` | array \| null  | `tag_ranges` of the matching entry; `null` when `tag_type` is. |

```json
{
  "id": "be81f8fc-0111-4826-b84a-906f4fe95ff3",
  "key_name": "targetTemperature",
  "value": 22,
  "updated_at": "2026-10-07T09:12:44.512000Z",
  "tag_type": "Temperature",
  "tag_ranges": ["15-25"]
}
```

### Sources

`TAG_TYPES` is read from two attributes of each device in the room:

| Attribute                  | Written by                                       | Priority   |
| -------------------------- | ------------------------------------------------ | ---------- |
| `SERVER_SCOPE` `TAG_TYPES` | this API (`POST` / `PUT device/{id}/tag-types/`) | **higher** |
| `CLIENT_SCOPE` `TAG_TYPES` | the device itself (JSON list, or a JSON string)  | lower      |

The priority applies **per tag**: when both attributes have an entry for the same tag, the `SERVER_SCOPE` entry is used; entries present in only one of them are used as they are. Entries of the `CLIENT_SCOPE` attribute are not validated. The `CLIENT_SCOPE` `TAG_TYPES` attribute itself is not listed as a room tag.

### Matching

A tag matches an entry of **its own device** only (two devices of a room may both have a tag `k`, each with its own type):

| Room tag                     | Entry                                                                       |
| ---------------------------- | --------------------------------------------------------------------------- |
| `CLIENT_SCOPE` attribute `k` | `tag_section = ATTRIBUTE`, `tag_sub_section = CLIENT_SCOPE`, `tag_name = k` |
| latest telemetry `k`         | `tag_section = TELEMETRY`, `tag_name = k`                                   |

`tag_name` must equal the tag key exactly (case and spaces included: `AC/ON OFF` does not match `AC ON OFF`). Room tags list only `CLIENT_SCOPE` attributes, so `SERVER_SCOPE` / `SHARED_SCOPE` entries never appear there.

### Updates

Saving `TAG_TYPES` (either scope) is an attribute change of the device, so active `room_tags` subscriptions of its room receive the updated payload. **Get Tag** and the `tag` stream do not include `tag_type` / `tag_ranges`.

---

## Typical Flow

```
1. POST /tag-type-groups/                       { "name": "Climate" }                → group.id
2. POST /tag-types/                             { "name": "Temperature",
                                                  "group": <group.id>,
                                                  "tag_ranges": ["15-25", 30] }
3. POST /device/{device_id}/tag-types/          [ { "tag_section": "ATTRIBUTE",
                                                    "tag_sub_section": "CLIENT_SCOPE",
                                                    "tag_name": "targetTemperature",
                                                    "tag_type": "Temperature",
                                                    "tag_ranges": ["15-25"] } ]
4. GET  /device/{device_id}/tag-types/          → the stored TAG_TYPES list
5. GET  /tags/{room_id}/                        → the device's targetTemperature tag carries
                                                  "tag_type": "Temperature", "tag_ranges": ["15-25"]
```
