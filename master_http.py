import zmq
import threading
import time

context = zmq.Context()

# PULL socket to receive client requests
client_receiver = context.socket(zmq.PULL)
client_receiver.bind("tcp://*:5558")

# PUSH socket to send results back to clients
client_responder = context.socket(zmq.PUSH)
client_responder.bind("tcp://*:5559")

# DEALER socket to forward tasks to workers
worker_sender = context.socket(zmq.DEALER)
worker_sender.bind("tcp://*:5555")

HEARTBEAT_PORT = 5557
WORKER_TIMEOUT = 10  # seconds

worker_last_seen = {}

def monitor_heartbeats():
    context = zmq.Context()
    hb_socket = context.socket(zmq.PULL)
    hb_socket.bind(f"tcp://*:{HEARTBEAT_PORT}")

    while True:
        try:
            heartbeat = hb_socket.recv_json(flags=zmq.NOBLOCK)
            worker_id = heartbeat["worker_id"]
            worker_last_seen[worker_id] = time.time()
            print(f"[HB] Received heartbeat from {worker_id}")
        except zmq.Again:
            pass

        # Cleanup dead workers
        now = time.time()
        dead_workers = [w for w, last in worker_last_seen.items() if now - last > WORKER_TIMEOUT]
        for dead in dead_workers:
            print(f"[HB] Worker {dead} timed out")
            del worker_last_seen[dead]

        time.sleep(1)

def receive_client_requests():
    """Receive tasks from clients and forward them to workers."""
    while True:
        request_data = client_receiver.recv_json()
        print(f"Received task from client: {request_data}")
        worker_sender.send_json(request_data)

def receive_worker_results():
    """Receive results from workers and send them back to clients."""
    while True:
        result = worker_sender.recv_json()
        print(f"Worker result: {result}")
        client_responder.send_json(result)  # Send result to client
        client_responder.flush() if hasattr(client_responder, 'flush') else time.sleep(0.1)


threading.Thread(target=monitor_heartbeats, daemon=True).start()
threading.Thread(target=receive_client_requests, daemon=True).start()
threading.Thread(target=receive_worker_results, daemon=True).start()

print("Master Node is running...")

while True:
    time.sleep(5)

