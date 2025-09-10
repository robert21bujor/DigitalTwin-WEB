#!/bin/bash

# Deploy Backend Code to Clean App Service
# Simple, reliable deployment using ZIP method

set -e

echo "🚀 Deploying Backend Code (Clean)"
echo "================================="

RESOURCE_GROUP="DigitalTwin"
BACKEND_APP="digitaltwin-api-clean"

# Create clean deployment package
echo "📦 Creating backend deployment package..."
DEPLOY_DIR="./clean-backend-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy ONLY backend-relevant files (lightweight approach)
# Core Python files
cp requirements.txt $DEPLOY_DIR/
cp launcher.py $DEPLOY_DIR/
cp .env $DEPLOY_DIR/

# Copy directory structure needed for imports
cp -r AgentComms/ $DEPLOY_DIR/
cp -r Auth/ $DEPLOY_DIR/
cp -r Core/ $DEPLOY_DIR/
cp -r Departments/ $DEPLOY_DIR/
cp -r Integrations/ $DEPLOY_DIR/
cp -r Memory/ $DEPLOY_DIR/
cp -r Utils/ $DEPLOY_DIR/
cp -r ClickUp/ $DEPLOY_DIR/ 2>/dev/null || true
cp -r Config/ $DEPLOY_DIR/ 2>/dev/null || true

# Copy backend API files
cp -r AgentUI/Backend/ $DEPLOY_DIR/AgentUI/
mkdir -p $DEPLOY_DIR/AgentUI
cp AgentUI/__init__.py $DEPLOY_DIR/AgentUI/ 2>/dev/null || true

# Remove any accidental large files
find $DEPLOY_DIR -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
find $DEPLOY_DIR -name ".next" -type d -exec rm -rf {} + 2>/dev/null || true
find $DEPLOY_DIR -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create ZIP
echo "🔧 Creating deployment ZIP..."
cd $DEPLOY_DIR
zip -r ../backend-clean.zip . -x "*.git*" "node_modules/*" "temp-*"
cd ..

echo "📤 Deploying to Azure..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $BACKEND_APP \
    --src-path backend-clean.zip \
    --type zip

# Get backend URL
BACKEND_URL="https://$(az webapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)"

echo ""
echo "✅ Backend deployment complete!"
echo "==============================="
echo "🌐 Backend URL: $BACKEND_URL"
echo "📚 API Docs: $BACKEND_URL/docs"
echo "❤️  Health: $BACKEND_URL/api/health"
echo ""
echo "⏳ Wait 3-5 minutes for dependencies to install"
echo "🔍 Monitor: Azure Portal → $BACKEND_APP → Log stream"

# Cleanup
rm -rf $DEPLOY_DIR backend-clean.zip
