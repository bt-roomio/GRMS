from card.querysets.group import GroupQuerySet
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint

from core.models import BaseModel, CreatedByModel, UpdateByModel

DENIED = 0
GUEST = 1
HOUSEKEEPING = 2
ENGINEERING = 3
MASTER_CARD = 4
FAILED = 5


TYPE_CHOICES = (
    (DENIED, "DENIED"),
    (GUEST, "GUEST"),
    (HOUSEKEEPING, "HOUSEKEEPING"),
    (ENGINEERING, "ENGINEERING"),
    (MASTER_CARD, "MASTER CARD"),
    (FAILED, "FAILED"),
)


ALL_DAYS = "all_days"
MONDAY = "monday"
TUESDAY = "tuesday"
WEDNESDAY = "wednesday"
THURSDAY = "thursday"
FRIDAY = "friday"
SATURDAY = "saturday"
SUNDAY = "sunday"

WEEK_DAYS = (
    (ALL_DAYS, "ALL_DAYS"),
    (MONDAY, "MONDAY"),
    (TUESDAY, "TUESDAY"),
    (WEDNESDAY, "WEDNESDAY"),
    (THURSDAY, "THURSDAY"),
    (FRIDAY, "FRIDAY"),
    (SATURDAY, "SATURDAY"),
    (SUNDAY, "SUNDAY"),
)


class Group(BaseModel, CreatedByModel, UpdateByModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", on_delete=models.CASCADE)
    week_days = ArrayField(models.CharField(max_length=10, choices=WEEK_DAYS))
    start_time = models.TimeField()
    end_time = models.TimeField()
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)
    group_type = models.CharField(choices=TYPE_CHOICES, default=DENIED)

    objects = GroupQuerySet.as_manager()

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "card_groups"
        constraints = [
            UniqueConstraint(fields=["name", "tenant"], condition=Q(is_active=True), name="unique_card_group")
        ]

    def __str__(self):
        return f"{self.name} (Tenant: {self.tenant})"


class Card(BaseModel, CreatedByModel, UpdateByModel):
    number = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    is_active = models.BooleanField(default=True)

    KNX = models.IntegerField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "card_cards"
        constraints = [UniqueConstraint(fields=["number", "tenant"], condition=Q(is_active=True), name="unique_card")]

    def __str__(self):
        return f"Card #{self.number}"


class PublicSpace(BaseModel, CreatedByModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    device = models.ForeignKey("main.Device", models.CASCADE)
    dashboard = models.ForeignKey("main.Dashboard", models.SET_NULL, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_public_areas"


class NeedSyncDevice(BaseModel, CreatedByModel):
    device = models.ForeignKey("main.Device", models.CASCADE)
    card = models.ForeignKey("card.Card", models.CASCADE)
    need_sync = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_need_sync_devices"


class Staff(BaseModel, CreatedByModel):
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_staff"
        constraints = [
            UniqueConstraint(
                fields=["tenant", "first_name", "last_name"], condition=Q(is_active=True), name="unique_staff"
            )
        ]


class GroupRoom(BaseModel, CreatedByModel):
    group = models.ForeignKey("card.Group", models.CASCADE)
    room = models.ForeignKey("main.Room", models.CASCADE)
    staff = models.ForeignKey("card.Staff", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_group_rooms"

    def __str__(self):
        return f"{self.group} -> {self.room}"


class GroupPublicSpace(BaseModel, CreatedByModel):
    group = models.ForeignKey("card.Group", models.CASCADE)
    public_space = models.ForeignKey("card.PublicSpace", models.CASCADE)
    staff = models.ForeignKey("card.Staff", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_group_public_spaces"

    def __str__(self):
        return f"{self.group} -> {self.public_space}"


class GuestPublicSpace(BaseModel):
    guest = models.ForeignKey("main.Guest", models.CASCADE)
    public_space = models.ForeignKey("card.PublicSpace", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "card_guest_public_spaces"

    def __str__(self):
        return f"{self.guest} -> {self.public_space}"
