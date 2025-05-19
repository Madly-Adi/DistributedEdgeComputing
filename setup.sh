#!/bin/bash

echo "🚀 Setting up your Distributed Image Processing environment..."

# 1. Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# 2. Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install flask pyzmq opencv-python redis numpy torch torchvision torchgeo   


# 5. Install Redis server
echo "🧠 Installing Redis server..."
sudo apt update
sudo apt install -y redis-server

# 6. Enable and start Redis server
echo "⚙️ Enabling Redis service..."
sudo systemctl enable redis
sudo systemctl start redis

# 7. Confirm Redis is running
echo "✅ Checking Redis status..."
sudo systemctl status redis | grep Active

echo ""
echo "🎉 Setup complete!"
echo "👉 To activate your virtual environment, run:"
echo "   source venv/bin/activate"

