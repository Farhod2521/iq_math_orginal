from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def group_name(room_id):
    return f"battle_{room_id}"


def send_event(room_id, event_type, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(group_name(room_id), {
        "type": "battle.event",
        "event": event_type,
        "payload": payload,
    })
