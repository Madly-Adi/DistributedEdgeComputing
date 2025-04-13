from flask import Flask, request, jsonify, render_template_string
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

# PUSH socket to send tasks to master
client_sender = context.socket(zmq.PUSH)
client_sender.connect("tcp://localhost:5558")

# PULL socket to receive processed results from master
client_receiver = context.socket(zmq.PULL)
client_receiver.connect("tcp://localhost:5559")

responses = {}         # task_id: result
response_events = {}   # task_id: threading.Event for async waiting

# 🔧 Enhanced HTML with CSS
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Distributed Image Processor</title>
    <style>
        body {
            background: #f4f4f4;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            width: 400px;
            text-align: center;
        }
        h2 {
            margin-bottom: 25px;
            color: #343a40;
        }
        input[type="file"],
        select,
        input[type="submit"] {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 16px;
        }
        input[type="submit"] {
            background: #007bff;
            color: white;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background: #0056b3;
        }
        img {
            margin-top: 20px;
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Upload Image for Processing</h2>
        <form method="post" enctype="multipart/form-data" action="/process_image">
            <input type="file" name="image" required>
            <select name="task" required>
                <option value="">-- Select Task --</option>
                <option value="grayscale">Grayscale</option>
                <option value="edge">Edge Detection</option>
            </select>
            <input type="submit" value="Process Image">
        </form>

        {% if processed_image %}
            <h3>Result ({{ task }})</h3>
            <img src="data:image/jpeg;base64,{{ processed_image }}" alt="Processed Image">
        {% endif %}
    </div>
</body>
</html>
'''

# 🎧 Background thread to receive results from master
def receive_responses():
    while True:
        try:
            response = client_receiver.recv_json()
            task_id = response["task_id"]
            responses[task_id] = response
            if task_id in response_events:
                response_events[task_id].set()
        except Exception as e:
            print(f"[CLIENT] Error receiving response: {e}")

# Start response listener thread
threading.Thread(target=receive_responses, daemon=True).start()

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files or 'task' not in request.form:
        return jsonify({"error": "Missing image or task type"}), 400

    task_type = request.form['task']
    image_file = request.files['image']
    image = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
    _, img_encoded = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')

    task_id = str(uuid.uuid4())
    request_data = {"task_id": task_id, "task": task_type, "image": img_base64}
    client_sender.send_json(request_data)

    response_events[task_id] = Event()

    if not response_events[task_id].wait(timeout=10):
        response_events.pop(task_id, None)
        responses.pop(task_id, None)
        return jsonify({"error": "Timeout waiting for response from worker."}), 504

    response = responses.pop(task_id)
    response_events.pop(task_id)

    processed_img = np.frombuffer(base64.b64decode(response["image"]), dtype=np.uint8)
    processed_img = cv2.imdecode(processed_img, cv2.IMREAD_GRAYSCALE)
    _, buffer = cv2.imencode('.jpg', processed_img)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    return render_template_string(HTML_TEMPLATE, processed_image=encoded_image, task=task_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

