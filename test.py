import requests
import numpy as np
import cv2
import base64

url = "http://localhost:5000/process_image"
files = {"image": open("input.jpg", "rb")}
data = {"task": "edge"}

response = requests.post(url, files=files, data=data)

data = response.json()  # Extract JSON from the response
image_data = data["image"] 

# Convert Base64 string back to bytes
img_data = base64.b64decode(image_data)

# Convert bytes to a NumPy array
img_array = np.frombuffer(img_data, dtype=np.uint8)

# Decode the image using OpenCV
processed_img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

# Display the image (Optional)
cv2.imshow("Processed Image", processed_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
