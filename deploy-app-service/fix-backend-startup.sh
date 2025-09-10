#!/bin/bash

# Fix backend startup by creating a proper startup script

set -e

echo "🔧 Creating backend startup script deployment"
echo "============================================"

BACKEND_APP_NAME="digitaltwin"
RESOURCE_GROUP="DigitalTwin"

# Create startup script
cat > startup.sh << 'EOF'
#!/bin/bash
set -e
echo "🚀 Starting backend application..."
echo "📦 Installing dependencies..."
cd /home/site/wwwroot
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "✅ Dependencies installed successfully"
echo "🔥 Starting FastAPI with uvicorn..."
python -m uvicorn AgentUI.Backend.api:app --host 0.0.0.0 --port 8000
EOF

# Deploy startup script
echo "📤 Deploying startup script..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $BACKEND_APP_NAME \
    --src-path startup.sh \
    --target-path startup.sh \
    --type static

# Update startup command to use the script
echo "⚙️ Updating startup command..."
az webapp config set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "bash startup.sh"

echo "✅ Backend startup fix complete!"
echo "📍 The app should restart automatically"
echo "⏳ Wait 3-5 minutes for dependency installation"

