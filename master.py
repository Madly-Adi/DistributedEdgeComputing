import zmq
import threading
import time

context = zmq.Context()

# ROUTER socket to receive requests from multiple clients
client_receiver = context.socket(zmq.ROUTER)
client_receiver.bind("tcp://*:5558")

# PUSH socket to send tasks to workers
task_sender = context.socket(zmq.PUSH)
task_sender.bind("tcp://*:5555")

# PULL socket to receive processed images
result_receiver = context.socket(zmq.PULL)
result_receiver.bind("tcp://*:5556")

# PULL socket to receive worker heartbeats
heartbeat_receiver = context.socket(zmq.PULL)
heartbeat_receiver.bind("tcp://*:5557")

pending_tasks = {}  # Store tasks mapped to clients
active_workers = {}  # Store active workers

# Function to monitor worker heartbeats
def monitor_workers():
    while True:
        try:
            worker_id = heartbeat_receiver.recv_string(flags=zmq.NOBLOCK)
            active_workers[worker_id] = time.time()
        except zmq.Again:
            pass

        # Remove unresponsive workers (5s timeout)
        for worker in list(active_workers.keys()):
            if time.time() - active_workers[worker] > 5:
                print(f"Worker {worker} failed!")
                del active_workers[worker]

        time.sleep(2)

# Start heartbeat monitoring in a separate thread
threading.Thread(target=monitor_workers, daemon=True).start()

# Function to handle client requests
def handle_clients():
    while True:
        client_id, request = client_receiver.recv_multipart()
        task_data = request.decode()
        
        # Store request for tracking
        pending_tasks[client_id] = task_data
        
        # Forward task to a worker
        task_sender.send_json(task_data)

# Function to receive results and send back to clients
def send_results():
    while True:
        result = result_receiver.recv_json()
        
        # Find the corresponding client
        client_id = next((c for c, t in pending_tasks.items() if t == result), None)
        if client_id:
            client_receiver.send_multipart([client_id, result.encode()])
            del pending_tasks[client_id]

# Start client handler and result sender in separate threads
threading.Thread(target=handle_clients, daemon=True).start()
threading.Thread(target=send_results, daemon=True).start()
