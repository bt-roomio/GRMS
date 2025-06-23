import json
from unittest import TestCase
from unittest.mock import patch, MagicMock

from apps.core.management.process_messages import process_messages

class TestProcessMessages(TestCase):
    @patch('apps.core.management.process_messages.redis_client')
    @patch('apps.core.management.process_messages.Device.objects.filter')
    def test_process_messages_with_cache(self, mock_filter, mock_redis):
        # Mock Redis to return cached device
        mock_redis.get.return_value = json.dumps({"id": 1, "name": "Test Device"}).encode('utf-8')

        # Mock database filter to ensure it's not called
        mock_filter.return_value.first.assert_not_called()

        # Simulate message processing
        body = json.dumps({"sourceDeviceUUID": 1})
        process_messages(None, body)

        # Validate Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_not_called()

    @patch('apps.core.management.process_messages.redis_client')
    @patch('apps.core.management.process_messages.Device.objects.filter')
    def test_process_messages_without_cache(self, mock_filter, mock_redis):
        # Mock Redis to return None for cache
        mock_redis.get.return_value = None

        # Mock database filter to return a device
        mock_device = MagicMock()
        mock_device.id = 1
        mock_device.name = "Test Device"
        mock_filter.return_value.first.return_value = mock_device

        # Simulate message processing
        body = json.dumps({"sourceDeviceUUID": 1})
        process_messages(None, body)

        # Validate Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once_with(
            'prodevice_cache:1',
            json.dumps({"id": mock_device.id, "name": mock_device.name})
        )

        # Validate DB interactions
        mock_filter.return_value.first.assert_called_once()

    @patch('apps.core.management.process_messages.redis_client')
    @patch('apps.core.management.process_messages.Device.objects.filter')
    def test_process_messages_device_not_found(self, mock_filter, mock_redis):
        # Mock Redis and DB to return None
        mock_redis.get.return_value = None
        mock_filter.return_value.first.return_value = None

        # Simulate message processing
        body = json.dumps({"sourceDeviceUUID": 1})
        process_messages(None, body)

        # Validate Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_not_called()

        # Validate DB interactions
        mock_filter.return_value.first.assert_called_once()

