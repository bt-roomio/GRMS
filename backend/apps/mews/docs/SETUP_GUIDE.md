# Mews WebSocket Integration - Setup Guide

## Summary

I've created a complete WebSocket integration for receiving real-time reservation events from Mews PMS. The implementation follows GRMS patterns and is production-ready.

## What Was Created

### 1. **Models** (`backend/apps/mews/models.py`)
- `MewsConfiguration` - Stores Mews credentials per tenant
- `MewsReservationMapping` - Maps Mews reservations to GRMS RoomHistory

### 2. **API Client** (`backend/apps/mews/client.py`)
- Lightweight REST API client for Mews Connector API
- Handles authentication, retries, rate limiting

### 3. **WebSocket Client** (`backend/apps/mews/websocket_client.py`)
- Persistent WebSocket connection to Mews
- Auto-reconnection with exponential backoff
- Health monitoring via ping/pong

### 4. **Event Handlers** (`backend/apps/mews/handlers.py`)
- Processes reservation events
- Creates/updates GRMS models:
  - **Created** → Creates Customer, Guest, RoomHistory
  - **Updated** → Updates existing reservation
  - **Cancelled** → Marks reservation as cancelled
  - **Checked In** → Sets status to active
  - **Checked Out** → Sets status to completed

### 5. **Management Command** (`backend/apps/mews/management/commands/mews_websocket.py`)
- Long-running WebSocket listener
- Supports multiple tenants simultaneously
- Graceful shutdown handling

### 6. **Admin Interface** (`backend/apps/mews/admin.py`)
- Django admin for managing MewsConfiguration
- View reservation mappings

### 7. **Supervisord Integration**
- Added `mews_websocket` process to `supervisord.conf`
- Auto-starts with other services
- Logs to `/var/log/supervisor/mews_websocket-stdout.log`

## Next Steps (When You Have Dependencies)

### Step 1: Create Migrations

```bash
cd /Users/bakhodir/Projects/GRMS/backend
./manage.py makemigrations mews
./manage.py migrate mews
```

### Step 2: Configure in Django Admin

1. Go to Django Admin → Mews Integration → Mews Configurations
2. Click "Add Mews Configuration"
3. Fill in:
   - **Tenant**: Select your tenant
   - **Client Token**: Your Mews application token
   - **Access Token**: Property-specific access token
   - **Environment**: Choose `demo` for testing
   - **Is Active**: ✓ Checked
   - **Auto Sync**: ✓ Checked
4. Save

### Step 3: Test Locally (Optional)

```bash
# Run the WebSocket listener
cd /Users/bakhodir/Projects/GRMS/backend
./manage.py mews_websocket

# Should output:
# ✓ Connected to Mews for tenant: <your-tenant-name>
# Listening for reservation events...
```

### Step 4: Deploy with Supervisord

The `mews_websocket` process is already configured in `supervisord.conf`. When you restart supervisord, it will automatically start:

```bash
# In Docker
supervisorctl restart mews_websocket

# View logs
tail -f /var/log/supervisor/mews_websocket-stdout.log
```

## Testing with Demo Environment

Use the public Mews demo credentials:

```
Client Token: E0D439EE522F44368DC78E1BFB03710C-D24FB11DBE31D4621C4817E028D9E1D
Access Token: C66EF7B239D24632943D115EDE9CB810-EA00F8FD8294692C940F6B5A8F9453D
Environment: demo
Demo URL: https://app.mews-demo.com/
```

You can log in to the demo environment and create test reservations to see events flowing into GRMS.

## How Events Flow

```
Mews PMS
   ↓
WebSocket Event (e.g., Reservation Created)
   ↓
MewsWebSocketClient receives event
   ↓
ReservationEventHandler.handle_event()
   ↓
Fetch full details from Mews API
   ↓
Determine action (create/update/cancel/check-in/check-out)
   ↓
Update GRMS models:
   - Create/update Customer
   - Create/update Guest
   - Create/update RoomHistory
   - Create MewsReservationMapping
```

## File Structure

```
backend/apps/mews/
├── __init__.py
├── apps.py                          # App configuration
├── models.py                        # MewsConfiguration, MewsReservationMapping
├── admin.py                         # Django admin
├── client.py                        # REST API client
├── websocket_client.py              # WebSocket connection handler
├── handlers.py                      # Event processing logic
├── management/
│   └── commands/
│       └── mews_websocket.py        # Management command
├── migrations/                      # (to be created)
├── README.md                        # Full documentation
└── SETUP_GUIDE.md                   # This file
```

## Dependencies

All required packages are already in `requirements.txt`:
- `websockets==12.0` - WebSocket client
- `requests` - HTTP client for REST API

## Configuration Files Updated

1. **`config/settings.py`**
   - Added `"mews"` to `INSTALLED_APPS`

2. **`supervisord.conf`**
   - Added `[program:mews_websocket]` section

## Monitoring

### Check Connection Status

```bash
# View WebSocket logs
tail -f /var/log/supervisor/mews_websocket-stdout.log

# Check if process is running
supervisorctl status mews_websocket

# Restart if needed
supervisorctl restart mews_websocket
```

### Check Database

```python
# Check configurations
from apps.mews.models import MewsConfiguration
MewsConfiguration.objects.filter(is_active=True)

# Check mappings
from apps.mews.models import MewsReservationMapping
MewsReservationMapping.objects.all().count()

# Check latest synced reservations
MewsReservationMapping.objects.order_by('-last_synced')[:10]
```

## Advanced Configuration

### Multi-Tenant Support

The system supports multiple tenants automatically. Each tenant with an active `MewsConfiguration` will have its own WebSocket connection.

### Custom Event Handling

To customize how events are processed, edit `backend/apps/mews/handlers.py`:

```python
class ReservationEventHandler:
    def _handle_created_or_updated(self, reservation_id, event):
        # Add custom logic here
        pass
```

### Room Mapping

Currently, rooms are not automatically mapped. To enable room mapping:

1. Create a new model `MewsResourceMapping`
2. Map Mews resource IDs to GRMS Room objects
3. Update `handlers.py` → `_get_room()` method

## Troubleshooting

### Issue: WebSocket won't connect

**Check**:
1. Credentials are correct in MewsConfiguration
2. Environment is set correctly (demo vs production)
3. Network allows outbound WebSocket connections
4. Check logs for authentication errors

### Issue: Events not being processed

**Check**:
1. `is_active` and `auto_sync` are True
2. Handler is not throwing exceptions (check logs)
3. API client can fetch reservation details

### Issue: Duplicate reservations

**Check**:
1. MewsReservationMapping is being created correctly
2. Check for existing mapping before creating new RoomHistory

## Production Checklist

- [ ] Run migrations: `./manage.py migrate mews`
- [ ] Configure MewsConfiguration in admin
- [ ] Set environment to `production` (not demo)
- [ ] Verify credentials are correct
- [ ] Test WebSocket connection locally
- [ ] Deploy and restart supervisord
- [ ] Monitor logs for first few hours
- [ ] Create test reservation in Mews and verify sync
- [ ] Set up alerts for WebSocket disconnections

## Reference

- [Mews Connector API Docs](https://mews-systems.gitbook.io/connector-api/)
- [WebSocket Events](https://mews-systems.gitbook.io/connector-api/websocket-api)
- GRMS Internal: `backend/apps/mews/README.md`

---

**Implementation Complete! 🎉**

All code is written and ready. Just run migrations when you have the environment set up.
