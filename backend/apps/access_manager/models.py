from uuid import UUID

from access_manager.querysets.card import CardQuerySet
from access_manager.querysets.group import GroupQuerySet, GroupRoomQuerySet
from access_manager.querysets.guest_card import GuestCardQuerySet
from access_manager.querysets.need_sync import NeedSyncDeviceQuerySet
from access_manager.querysets.staff import StaffQuerySet
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone

from access_manager.querysets.card_log import CardLogQuerySet
from core.models import BaseModel, CreatedByModel, UpdateByModel


class TypeChoices(models.IntegerChoices):
    HOUSEKEEPING = 2, "HOUSEKEEPING"
    ENGINEERING = 3, "ENGINEERING"
    MASTER_CARD = 4, "MASTER_CARD"


class AccessGroupChoices(models.IntegerChoices):
    DENIED = 0, "DENIED"
    GUEST = 1, "GUEST"
    HOUSEKEEPING = 2, "HOUSEKEEPING"
    ENGINEERING = 3, "ENGINEERING"
    MASTER_CARD = 4, "MASTER_CARD"
    FAILED = 5, "FAILED"


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
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)
    group_type = models.IntegerField(
        choices=TypeChoices.choices,
        help_text="Must be one of: HOUSEKEEPING, ENGINEERING, MASTER_CARD",
    )

    objects = GroupQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "access_manager_groups"
        constraints = [
            UniqueConstraint(fields=["name", "tenant"], condition=Q(is_active=True), name="unique_card_group")
        ]


class Card(BaseModel, CreatedByModel, UpdateByModel):
    number = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)

    KNX = models.IntegerField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = CardQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "access_manager_cards"
        unique_together = ("number", "tenant")


class CardLog(BaseModel, CreatedByModel, UpdateByModel):
    created_at: models.DateTimeField = models.DateTimeField(default=timezone.now)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    number = models.CharField(max_length=200)
    event_ts = models.DateTimeField()
    access_group = models.IntegerField(
        choices=AccessGroupChoices.choices,
        help_text="Must be one of: HOUSEKEEPING, ENGINEERING, MASTER_CARD",
    )

    device = models.ForeignKey("main.Device", models.DO_NOTHING)
    staff = models.ForeignKey("access_manager.Staff", models.DO_NOTHING, null=True, blank=True,
                              related_name="card_logs")
    guest = models.ForeignKey("main.Guest", models.DO_NOTHING, null=True, blank=True, related_name="card_logs")

    additional_info = models.JSONField(null=True, blank=True)

    objects = CardLogQuerySet.as_manager()

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "access_manager_card_logs"
        ordering = ["-event_ts"]

    def __str__(self):
        return f"{self.number} - {self.device} - {self.event_ts} - {self.access_group}"


class NeedSyncDevice(BaseModel, CreatedByModel):
    device = models.ForeignKey("main.Device", models.CASCADE)
    card = models.ForeignKey("access_manager.Card", models.CASCADE)
    need_sync = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = NeedSyncDeviceQuerySet.as_manager()

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_need_sync_devices"


class Staff(BaseModel, CreatedByModel):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    group = models.ForeignKey("access_manager.Group", models.SET_NULL, null=True, blank=True)
    group_id: UUID
    additional_info = models.JSONField(null=True, blank=True)

    tenant = models.ForeignKey("main.Tenant", models.CASCADE)

    objects = StaffQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    def get_name(self):
        return str(self.first_name + " " + self.last_name)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_staff"
        constraints = [
            UniqueConstraint(
                fields=["tenant", "first_name", "last_name"], condition=Q(is_active=True), name="unique_staff"
            )
        ]


class StaffCard(BaseModel, CreatedByModel):
    staff = models.ForeignKey("access_manager.Staff", models.CASCADE)
    card = models.OneToOneField("access_manager.Card", models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_staff_cards"
        constraints = [UniqueConstraint("staff", "card", condition=Q(is_active=True), name="unique_active_staff_card")]


class GuestCard(BaseModel, CreatedByModel):
    guest = models.ForeignKey("main.Guest", models.CASCADE)
    card = models.ForeignKey("access_manager.Card", models.CASCADE)
    is_active = models.BooleanField(default=True)

    objects = GuestCardQuerySet.as_manager()

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_guest_cards"
        constraints = [
            UniqueConstraint(fields=["card"], condition=Q(is_active=True), name="unique_card_active"),
        ]


class GroupRoom(BaseModel, CreatedByModel):
    group = models.ForeignKey("access_manager.Group", models.CASCADE, "group_room")
    room = models.ForeignKey("main.Room", models.CASCADE, "group_room")
    additional_info = models.JSONField(null=True, blank=True)

    objects = GroupRoomQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_group_rooms"


class GroupPublicSpace(BaseModel, CreatedByModel):
    group = models.ForeignKey("access_manager.Group", models.CASCADE, "group_public_space")
    public_space = models.ForeignKey("main.PublicSpace", models.CASCADE, "group_public_space")
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_group_public_spaces"

    def __str__(self):
        return f"{self.group} -> {self.public_space}"


class GuestPublicSpace(BaseModel):
    guest = models.ForeignKey("main.Guest", models.CASCADE)
    public_space = models.ForeignKey("main.PublicSpace", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "access_manager_guest_public_spaces"

    def __str__(self):
        return f"{self.guest} -> {self.public_space}"
