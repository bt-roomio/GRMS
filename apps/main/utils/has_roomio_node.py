from main.models import Device


def has_roomio_node(tenant_id):
    devices = Device.objects.filter(tenant_id=tenant_id).values_list("additional_info", flat=True)
    for d in list(devices):
        if isinstance(d, dict) and "roomio_node" in d and d.get("roomio_node"):
            return True
    return False
