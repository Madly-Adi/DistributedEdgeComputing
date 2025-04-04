import requests

url = "http://localhost:5000/process_image"
files = {"image": open("input.jpg", "rb")}
data = {"task": "grayscale"}

response = requests.post(url, files=files, data=data)
print(response.json())  # Check the response

