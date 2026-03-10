from _typeshed import Incomplete

from core.models import BaseModel, UpdateByModel


class MewsConfiguration(BaseModel, UpdateByModel):
    tenant: Incomplete
    client_token: Incomplete
    access_token: Incomplete
    company_id: Incomplete
    environment: Incomplete
    is_active: Incomplete
    auto_sync: Incomplete
    last_sync: Incomplete

    @property
    def api_base_url(self) -> str | None: ...
    @property
    def ws_url(self) -> str | None: ...

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        verbose_name: str
        verbose_name_plural: str
