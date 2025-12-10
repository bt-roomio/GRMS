# Mews Integration for GRMS

Real-time WebSocket integration for syncing reservations from Mews PMS to GRMS.

## Features

- **Real-time Sync**: WebSocket connection for instant reservation updates
- **Auto-reconnection**: Automatic reconnection with exponential backoff
- **Event Detection**: Handles add/update/delete/check-in/check-out events
- **Multi-tenant**: Supports multiple properties with separate configurations

## Components

### 1. Models (`models.py`)
- `MewsConfiguration`: Stores Mews credentials per tenant
- `MewsReservationMapping`: Maps Mews reservation IDs to GRMS RoomHistory

### 2. API Client (`client.py`)
- Simple REST API client for Mews Connector API v1
- Handles authentication, retry logic, rate limiting

### 3. WebSocket Client (`websocket_client.py`)
- Maintains persistent WebSocket connection to Mews
- Auto-reconnect with exponential backoff
- Ping/pong health monitoring

### 4. Event Handlers (`handlers.py`)
- Processes reservation events (Created, Updated, Cancelled, Checked In, Checked Out)
- Fetches full details from API
- Creates/updates GRMS models (Customer, Guest, RoomHistory)

### 5. Management Command (`management/commands/mews_websocket.py`)
- Long-running process managed by supervisord
- Listens for all active tenant configurations

## Setup

### 1. Run Migrations

```bash
cd /Users/bakhodir/Projects/GRMS/backend
./manage.py makemigrations mews
./manage.py migrate mews
```

### 2. Configure Mews Integration

In Django Admin, create a `MewsConfiguration` for your tenant:

- **Tenant**: Select your tenant
- **Client Token**: Your Mews ClientToken (application identifier)
- **Access Token**: Property-specific AccessToken from Mews
- **Environment**: `demo` or `production`
- **Is Active**: Enable integration
- **Auto Sync**: Enable real-time sync

### 3. Start WebSocket Listener

The WebSocket listener runs automatically via supervisord:

```bash
# Manually test the command
./manage.py mews_websocket

# Or for specific tenant
./manage.py mews_websocket --tenant-id=<tenant-uuid>
```

### 4. Supervisord Integration

The `mews_websocket` process is already configured in `supervisord.conf` and will start automatically with other services.

View logs:
```bash
tail -f /var/log/supervisor/mews_websocket-stdout.log
```

## How It Works

1. **WebSocket Connection**: The `mews_websocket` management command connects to Mews WebSocket API using credentials from `MewsConfiguration`

2. **Event Received**: When a reservation changes in Mews, an event is sent via WebSocket:
   ```json
   {
     "Events": [{
       "Type": "Reservation",
       "Id": "reservation-uuid",
       "State": "Confirmed"
     }]
   }
   ```

3. **Event Processing**:
   - Handler receives event
   - Fetches full reservation details via REST API
   - Determines action (created/updated/cancelled/checked-in/checked-out)
   - Updates GRMS models

4. **GRMS Sync**:
   - **Created**: Creates Customer, Guest, and RoomHistory
   - **Updated**: Updates RoomHistory dates/room assignment
   - **Cancelled**: Marks RoomHistory as cancelled
   - **Checked In**: Sets RoomHistory status to active
   - **Checked Out**: Sets RoomHistory status to completed

## Event Types

| Mews State | GRMS Action | Description |
|------------|-------------|-------------|
| Confirmed | Create/Update | New reservation or reservation confirmed |
| Started | Check-in | Guest has checked in |
| Processed | Check-out | Guest has checked out |
| Canceled | Cancel | Reservation cancelled |
| Optional | Create/Update | Optional booking |
| Requested | Create/Update | Booking request |

## Testing

### Demo Environment

Use the public Mews demo credentials for testing:

```python
# Demo credentials (from Mews public docs)
CLIENT_TOKEN = "E0D439EE522F44368DC78E1BFB03710C-D24FB11DBE31D4621C4817E028D9E1D"
ACCESS_TOKEN = "C66EF7B239D24632943D115EDE9CB810-EA00F8FD8294692C940F6B5A8F9453D"
ENVIRONMENT = "demo"
```

### Manual Test

```bash
cd /Users/bakhodir/Projects/GRMS/backend
./manage.py shell
```

```python
from apps.mews.models import MewsConfiguration
from apps.main.models import Tenant

# Get or create tenant
tenant = Tenant.objects.first()

# Create configuration
config = MewsConfiguration.objects.create(
    tenant=tenant,
    client_token="E0D439EE522F44368DC78E1BFB03710C-D24FB11DBE31D4621C4817E028D9E1D",
    access_token="C66EF7B239D24632943D115EDE9CB810-EA00F8FD8294692C940F6B5A8F9453D",
    environment="demo",
    is_active=True,
    auto_sync=True,
)

# Test API client
from apps.mews.client import MewsAPIClient

client = MewsAPIClient(
    client_token=config.client_token,
    access_token=config.access_token,
    base_url=config.api_base_url,
)

# Get configuration
info = client.get_configuration()
print(f"Connected to: {info['Enterprise']['Name']}")

# Test WebSocket (run in separate terminal)
./manage.py mews_websocket --tenant-id=<your-tenant-id>
```

## Room Mapping (TODO)

Currently, room mapping is not implemented. Mews resource IDs are not automatically mapped to GRMS rooms. This can be added by:

1. Creating a `MewsResourceMapping` model
2. Mapping Mews resource IDs to GRMS Room objects
3. Using the mapping in `handlers.py` `_get_room()` method

## Troubleshooting

### Connection Issues

**Problem**: WebSocket not connecting

**Solutions**:
- Check credentials in MewsConfiguration
- Verify `is_active` and `auto_sync` are True
- Check logs: `/var/log/supervisor/mews_websocket-stdout.log`
- Test environment: Use `demo` first before `production`

### No Events Received

**Problem**: Connected but no events coming through

**Solutions**:
- Create a test reservation in Mews demo environment
- Check Mews WebSocket is sending events (they should appear in logs)
- Verify event handler is processing events

### Duplicate Reservations

**Problem**: Same reservation created multiple times

**Solutions**:
- Check `MewsReservationMapping` table for existing mappings
- Ensure `mews_reservation_id` is unique
- Handler should check for existing mapping before creating

## API Documentation

- [Mews Connector API](https://mews-systems.gitbook.io/connector-api/)
- [WebSocket Events](https://mews-systems.gitbook.io/connector-api/websocket-api)
- [Reservation Operations](https://mews-systems.gitbook.io/connector-api/operations/reservations)

## Notes

- WebSocket connection requires no spaces around `=` in cookie header
- API rate limit: 200 requests per 30 seconds per AccessToken
- All dates must be in UTC: `YYYY-MM-DDTHH:MM:SSZ`
- Maximum query interval: 3 months
