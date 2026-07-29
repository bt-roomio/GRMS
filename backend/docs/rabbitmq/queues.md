# RabbitMQ queues — message templates

Reference for the message shapes flowing through each RabbitMQ queue used by device
communication and PMS integration. Templates are derived from the code that produces/consumes
them (not captured from live traffic), so field names and structure are accurate but example
values are illustrative.

Consumers:

- `mq-async` service (`apps/core/management/commands/mq_async.py`) — consumes `toGRMS`,
  `v1/devices/me/attributes/request`, `v1/gateway/rpc`, `v1/gateway/attributes/request`,
  `/attributes`, `/telemetry`. Publishes to `fromGRMS`.
- `pms-handler` service (`apps/services/management/commands/pms_handler.py`) — separate
  consumer, only handles `pmsMessages` (and republishes unroutable events to `pmsUnhandled`).

## Common envelope

Every message consumed by `mq_async` (i.e. every queue except `pmsMessages`) must include
`sourceDeviceUUID` — `validate_body()` (`mq_async.py:162-167`) looks up the `Device` by this
field before any further processing. Routing to a handler is based on the `topic` field, not
on which queue the message arrived on.

---

## `/telemetry` — inbound, from devices

Source: `sim_message.py:76-95`

```json
{
  "sourceDeviceUUID": "<gateway_device_uuid>",
  "topic": "v1/gateway/telemetry",
  "data": {
    "<sub_device_name>": [
      {
        "ts": 1785293000000,
        "values": {
          "MUR Relay": 1,
          "Room Temperature": 23,
          "AC ON OFF": 1,
          "Occupancy State": 0
        }
      }
    ]
  }
}
```

Non-gateway variant: `topic` ends with `/telemetry` directly and `data` is a list of
`{ts, values}` without the sub-device wrapper (`apps/core/management/mq/telemetry.py:191-194`).

RFID event nested inside `values` (`sim_message.py:150-168`,
`apps/core/management/mq/telemetry.py:202-206`):

```json
"values": {
  "rfid_card_event": {
    "access_log_id": "1774079209000",
    "lock_type": "ttlock",
    "card_uid": "Pasword unlock",
    "open_type": "unknown",
    "openResult": 1,
    "event_ts": 1774079212319
  }
}
```

## `/attributes` — inbound, from devices

Source: `sim_message.py:64-72`

```json
{
  "sourceDeviceUUID": "<device_uuid>",
  "topic": "v1/devices/me/attributes",
  "data": { "gatewayOnline": true }
}
```

Gateway variant (`apps/core/management/mq/attributes.py:158-162`): `topic` starts with
`v1/gateway/` and does not end with `request` → `data` is
`{"<sub_device_name>": {"<key>": value, ...}}`.

## `v1/devices/me/attributes/request` — inbound, shared-attribute request

Source: `apps/core/management/commands/mq_async.py:201-231`

```json
{
  "sourceDeviceUUID": "<device_uuid>",
  "topic": "v1/devices/me/attributes/request",
  "data": { "id": 123, "keys": ["dnd", "someSharedKey"] }
}
```

`keys` may instead arrive as `"sharedKeys": "dnd,someSharedKey"` (comma-separated string).
Response is published to `fromGRMS`:

```json
{
  "targetDeviceUUID": "<device_uuid>",
  "topic": "v1/devices/me/attributes/response",
  "data": { "dnd": 1 }
}
```

## `v1/gateway/attributes/request` — inbound, sub-device attribute request

Same handler as above, with an extra `"device"` field:

```json
{
  "sourceDeviceUUID": "<gateway_uuid>",
  "topic": "v1/gateway/attributes/request",
  "data": { "device": "<sub_device_name>", "id": 123, "keys": ["dnd"] }
}
```

Response to `fromGRMS`:

```json
{
  "targetDeviceUUID": "<gateway_uuid>",
  "topic": "v1/gateway/attributes",
  "data": { "device": "<sub_device_name>", "data": { "dnd": 1 }, "id": 123 }
}
```

## `v1/gateway/rpc` — inbound, RPC confirmation from device

Source: `apps/core/management/mq/rpc_message.py`

```json
{
  "sourceDeviceUUID": "<gateway_uuid>",
  "topic": "v1/gateway/rpc",
  "data": { "id": 42, "data": { "success": true } }
}
```

`data.id` is the `RPCMessage.id` set by Django on the original outbound RPC request;
`handle_rpc()` marks that row `received=True` and stores `data.data` as `additional_info`.

## `toGRMS` — inbound, generic catch-all from mqtt-broker

Same common envelope (`sourceDeviceUUID`, `topic`, `data`) — routing inside
`BatchAccumulator.process_batch` (`mq_async.py:301-405`) is entirely by `topic`, so this queue
can carry any of the message shapes above plus `v1/gateway/connect` / `v1/gateway/disconnect`.
Produced by the external `mqtt-broker` image (`registry.gitlab.com/grms1/mqtt-broker`), not
part of this repo — the contract above is inferred from the consumer side.

## `fromGRMS` — **outbound** (Django → device, via mqtt-broker)

Three shapes currently produced:

1. Attribute-request response — see above (`mq_async.py:213-229`).
2. Access-control command (write RFID / set PIN), `apps/access_manager/utilits/prepare_rpc_request.py:44-50`:

   ```json
   {
     "targetDeviceUUID": "<gateway_uuid>",
     "topic": "v1/gateway/rpc",
     "data": {
       "device": "<sub_device_name>",
       "data": {
         "id": 42,
         "method": "writeRFID",
         "params": {},
         "timeout": 10000
       }
     }
   }
   ```

   `method` is also `add_pwd` / `delete_pwd` for PIN codes.

3. FIAS card-operation confirmation, `apps/core/management/mq/fias/utils/rpc.py:19-33` —
   `method: "confirmCardOperation"`.
4. Room attribute/status push, `apps/main/signals.py:222-230` — `method: "setAttribute"`, or
   `topic: "v1/gateway/attributes"` for shared-scope attributes.

## `pmsMessages` — inbound, handled by a **separate consumer** (`pms_handler.py`, not `mq_async`)

Source: `apps/mews/handlers.py:313-320`

```json
{
  "topic": "checkin",
  "data": {
    "hotel_id": "78061956-4619-4da6-b18a-eb9f39daa500",
    "first_name": "John",
    "last_name": "Doe",
    "room_number": "101",
    "check_in_date": "2026-07-28T14:00:00Z",
    "check_out_date": "2026-07-30T11:00:00Z",
    "gender": "",
    "language": "en",
    "nationality": "",
    "birthday": "",
    "pms_id": "12345",
    "type": "Reservation",
    "state": "Started",
    "event_type": "checkin",
    "additional_info": {
      "mews_customer_id": "...",
      "mews_resource_id": "...",
      "mews_reservation_id": "..."
    }
  }
}
```

`topic` is one of `checkin | checkout | reservation | canceled`
(`apps/services/management/commands/pms_handler.py:ROUTES`). Anything else is republished to
`pmsUnhandled` with an added `"unhandled": true` flag.
