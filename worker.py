import zmq
import cv2
import numpy as np
import base64
import random
import threading
import time

context = zmq.Context()

# DEALER socket to talk to the Master
worker_socket = context.socket(zmq.DEALER)
worker_id = f"worker-{random.randint(100, 999)}"
worker_socket.setsockopt_string(zmq.IDENTITY, worker_id)
worker_socket.connect("tcp://localhost:5555")

print(f"[{worker_id}] Worker Node is ready...")

# Heartbeat settings
HEARTBEAT_INTERVAL = 2  # seconds

def send_heartbeat():
    hb_context = zmq.Context()
    hb_socket = hb_context.socket(zmq.PUSH)
    hb_socket.connect("tcp://localhost:5557")  # Master listens here

    while True:
        hb_socket.send_json({"worker_id": worker_id, "timestamp": time.time()})
        time.sleep(HEARTBEAT_INTERVAL)

# Start heartbeat thread
threading.Thread(target=send_heartbeat, daemon=True).start()

while True:
    print(f"[{worker_id}] Waiting for task...")
    request_data = worker_socket.recv_json()
    print(f"[{worker_id}] Received task: {request_data}")

    # Decode the image
    img_data = np.frombuffer(base64.b64decode(request_data["image"]), dtype=np.uint8)
    image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

    # Perform task
    if request_data["task"] == "grayscale":
        processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif request_data["task"] == "edge":
        processed_img = cv2.Canny(image, 100, 200)
    else:
        processed_img = image  # Default to original image if task is unknown

    # Encode processed image
    _, buffer = cv2.imencode('.jpg', processed_img)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    # Send result back to master
    response = {"task_id": request_data["task_id"],"task": request_data["task"], "image": encoded_image}
    worker_socket.send_json(response)

