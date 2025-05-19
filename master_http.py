import zmq
import threading
import time
import redis

context = zmq.Context()

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# ZMQ sockets
client_receiver = context.socket(zmq.PULL)
client_receiver.bind("tcp://*:5558")

client_responder = context.socket(zmq.PUSH)
client_responder.bind("tcp://*:5559")

worker_sender = context.socket(zmq.DEALER)
worker_sender.bind("tcp://*:5555")

HEARTBEAT_PORT = 5557
WORKER_TIMEOUT = 10  # seconds

worker_last_seen = {}

def log_master_event(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    # Push to Redis log list and keep only last 100 logs
    redis_client.lpush("master_logs", log_entry)
    redis_client.ltrim("master_logs", 0, 99)

def monitor_heartbeats():
    context = zmq.Context()
    hb_socket = context.socket(zmq.PULL)
    hb_socket.bind(f"tcp://*:{HEARTBEAT_PORT}")

    while True:
        try:
            heartbeat = hb_socket.recv_json(flags=zmq.NOBLOCK)
            worker_id = heartbeat["worker_id"]
            worker_last_seen[worker_id] = time.time()
            redis_client.hset("workers_status", worker_id, worker_last_seen[worker_id])
            log_master_event(f"Received heartbeat from {worker_id}")
        except zmq.Again:
            pass

        # Cleanup dead workers
        now = time.time()
        dead_workers = [w for w, last in worker_last_seen.items() if now - last > WORKER_TIMEOUT]
        for dead in dead_workers:
            log_master_event(f"Worker {dead} timed out")
            del worker_last_seen[dead]
            redis_client.hdel("workers_status", dead)

        time.sleep(1)

def receive_client_requests():
    while True:
        request_data = client_receiver.recv_json()
        log_master_event(f"Received task from client: {request_data.get('task')} (ID: {request_data.get('task_id')})")
        worker_sender.send_json(request_data)

def receive_worker_results():
    while True:
        result = worker_sender.recv_json()
        log_master_event(f"Worker result received for task {result.get('task_id')} (Task: {result.get('task')})")
        client_responder.send_json(result)
        # Flush or small delay for push socket if needed
        if hasattr(client_responder, 'flush'):
            client_responder.flush()
        else:
            time.sleep(0.1)


threading.Thread(target=monitor_heartbeats, daemon=True).start()
threading.Thread(target=receive_client_requests, daemon=True).start()
threading.Thread(target=receive_worker_results, daemon=True).start()

log_master_event("Master Node is running...")

while True:
    time.sleep(5)

