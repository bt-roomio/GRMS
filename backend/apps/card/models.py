import time

from card.querysets.group import GroupQuerySet
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint

from core.models import BaseModel, CreatedByModel
from core.utils.unix_timestamp import UnixTimeStampField

DENIED = 0
GUEST = 1
HOUSEKEEPING = 2
ENGINEERING = 3
MASTER_CARD = 4
FAILED = 5


CARD_TYPE_CHOICES = (
    (DENIED, "DENIED"),
    (GUEST, "GUEST"),
    (HOUSEKEEPING, "HOUSEKEEPING"),
    (ENGINEERING, "ENGINEERING"),
    (MASTER_CARD, "MASTER CARD"),
    (FAILED, "FAILED"),
)


MONDAY = "monday"
TUESDAY = "tuesday"
WEDNESDAY = "wednesday"
THURSDAY = "thursday"
FRIDAY = "friday"
SATURDAY = "saturday"
SUNDAY = "sunday"

WEEK_DAYS = (
    (SUNDAY, "SUNDAY"),
    (MONDAY, "MONDAY"),
    (TUESDAY, "TUESDAY"),
    (WEDNESDAY, "WEDNESDAY"),
    (THURSDAY, "THURSDAY"),
    (FRIDAY, "FRIDAY"),
    (SATURDAY, "SATURDAY"),
)


class PublicAreas(BaseModel, CreatedByModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    device = models.ForeignKey("main.Device", models.SET_NULL, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_public_areas"


class Group(BaseModel, CreatedByModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", on_delete=models.CASCADE)
    week_days = ArrayField(models.CharField(max_length=10, choices=WEEK_DAYS))
    start_time = models.TimeField()
    end_time = models.TimeField()
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = GroupQuerySet.as_manager()

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_groups"
        constraints = [
            UniqueConstraint(fields=["name", "tenant"], condition=Q(is_active=True), name="unique_card_group")
        ]

    def __str__(self):
        return f"{self.name} (Tenant: {self.tenant})"


class Staff(BaseModel, CreatedByModel):
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(choices=CARD_TYPE_CHOICES, default=GUEST)
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


class Card(BaseModel, CreatedByModel):
    revoked_at = UnixTimeStampField(default=time.time, null=True)
    number = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    card_type = models.PositiveIntegerField(choices=CARD_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    staff = models.ForeignKey("card.Staff", models.SET_NULL, null=True, blank=True)
    guest = models.ForeignKey("main.Guest", models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey("card.Group", models.SET_NULL, null=True, blank=True)

    KNX = models.IntegerField(null=True, blank=True)
    need_sync = models.IntegerField(default=0)
    public_areas = models.ForeignKey("card.PublicAreas", models.SET_NULL, null=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "card_cards"
        constraints = [UniqueConstraint(fields=["number", "tenant"], condition=Q(is_active=True), name="unique_card")]

    def __str__(self):
        return f"Card #{self.number}"


class GroupRoom(BaseModel):
    group = models.ForeignKey("card.Group", models.CASCADE)
    room = models.ForeignKey("main.Room", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "card_group_rooms"

    def __str__(self):
        return f"{self.group} -> {self.room}"


class AccessLog(BaseModel):
    card_number = models.CharField(max_length=255)
    device = models.ForeignKey("main.Device", models.SET_NULL, null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    is_success = models.BooleanField(default=False)

    staff = models.ForeignKey("card.Staff", models.SET_NULL, null=True, blank=True)
    guest = models.ForeignKey("main.Guest", models.SET_NULL, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "card_access_logs"

    def __str__(self):
        return f"{self.card_number} -> {self.device}"
