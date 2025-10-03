from django.db.models import F
from django.db.models import Prefetch, Q

from core.querysets.base_queryset import BaseQuerySet


class AttributeKvQuerySet(BaseQuerySet):
    def get_attributes(self, device, scope, sort_by=[]):
        query = (
            self.filter(entity=device, attribute_type=scope)
            .annotate(key_name=F("attribute_key"))
            .values("last_update_ts", "str_v", "bool_v", "json_v", "long_v", "dbl_v", "key_name")
            .order_by(*sort_by)
        )
        cleaned_data = [{k: v for k, v in record.items() if v is not None} for record in query]
        cleaned_data = [
            {(k if k in ["last_update_ts", "key_name"] else "value"): v for k, v in record.items()}
            for record in cleaned_data
        ]

        return cleaned_data

    def update_or_create_or_delete(self, devices, room):
        from shuttle.models import AttributeKv

        for device in devices:
            self.update_or_create(
                entity_id=device.id,
                attribute_type=AttributeKv.SHARED_SCOPE,
                attribute_key="roomNumber",
                defaults={"long_v": room.number},
            )

        self.filter(entity__room=room, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key="roomNumber").exclude(
            entity_id__in=devices
        ).update(long_v=None)


    def inactive_devices_in_spaces(self, tenant_id, sort_by="-last_update_ts"):
        from main.models import DevicePublicSpaces
        from shuttle.models import AttributeKv

        order = (sort_by,) if isinstance(sort_by, str) else tuple(sort_by or ("-last_update_ts",))


        qs = (
            self.filter(
                entity__tenant_id=tenant_id,
                attribute_type=AttributeKv.SERVER_SCOPE,
                attribute_key="active",
                bool_v=False,
            )
            .filter(Q(entity__room__isnull=False) | Q(entity__device_public_spaces__isnull=False))
            .select_related("entity", "entity__room", "entity__device_profile", "entity__tenant")
            .prefetch_related(
                Prefetch(
                    "entity__device_public_spaces",
                    queryset=DevicePublicSpaces.objects.select_related("public_space"),
                    to_attr="prefetched_device_public_spaces",
                ),
                Prefetch(
                    "entity__attribute_kvs",
                    queryset=AttributeKv.objects.filter(
                        attribute_key="ipAddress"
                    ).order_by("-last_update_ts"),
                    to_attr="prefetched_ip_attrs",
                ),
            )
            .order_by(*order)
            .distinct()
        )
        return qs
