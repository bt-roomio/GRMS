from prometheus_client import Counter

mq_messages_processed_total = Counter(
    "mq_messages_processed_total",
    "Total MQ messages processed per gateway",
    ["gateway_id", "topic"],
)

mq_keys_processed_total = Counter(
    "mq_keys_processed_total",
    "Total MQ data keys processed per gateway",
    ["gateway_id"],
)
