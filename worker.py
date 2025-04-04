import zmq
import cv2
import numpy as np
import threading
import time
import random
import sys

context = zmq.Context()

# PULL socket to receive tasks
task_receiver = context.socket(zmq.PULL)
task_receiver.connect("tcp://localhost:5555")

# PUSH socket to send processed images
result_sender = context.socket(zmq.PUSH)
result_sender.connect("tcp://localhost:5556")

# PUSH socket for sending heartbeat signals
heartbeat_sender = context.socket(zmq.PUSH)
heartbeat_sender.connect("tcp://localhost:5557")

worker_id = f"Worker-{random.randint(1000, 9999)}"

# Function to send heartbeat
def send_heartbeat():
    while True:
        heartbeat_sender.send_string(worker_id)
        time.sleep(3)

# Start heartbeat thread
threading.Thread(target=send_heartbeat, daemon=True).start()

# Process tasks
while True:
    try:
        task_data = task_receiver.recv_json(flags=zmq.NOBLOCK)
        task_type = task_data["task"]
        # Decode the base64-encoded image string to bytes
        image_bytes = base64.b64decode(task_data["image"])

        # Convert bytes to numpy array
        img_data = np.frombuffer(image_bytes, dtype=np.uint8)

        # Decode image to OpenCV format
        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        
        img_data = np.frombuffer(task_data["image"], dtype=np.uint8)

        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if task_type == "grayscale":
            processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif task_type == "edge":
            processed_img = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 50, 150)

        _, img_encoded = cv2.imencode('.jpg', processed_img)

        result_sender.send_json({
            "task": task_type,
            "image": img_encoded.tobytes(),
        })

        # Simulate worker failure (20% chance)
        if random.random() < 0.2:
            print(f"{worker_id} failed!")
            sys.exit(1)

    except zmq.Again:
        pass

    time.sleep(1)
