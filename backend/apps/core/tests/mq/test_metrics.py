"""Unit tests guarding the MQ Prometheus metric label sets (cardinality)."""

from core.management.mq.mq_metrics import mq_keys_processed_total, mq_messages_processed_total


def test_keys_metric_dropped_high_cardinality_key_label():
    # Only gateway_id — the per-key label was removed to avoid series explosion.
    assert mq_keys_processed_total._labelnames == ("gateway_id",)


def test_messages_metric_labels():
    assert mq_messages_processed_total._labelnames == ("gateway_id", "topic")
