import json

from access_manager.models import Card
from access_manager.serializers.card import CardFilterParams, CardSerializer
from channels.db import database_sync_to_async

from core.utils.pagination import pagination
from shuttle.consumers.utils.encoders import UUIDEncoder
from shuttle.utils.response import response


async def card_list(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    try:
        filters = cmd.get("query", {}).get("filters", {})
        page_link = cmd.get("query", {}).get("page_link", {})
        params = await database_sync_to_async(CardFilterParams.check)({**filters, **page_link})
        rooms = await get_cards(params, user)
        result["data"] = rooms
    except Exception as err:
        result["error_code"] = 400
        result["error_msg"] = str(err)
        return result
    return result


@database_sync_to_async
def get_cards(params, user):
    queryset = Card.objects.list(  # pyright: ignore
        tenant_id=user.tenant_id,
        sort_by=params.get("sort_by", []),  # pyright: ignore
        search_field=params.get("search_field"),  # pyright: ignore
        search_value=params.get("search_value"),  # pyright: ignore
    )
    serializer = CardSerializer(queryset, many=True)
    data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
    return json.loads(json.dumps(data, cls=UUIDEncoder))
