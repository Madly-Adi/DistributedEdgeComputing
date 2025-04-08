from flask import Flask, request, jsonify,render_template_string
import zmq
import cv2
import numpy as np
import base64
import threading
import time
from threading import Event
import uuid




app = Flask(__name__)
context = zmq.Context()

# PUSH socket to send tasks
client_sender = context.socket(zmq.PUSH)
client_sender.connect("tcp://localhost:5558")

# PULL socket to receive responses asynchronously
client_receiver = context.socket(zmq.PULL)
client_receiver.connect("tcp://localhost:5559")

responses = {}  # task_id: response
response_events = {}  # task_id: Event


# HTML template
HTML_TEMPLATE = '''
<!doctype html>
<title>Image Processor</title>
<h2>Upload Image for Processing</h2>
<form method=post enctype=multipart/form-data action="/process_image">
  <input type=file name=image required>
  <select name="task">
    <option value="grayscale">Grayscale</option>
    <option value="edge">Edge Detection</option>
  </select>
  <input type=submit value="Process Image">
</form>

{% if processed_image %}
  <h3>Result ({{ task }})</h3>
  <img src="data:image/jpeg;base64,{{ processed_image }}" alt="Processed Image">
{% endif %}
'''


def receive_responses():
    """Continuously receive results from the master."""
    while True:
        try:
            response = client_receiver.recv_json()
            print(f"[CLIENT] Received response: {response}")
            task_id = response["task_id"]
            responses[task_id] = response
            if task_id in response_events:
                response_events[task_id].set()
        except Exception as e:
            print(f"[CLIENT] Error receiving response: {e}")



threading.Thread(target=receive_responses, daemon=True).start()

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

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
    task_id = str(uuid.uuid4())

    # Send request to Master
    request_data = {"task_id": task_id, "task": task_type, "image": img_base64}
    client_sender.send_json(request_data)

    # Create an event to wait for this task's response
    response_events[task_id] = Event()

    # Wait up to 15 seconds for the result
    if not response_events[task_id].wait(timeout=5):
        # Cleanup to avoid memory leaks or stale state
        response_events.pop(task_id, None)
        responses.pop(task_id, None)
        return jsonify({"error": "Timeout waiting for response from worker."}), 504


    response = responses.pop(task_id)
    response_events.pop(task_id)


    # Convert Base64 back to an image
    processed_img = np.frombuffer(base64.b64decode(response["image"]), dtype=np.uint8)
    processed_img = cv2.imdecode(processed_img, cv2.IMREAD_GRAYSCALE)

    # Encode processed image in Base64 for HTTP response
    _, buffer = cv2.imencode('.jpg', processed_img)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    return render_template_string(HTML_TEMPLATE, processed_image=encoded_image, task=task_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

