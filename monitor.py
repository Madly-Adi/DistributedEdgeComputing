from flask import Flask, jsonify, render_template_string
import redis
import time

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# HTML template for monitoring page
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Distributed System Monitor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .offline { color: red; font-weight: bold; }
        .online { color: green; font-weight: bold; }
        #refresh-btn { padding: 8px 12px; cursor: pointer; }
    </style>
    <script>
        async function fetchData() {
            const workersRes = await fetch('/api/workers');
            const logsRes = await fetch('/api/logs');
            const workers = await workersRes.json();
            const logs = await logsRes.json();

            // Update workers table
            const workersTableBody = document.getElementById('workers-body');
            workersTableBody.innerHTML = '';
            const now = Date.now() / 1000;

            for (const w of workers) {
                const row = document.createElement('tr');
                const status = (now - w.timestamp) < 10 ? 'Online' : 'Offline';
                row.innerHTML = `
                    <td>${w.worker_id}</td>
                    <td>${new Date(w.timestamp * 1000).toLocaleString()}</td>
                    <td class="${status.toLowerCase()}">${status}</td>
                `;
                workersTableBody.appendChild(row);
            }

            // Update logs
            const logsContainer = document.getElementById('logs');
            logsContainer.innerHTML = logs.map(l => `<div>${l}</div>`).join('');
        }

        function startAutoRefresh() {
            fetchData();
            setInterval(fetchData, 5000);
        }

        window.onload = startAutoRefresh;
    </script>
</head>
<body>
    <h2>Worker Status</h2>
    <table>
        <thead>
            <tr><th>Worker ID</th><th>Last Heartbeat</th><th>Status</th></tr>
        </thead>
        <tbody id="workers-body">
            <!-- Filled by JS -->
        </tbody>
    </table>

    <h2>Master Logs</h2>
    <div id="logs" style="height: 300px; overflow-y: scroll; background: #eee; padding: 10px; border-radius: 5px;"></div>

    <button id="refresh-btn" onclick="fetchData()">Refresh Now</button>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/workers')
def api_workers():
    workers_data = redis_client.hgetall("workers_status")
    now = time.time()
    workers = []
    for k, v in workers_data.items():
        workers.append({"worker_id": k.decode('utf-8'), "timestamp": float(v)})
    return jsonify(workers)

@app.route('/api/logs')
def api_logs():
    logs = redis_client.lrange("master_logs", 0, 99)
    logs = [log.decode('utf-8') for log in logs]
    return jsonify(logs)

if __name__ == "__main__":
    app.run(port=6060, debug=True)

