from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_card_log_updates_batch(card_logs: list):
    channel_layer = get_channel_layer()
    if not channel_layer or not card_logs:
        return

    card_logs_data = []
    for card_log in card_logs:
        card_logs_data.append({
            "id": str(card_log.id) if card_log.id else None,
            "tenant_id": str(card_log.tenant_id),
            "device_id": str(card_log.device_id),
            "number": card_log.number,
            "event_ts": card_log.event_ts.isoformat() if card_log.event_ts else None,
            "access_group": card_log.access_group,
            "created_at": card_log.created_at.isoformat() if card_log.created_at else None,
            "staff_id": str(card_log.staff_id) if card_log.staff_id else None,
            "staff_name": str(card_log.staff) if card_log.staff else None,
            "guest_id": str(card_log.guest_id) if card_log.guest_id else None,
            "guest_name": str(card_log.guest) if card_log.guest else None,
        })

    payload = {"type": "get_list_activity", "card_logs": card_logs_data}
    async_to_sync(channel_layer.group_send)("card_logs", payload)