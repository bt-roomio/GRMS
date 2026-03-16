from django.db.models import F, Prefetch, Q

from core.querysets.base_queryset import BaseQuerySet


class AttributeKvQuerySet(BaseQuerySet):
    def get_attributes(self, device, scope, sort_by=[]):
        query = (
            self.filter(entity=device, attribute_type=scope)
            .annotate(key_name=F("attribute_key"))
            .values("last_update_ts", "str_v", "bool_v", "json_v", "long_v", "dbl_v", "key_name")
            .order_by(*sort_by)
        )
        cleaned_data = []
        for record in query:
            # First rename fields, then filter out None values except for value field
            renamed = {}
            value_field = None
            for k, v in record.items():
                if k in ["last_update_ts", "key_name"]:
                    if v is not None:
                        renamed[k] = v
                else:
                    # This is one of the value fields (str_v, bool_v, etc.)
                    if v is not None:
                        value_field = v

            # Always include 'value' field, even if None
            renamed["value"] = value_field
            cleaned_data.append(renamed)

        return cleaned_data

    def unique_keys_by_tenant(self, tenant_id, scope):
        return (
            self.filter(entity__tenant_id=tenant_id, attribute_type=scope)
            .values_list("attribute_key", flat=True)
            .distinct()
            .order_by("attribute_key")
        )

    def update_or_create_or_delete(self, devices, room):
        from shuttle.models import AttributeKv

        for device in devices:
            self.update_or_create(
                entity_id=device.id,
                attribute_type=AttributeKv.SHARED_SCOPE,
                attribute_key="roomNumber",
                defaults={"str_v": room.number},
            )

        self.filter(entity__room=room, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key="roomNumber").exclude(
            entity_id__in=devices
        ).update(str_v=None)

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
                    queryset=AttributeKv.objects.filter(attribute_key="ipAddress").order_by("-last_update_ts"),
                    to_attr="prefetched_ip_attrs",
                ),
            )
            .order_by(*order)
            .distinct()
        )
        return qs
