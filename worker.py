import zmq
import cv2
import numpy as np
import base64
import random
import threading
import time

context = zmq.Context()

worker_socket = context.socket(zmq.DEALER)  # Use DEALER instead of REP
worker_socket.setsockopt_string(zmq.IDENTITY, str(random.randrange(100,999)))  # Unique worker ID
worker_socket.connect("tcp://localhost:5555")

print("Worker Node is ready...")

HEARTBEAT_INTERVAL = 2  # seconds

def send_heartbeat():
    hb_socket = context.socket(zmq.PUSH)
    hb_socket.connect("tcp://localhost:5557")  # Master listens here
    while True:
        hb_socket.send_json({"worker_id": worker_socket.getsockopt_string(zmq.IDENTITY), "timestamp": time.time()})
        time.sleep(HEARTBEAT_INTERVAL)
 
threading.Thread(target=send_heartbeat, daemon=True).start()

while True:
    try:
        request_data = worker_socket.recv_json()
        print(f"Received task: {request_data}")

        # Decode the image
        img_data = np.frombuffer(base64.b64decode(request_data["image"]), dtype=np.uint8)
        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        # Handle possible decoding failures
        if image is None:
            print("[Worker] Error: Image decoding failed!")
            worker_socket.send_json({"error": "Image decoding failed"})
            continue

        # Perform task
        if request_data["task"] == "grayscale":
            processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif request_data["task"] == "edge":
            processed_img = cv2.Canny(image, 100, 200)
        else:
            processed_img = image

        # Encode processed image
        _, buffer = cv2.imencode('.jpg', processed_img)
        encoded_image = base64.b64encode(buffer).decode('utf-8')

        # Send result back
        worker_socket.send_json({"task": request_data["task"], "image": encoded_image})
    
    except Exception as e:
        print(f"[Worker] Error: {e}")

