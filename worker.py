import zmq
import cv2
import numpy as np
import base64
import random
import threading
import time
import torch
import torchvision.transforms as T
from torchvision.models.segmentation import deeplabv3_resnet50


# ---------- Model Setup ----------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Use standard DeepLabV3 with more visible classes
lulc_model = deeplabv3_resnet50(pretrained=True).to(device).eval()

# Pascal VOC colors (more visible than LULC)
VOC_COLORS = np.array([
    [0, 0, 0],       # Background
    [128, 0, 0],     # Aeroplane
    [0, 128, 0],     # Bicycle
    [128, 128, 0],   # Bird
    [0, 0, 128],     # Boat
    [128, 0, 128],   # Bottle
    [0, 128, 128],   # Bus
    [128, 128, 128], # Car
    [64, 0, 0],      # Cat
    [192, 0, 0],     # Chair
    [64, 128, 0],    # Cow
    [192, 128, 0],   # Dining table
    [64, 0, 128],    # Dog
    [192, 0, 128],   # Horse
    [64, 128, 128],  # Motorbike
    [192, 128, 128], # Person
    [0, 64, 0],      # Potted plant
    [128, 64, 0],    # Sheep
    [0, 192, 0],     # Sofa
    [128, 192, 0],   # Train
    [0, 64, 128]     # TV/Monitor
], dtype=np.uint8)

def run_lulc_segmentation(image):
    original_size = image.shape[:2]
    
    # Preprocessing
    transform = T.Compose([
        T.ToPILImage(),
        T.Resize(512),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406],
                   std=[0.229, 0.224, 0.225])
    ])
    
    input_tensor = transform(image).unsqueeze(0).to(device)

    # Prediction
    with torch.no_grad():
        output = lulc_model(input_tensor)['out']
        pred = torch.argmax(output, dim=1).squeeze().cpu().numpy()

    # Create highly visible mask
    mask = np.zeros((*pred.shape, 3), dtype=np.uint8)
    for class_id in range(len(VOC_COLORS)):
        mask[pred == class_id] = VOC_COLORS[class_id]
    
    # Make colors more vibrant
    mask = cv2.convertScaleAbs(mask, alpha=1.5, beta=50)
    
    # Resize to original dimensions
    mask = cv2.resize(mask, (original_size[1], original_size[0]),
                     interpolation=cv2.INTER_NEAREST)
    
    # Create high-contrast overlay
    overlay = cv2.addWeighted(image, 0.4, mask, 0.8, 0)
    
    # Draw contours for better visibility
    for class_id in np.unique(pred):
        if class_id > 0:  # Skip background
            class_mask = (pred == class_id).astype(np.uint8)
            contours, _ = cv2.findContours(
                cv2.resize(class_mask, (original_size[1], original_size[0])),
                cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(overlay, contours, -1, (255, 255, 255), 2)
    unique_classes = np.unique(pred)
        
    print("Detected classes:", unique_classes)
    if len(unique_classes) == 1:
        print("Warning: Only background detected - try different images")
    
    return overlay

# ---------- ZMQ Setup ----------
context = zmq.Context()
worker_socket = context.socket(zmq.DEALER)
worker_id = f"worker-{random.randint(100, 999)}"
worker_socket.setsockopt_string(zmq.IDENTITY, worker_id)
worker_socket.connect("tcp://localhost:5555")
print(f"[{worker_id}] Worker Node is ready...")

# ---------- Heartbeat ----------
HEARTBEAT_INTERVAL = 2

def send_heartbeat():
    hb_context = zmq.Context()
    hb_socket = hb_context.socket(zmq.PUSH)
    hb_socket.connect("tcp://localhost:5557")
    while True:
        hb_socket.send_json({"worker_id": worker_id, "timestamp": time.time()})
        time.sleep(HEARTBEAT_INTERVAL)

threading.Thread(target=send_heartbeat, daemon=True).start()

# ---------- Optional K-means Segmentation ----------
def segment_image(image, k=3):
    lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    pixel_values = lab_image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.uint8(centers)
    segmented_data = centers[labels.flatten()]
    return segmented_data.reshape(image.shape)

# ---------- Task Loop ----------
while True:
    print(f"[{worker_id}] Waiting for task...")
    request_data = worker_socket.recv_json()
    print(f"[{worker_id}] Received task: {request_data}")

    img_data = np.frombuffer(base64.b64decode(request_data["image"]), dtype=np.uint8)
    image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

    if request_data["task"] == "grayscale":
        processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif request_data["task"] == "edge":
        processed_img = cv2.Canny(image, 100, 200)
    elif request_data["task"] == "segmentation":
        processed_img = segment_image(image, k=3)
    elif request_data["task"] == "lulc":
        processed_img = run_lulc_segmentation(image)
    else:
        processed_img = image  # fallback

    _, buffer = cv2.imencode('.jpg', processed_img)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    response = {
        "task_id": request_data["task_id"],
        "task": request_data["task"],
        "image": encoded_image
    }
    print(f"[{worker_id}] Sending response...")
    worker_socket.send_json(response)

