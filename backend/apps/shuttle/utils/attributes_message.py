def build_attributes_message(device, gateway_id, attributes: dict) -> dict:
    """
    RabbitMQ message that pushes shared attributes to a device: straight to a gateway,
    or through its parent gateway (``gateway_id``) for a sub-device.
    """
    if device.additional_info and device.additional_info.get("gateway"):
        return {"targetDeviceUUID": str(device.id), "topic": "v1/devices/me/attributes", "data": attributes}
    return {
        "targetDeviceUUID": str(gateway_id),
        "topic": "v1/gateway/attributes",
        "data": {"device": device.name, "data": attributes},
    }
