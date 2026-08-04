"""Unit tests guarding the MQ Prometheus metric label sets (cardinality)."""

from core.management.mq.mq_metrics import mq_keys_processed_total, mq_messages_processed_total


def test_keys_metric_has_no_labels():
    # Метка gateway_id убрана (взрыв кардинальности); счётчик агрегируется по батчу.
    assert mq_keys_processed_total._labelnames == ()


def test_messages_metric_labels():
    # Осталась только topic (ограниченный набор); gateway_id убран во избежание
    # серии на каждое устройство.
    assert mq_messages_processed_total._labelnames == ("topic",)
