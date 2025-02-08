from main.models import Device


def has_roomio_node(tenant_id, self=None):
    if (
        Device.objects.is_active()
        .exclude(id=self)
        .filter(tenant_id=tenant_id, additional_info__roomio_node=True)
        .exists()
    ):
        return True
    return False
