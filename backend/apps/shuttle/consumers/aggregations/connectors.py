import random


def make_connectors():
    connectors = []
    for i in range(100):
        controller = {
            "name": random.choice(["Deluxe QUEEN", "Roomio", "Gateway roomio"]),
            "mac_address": random.choice(["Doesn't exist", "10.22.50.156"]),
            "ip_address": f"10.22.50.{i}",
            "room": random.choice([i for i in range(100, 400, 10)]),
            "address_map": random.choice(["Open map", "Not connected"]),
            "status": random.choice(["Oneline", "Offline", "Processing"]),
            "file_name": "Doesn't exist",
        }
        connectors.append(controller)

    return connectors
