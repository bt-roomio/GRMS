from main.models import Device


def get_space(device_id):
    room_numbers = list(
        Device.objects.filter(id=device_id, room__isnull=False).values_list("room__number", flat=True).distinct()
    )

    public_space_names = list(
        Device.objects.filter(id=device_id, device_public_spaces__isnull=False)
        .values_list("device_public_spaces__public_space__name", flat=True)
        .distinct()
    )

    locations = [f"Room {num}" for num in room_numbers] + public_space_names
    return list(set(locations))
