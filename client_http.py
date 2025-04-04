from flask import Flask, request, jsonify
import zmq
import cv2
import numpy as np
import base64
import threading

app = Flask(__name__)
context = zmq.Context()

# PUSH socket to send tasks
client_sender = context.socket(zmq.PUSH)
client_sender.connect("tcp://localhost:5558")

# PULL socket to receive responses asynchronously
client_receiver = context.socket(zmq.PULL)
client_receiver.connect("tcp://localhost:5559")

responses = {}  # Dictionary to store results

def receive_responses():
    """Continuously receive results from the master."""
    while True:
        response = client_receiver.recv_json()
        task_id = response["task_id"]
        responses[task_id] = response

threading.Thread(target=receive_responses, daemon=True).start()

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files or 'task' not in request.form:
        return jsonify({"error": "Missing image or task type"}), 400

    task_type = request.form['task']
    image_file = request.files['image']

    # Read and encode image
    image = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
    _, img_encoded = cv2.imencode('.jpg', image)

    # Convert image bytes to Base64
    img_base64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')

    # Generate task ID
    task_id = str(hash(img_base64))  # Simple unique identifier

    # Send request to Master
    request_data = {"task_id": task_id, "task": task_type, "image": img_base64}
    client_sender.send_json(request_data)

    # Wait for response
    while task_id not in responses:
        pass  # Wait for the response to be received

    response = responses.pop(task_id)

    # Convert Base64 back to an image
    processed_img = np.frombuffer(base64.b64decode(response["image"]), dtype=np.uint8)
    processed_img = cv2.imdecode(processed_img, cv2.IMREAD_GRAYSCALE)

    # Encode processed image in Base64 for HTTP response
    _, buffer = cv2.imencode('.jpg', processed_img)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    return jsonify({"task": response["task"], "image": encoded_image})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

