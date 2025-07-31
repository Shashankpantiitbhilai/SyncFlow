"""
Kafka topics configuration.
"""


class KafkaTopics:
    """Kafka topics used in the system."""
    
    # Topic for inbound sync (Stripe → Our System)
    SYNC_INBOUND = "sync.inbound"
    
    # Topic for outbound sync (Our System → Stripe)
    SYNC_OUTBOUND = "sync.outbound"
