try:
    # Your existing master node code
    import zmq
    import threading

    context = zmq.Context()
    
    api_receiver = context.socket(zmq.REP)
    api_receiver.bind("tcp://*:5558")

    task_sender = context.socket(zmq.PUSH)
    task_sender.bind("tcp://*:5555")

    result_receiver = context.socket(zmq.PULL)
    result_receiver.bind("tcp://*:5556")

    pending_tasks = {}

    def handle_api_requests():
        while True:
            print("Waiting for API request...")
            request_data = api_receiver.recv_json()
            print(f"Received task: {request_data}")
            pending_tasks[request_data["image"]] = api_receiver
            task_sender.send_json(request_data)

    def send_results():
        while True:
            print("Waiting for worker results...")
            result = result_receiver.recv_json()
            print(f"Worker result: {result}")

            if result["image"] in pending_tasks:
                client_socket = pending_tasks.pop(result["image"])
                client_socket.send_json(result)

    threading.Thread(target=handle_api_requests, daemon=False).start()
    threading.Thread(target=send_results, daemon=False).start()

    # Keep script alive
    while True:
        print("Master Node is running...")
        time.sleep(5)

except Exception as e:
    print(f"Error in Master Node: {e}")

