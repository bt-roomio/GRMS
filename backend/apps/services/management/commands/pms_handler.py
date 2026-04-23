"""
Django Management Command: Handle PMS messages
Runs as a long-running process managed by supervisord
Get for real-time reservation events from RabbitMQ ( pmsMessages queue )
Process messages for checkin and checkout
"""

import json
import logging
import time

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from pika.adapters.blocking_connection import BlockingChannel

from rest_framework.fields import ValidationError

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.date import datetime_to_unix
from main.models import Guest, Room, Tenant
from main.observables.guest import publish_guest_changes
from shuttle.utils.access_cards import access_cards

logger = logging.getLogger(__name__)

PMS_MESSAGES_QUEUE = "pmsMessages"
PMS_UNHANDLED_QUEUE = "pmsUnhandled"


class Command(BaseCommand):
    help = "Handle PMS messages from rabbitMQ"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Starting PMS message handler for queue '{PMS_MESSAGES_QUEUE}'..."))

        try:
            credentials = pika.PlainCredentials(settings.RABBIT_LOGIN, settings.RABBIT_PASSWORD)
            parameters = pika.ConnectionParameters(settings.RABBIT_HOST, settings.RABBIT_PORT, "/", credentials)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare the queue (create if doesn't exist)
            channel.queue_declare(queue=PMS_MESSAGES_QUEUE, durable=True)

            connection.close()
            self.stdout.write(self.style.SUCCESS(f"Queue '{PMS_MESSAGES_QUEUE}' setup completed"))
        except Exception as e:
            logger.error(f"✗ Failed to setup queue '{PMS_MESSAGES_QUEUE}': {str(e)}")
            self.stdout.write(self.style.ERROR(f"✗ Failed to setup queue '{PMS_MESSAGES_QUEUE}': {e}"))
            return

        # Start consuming messages
        self.stdout.write(self.style.SUCCESS(f"Starting to consume messages from '{PMS_MESSAGES_QUEUE}'..."))
        self.consume_messages(PMS_MESSAGES_QUEUE)

    def consume_messages(self, queue_name: str):
        """Main consumer loop with automatic reconnection"""
        while True:
            try:
                credentials = pika.PlainCredentials(settings.RABBIT_LOGIN, settings.RABBIT_PASSWORD)
                parameters = pika.ConnectionParameters(settings.RABBIT_HOST, settings.RABBIT_PORT, "/", credentials)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()

                channel.queue_declare(queue=queue_name, durable=True, passive=True)

                def callback(
                    ch: BlockingChannel,
                    method: pika.spec.Basic.Deliver,
                    _: pika.BasicProperties,
                    body: bytes,
                ):
                    try:
                        self.process_pms_message(body)
                        if method.delivery_tag:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                    except ValidationError as e:
                        error_msg = e.detail[0] if isinstance(e.detail, list) else str(e.detail)
                        logger.error(f"[{queue_name}] ✗ Validation failed: {error_msg}")
                        self.stdout.write(self.style.ERROR(f"[{queue_name}] ✗ {error_msg}"))
                        # Acknowledge message - validation errors won't be fixed by retrying
                        if method.delivery_tag:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"[{queue_name}] ✗ Unexpected error: {str(e)}", exc_info=True)
                        # Acknowledge to prevent requeue loop
                        if method.delivery_tag:
                            ch.basic_ack(delivery_tag=method.delivery_tag)

                channel.basic_consume(queue=queue_name, on_message_callback=callback)
                self.stdout.write(self.style.SUCCESS(f"✓ Connected! Waiting for messages from '{queue_name}'..."))
                channel.start_consuming()

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.stdout.write(self.style.WARNING("\nShutting down gracefully..."))
                break
            except Exception as err:
                logger.error(f"[{queue_name}] ✗ Connection error: {str(err)}. Retrying in 5 seconds...")
                self.stdout.write(self.style.ERROR(f"[{queue_name}] Connection lost. Retrying in 5 seconds..."))
                time.sleep(5)

    def _republish_unhandled(self, message: dict, event_type: str):
        """Republish unhandled messages to pmsUnhandled queue with unhandled flag"""
        try:
            message["unhandled"] = True
            channel = connect_to_rabbitmq()
            channel.queue_declare(queue="pmsUnhandled", durable=True)
            send_to_rabbitmq(channel, message, routing_key="pmsUnhandled")
            channel.connection.close()
            logger.info(f"✓ Republished unhandled event_type={event_type!r} to pmsUnhandled")
        except Exception as e:
            logger.error(f"✗ Failed to republish unhandled message: {e}")

    def process_pms_message(self, body: bytes):
        """Process PMS message - implement business logic here"""
        try:
            message = json.loads(body.decode("utf-8"))
            event_type = message.get("topic")  # e.g., "checkin", "checkout"
            reservation_data = message.get("data")
            logger.info(f"✓ Received message: {message}")

            if event_type not in ROUTES:
                logger.warning(f"⚠ Unhandled event type: {event_type!r}")
                self._republish_unhandled(message, event_type)
                return

            validated_data = self._base_validate_data(reservation_data)
            ROUTES[event_type](validated_data)

        except json.JSONDecodeError as e:
            logger.error(f"✗ Failed to decode message: {str(e)}")
            raise ValidationError("Invalid JSON format")
        except (ValidationError, Exception):
            raise

    def _base_validate_data(self, data):
        tenants = Tenant.objects.filter(
            additional_info__integration_settings__mews__hotel_id=data.get("hotel_id"),
            additional_info__integration_settings__mews__enable=True,
        )
        if tenants.count() > 1:
            logger.warning(f"Found multiple tenants for hotel_id: {data.get('hotel_id')}")

        tenant: Tenant | None = tenants.first()

        if not tenant:
            logger.error(f"✗ Tenant not found for hotel_id: {data.get('hotel_id')}")
            raise ValidationError("Tenant not found!")

        if data.get("event_type") != "canceled":
            # WARN: Only debug purpose - in production all rooms should exist beforehand
            # room, _ = Room.objects.get_or_create(
            #     tenant=tenant,
            #     number=data.get("room_number"),
            #     defaults={"floor": 1, "block": "A"},
            # )

            room = Room.objects.filter(tenant=tenant, number=data.get("room_number")).first()

            if not room:
                logger.error(f"✗ Room not found: {data.get('room_number')} for tenant: {tenant.title}")
                raise ValidationError("Room not found!")

            data["room"] = room

        data["tenant"] = tenant
        return data


def checkup_guest(data):
    room = data.get("room")
    try:
        guest: Guest = Guest.objects.get(pms_id=data.get("pms_id"))
        # if guest.is_reservation and guest.room == room:
        #     return data
        # if guest and guest.room == room:
        #     raise ValidationError("This guest already exists!")
        if guest and guest.room != room:
            logger.info(f"→ Guest needs to be moved from room {guest.room.number} to {room.number}")
            handle_guest_move(guest, data)
            return None
    except Guest.DoesNotExist:
        pass

    return data


def handle_reservation(data):
    logger.info("Processing handle_reservation")
    validated_data = data
    new_room: Room = validated_data.get("room")

    # Remember old room before update to recalculate its state if guest moves
    old_room: Room | None = None
    try:
        existing = Guest.objects.get(pms_id=data.get("pms_id"))
        if existing.room_id != new_room.id:
            old_room = existing.room
    except Guest.DoesNotExist:
        pass

    try:
        guest, _ = Guest.objects.update_or_create(
            pms_id=data.get("pms_id"),
            defaults={
                "is_active": True,
                "is_reservation": True,
                "lastname": validated_data.get("last_name"),
                "name": validated_data.get("first_name"),
                "check_in": datetime_to_unix(validated_data.get("check_in_date")),
                "check_out": datetime_to_unix(validated_data.get("check_out_date")),
                "auto_check_out": False,
                "room": new_room,
                "reservation_number": new_room.number,
                "birthday": validated_data.get("birthday", None) or None,
                "gender": validated_data.get("gender"),
                "language": validated_data.get("language"),
                "nationality": validated_data.get("nationality"),
                "tenant": validated_data.get("tenant"),
                "pms_id": validated_data.get("pms_id"),
                "additional_info": validated_data.get("additional_info"),
            },
        )
        logger.info(
            f"✓ Guest reserved successfully: {guest.name} {guest.lastname}, room: {guest.room}, pms_id: {validated_data.get('pms_id')}"
        )

        publish_guest_changes(guest, old_room_id=old_room.id if old_room else None)
        new_room.save(update_fields=["state"])

        if old_room:
            logger.info(f"→ Guest moved from room {old_room.number} to {new_room.number}, recalculating old room state")
            old_room.refresh_from_db()
            old_room.save(update_fields=["state"])
    except Exception:
        raise


def handle_checkin(validated_data):
    new_room: Room = validated_data.get("room")

    # Remember old room before update to recalculate its state if guest moves
    old_room: Room | None = None
    try:
        existing = Guest.objects.get(pms_id=validated_data.get("pms_id"))
        if existing.room_id != new_room.id:
            old_room = existing.room
    except Guest.DoesNotExist:
        pass

    try:
        guest, _ = Guest.objects.update_or_create(
            pms_id=validated_data.get("pms_id"),
            defaults={
                "is_active": True,
                "is_reservation": False,
                "lastname": validated_data.get("last_name"),
                "name": validated_data.get("first_name"),
                "check_in": datetime_to_unix(validated_data.get("check_in_date")),
                "check_out": datetime_to_unix(validated_data.get("check_out_date")),
                "auto_check_out": False,
                "room": new_room,
                "birthday": validated_data.get("birthday", None) or None,
                "gender": validated_data.get("gender"),
                "language": validated_data.get("language"),
                "nationality": validated_data.get("nationality"),
                "tenant": validated_data.get("tenant"),
                "pms_id": validated_data.get("pms_id"),
                "additional_info": validated_data.get("additional_info"),
            },
        )
        logger.info(
            f"✓ Guest checked in successfully: {guest.name} {guest.lastname}, room: {guest.room}, pms_id: {validated_data.get('pms_id')}"
        )

        publish_guest_changes(guest, old_room_id=old_room.id if old_room else None)
        new_room.save(update_fields=["state"])

        if old_room:
            logger.info(f"→ Guest moved from room {old_room.number} to {new_room.number}, recalculating old room state")
            old_room.refresh_from_db()
            old_room.save(update_fields=["state"])
    except Exception:
        raise


def handle_checkout(validated_data):
    logger.info("Processing check-out")
    try:
        guest: Guest = Guest.objects.get(pms_id=validated_data.get("pms_id"), is_active=True)
        guest.is_active = False
        guest.save()
        logger.info(
            f"✓ Guest checked out successfully: {guest.name} {guest.lastname}, room: {guest.room.number if guest.room else 'N/A'}, pms_id: {validated_data.get('pms_id')}"
        )
        publish_guest_changes(guest)
        guest.room.save(update_fields=["state"])
        access_cards([guest], guest.room, 0)
    except Guest.DoesNotExist:
        logger.warning(f"⚠ No active guests found with pms_id: {validated_data.get('pms_id')}")
    return {"success": True}


def handle_canceled(data):
    logger.info("Processing handle_canceled")

    try:
        guest: Guest = Guest.objects.get(pms_id=data.get("pms_id"), is_active=True, is_reservation=True)
    except Guest.DoesNotExist:
        logger.warning(f"⚠ No active reservation found for pms_id: {data.get('pms_id')}, skipping cancel")
        return

    room = guest.room
    guest.is_active = False
    guest.is_reservation = False
    guest.save()

    logger.info(
        f"✓ Reservation canceled successfully: {guest.name} {guest.lastname}, room: {room}, pms_id: {data.get('pms_id')}"
    )

    publish_guest_changes(guest)
    room.refresh_from_db()
    room.save(update_fields=["state"])


def handle_guest_move(guest: Guest, data: dict):
    """Move guest from one room to another"""
    old_room: Room = guest.room
    new_room: Room = data.get("room")  # pyright: ignore

    try:
        # Update guest information
        guest.room = new_room
        guest.name = data.get("first_name", guest.name)
        guest.lastname = data.get("last_name", guest.lastname)
        guest.check_in = datetime_to_unix(data.get("check_in_date")) if data.get("check_in_date") else guest.check_in
        guest.check_out = (
            datetime_to_unix(data.get("check_out_date")) if data.get("check_out_date") else guest.check_out
        )

        # Update additional fields if provided
        if data.get("gender"):
            guest.gender = data.get("gender")
        if data.get("language"):
            guest.language = data.get("language")
        if data.get("nationality"):
            guest.nationality = data.get("nationality")
        if data.get("additional_info"):
            guest.additional_info = data.get("additional_info")

        guest.save()

        logger.info(
            f"✓ Guest moved successfully: {guest.name} {guest.lastname} from Room {old_room.number if old_room else 'N/A'} to Room {new_room.number}, pms_id: {guest.pms_id}"  # pyright: ignore
        )

        publish_guest_changes(guest)
        access_cards([guest], old_room, 0)
        access_cards([guest], new_room, 1)
        new_room.save(update_fields=["state"])
        old_room.refresh_from_db()
        old_room.save(update_fields=["state"])
    except Exception as e:
        logger.error(f"✗ Failed to move guest: {str(e)}")
        raise


ROUTES = {
    "checkin": handle_checkin,
    "checkout": handle_checkout,
    "reservation": handle_reservation,
    "canceled": handle_canceled,
}
