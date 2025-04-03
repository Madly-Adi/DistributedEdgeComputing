import zmq
import threading
import time

context = zmq.Context()

# REP socket to handle REST API requests
api_receiver = context.socket(zmq.REP)
api_receiver.bind("tcp://*:5558")

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

# Function to handle API requests
def handle_api_requests():
    while True:
        request_data = api_receiver.recv_json()
        pending_tasks[request_data["image"]] = api_receiver  # Track client

        # Forward task to a worker
        task_sender.send_json(request_data)
        print("Task forwarded to worker \n")

# Function to send results back to API clients
def send_results():
    while True:
        result = result_receiver.recv_json()
        
        if result["image"] in pending_tasks:
            client_socket = pending_tasks.pop(result["image"])
            client_socket.send_json(result)  # Send response back to REST API


# Start API request handler and result sender in threads
threading.Thread(target=handle_api_requests, daemon=True).start()
threading.Thread(target=send_results, daemon=True).start()
