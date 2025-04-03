from django.db.models import F

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
