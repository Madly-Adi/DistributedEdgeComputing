import zmq
import threading
import time

context = zmq.Context()

# ROUTER for Clients
client_receiver = context.socket(zmq.ROUTER)
client_receiver.bind("tcp://*:5558")

# DEALER for Workers
worker_sender = context.socket(zmq.DEALER)
worker_sender.bind("tcp://*:5555")

# Heartbeat socket
heartbeat_socket = context.socket(zmq.PULL)
heartbeat_socket.bind("tcp://*:5557")

HEARTBEAT_INTERVAL = 1
WORKER_TIMEOUT = 5  # seconds
worker_last_seen = {}

def monitor_heartbeats():
    while True:
        try:
            heartbeat = heartbeat_socket.recv_json(flags=zmq.NOBLOCK)
            worker_id = heartbeat["worker_id"]
            worker_last_seen[worker_id] = time.time()
            print(f"[HB] Worker {worker_id} is alive")
        except zmq.Again:
            pass

        # Remove timed-out workers
        now = time.time()
        for worker_id, last_seen in list(worker_last_seen.items()):
            if now - last_seen > WORKER_TIMEOUT:
                print(f"[HB] Worker {worker_id} timed out")
                del worker_last_seen[worker_id]

        time.sleep(HEARTBEAT_INTERVAL)

# Use a built-in ZMQ queue proxy to forward messages
threading.Thread(target=monitor_heartbeats, daemon=True).start()
threading.Thread(target=lambda: zmq.proxy(client_receiver, worker_sender), daemon=True).start()

print("Master Node is running...")
while True:
    time.sleep(5)

