import zmq
import cv2
import numpy as np

context = zmq.Context()
client_socket = context.socket(zmq.REQ)
client_socket.connect("tcp://localhost:5558")  # Connect to Master Node

def send_request(image_path, task_type):
    """Send an image processing request."""
    image = cv2.imread(image_path)
    _, img_encoded = cv2.imencode('.jpg', image)
    
    request_data = {
        "task": task_type,  # "grayscale" or "edge"
        "image": img_encoded.tobytes(),
    }

    client_socket.send_json(request_data)
    response = client_socket.recv_json()  # Receive processed image

    # Decode and display processed image
    processed_img = np.frombuffer(response["image"], dtype=np.uint8)
    processed_img = cv2.imdecode(processed_img, cv2.IMREAD_GRAYSCALE)

    cv2.imshow(f"Processed Image - {response['task']}", processed_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Example usage
send_request("input.jpg", "grayscale")
send_request("input.jpg", "edge")
