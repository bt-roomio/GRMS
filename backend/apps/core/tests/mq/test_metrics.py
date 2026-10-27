"""Unit tests guarding the MQ Prometheus metric label sets (cardinality)."""

from core.management.mq.mq_metrics import mq_keys_processed_total, mq_messages_processed_total


def test_keys_metric_has_no_labels():
    # The gateway_id label was removed (cardinality blow-up); the counter is aggregated per batch.
    assert mq_keys_processed_total._labelnames == ()


def test_messages_metric_labels():
    # Only topic remains (a bounded set); gateway_id was removed to avoid
    # a series per device.
    assert mq_messages_processed_total._labelnames == ("topic",)
