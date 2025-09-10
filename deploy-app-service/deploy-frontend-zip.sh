#!/bin/bash

# Deploy Frontend via ZIP (easier than Git)
# No authentication issues - uses Azure CLI session

set -e

echo "📦 Creating ZIP deployment for Frontend"
echo "======================================"

FRONTEND_APP_NAME="digitaltwin-frontend"
RESOURCE_GROUP="DigitalTwin"
DEPLOY_DIR="./temp-frontend-deploy"

# Create ZIP file
cd $DEPLOY_DIR
echo "🔧 Creating deployment package..."
zip -r ../frontend-deploy.zip . -x "*.git*"
cd ..

echo "📤 Deploying to Azure App Service..."
az webapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FRONTEND_APP_NAME \
    --src frontend-deploy.zip

echo ""
echo "🎉 Frontend deployment complete!"
echo "📍 Your frontend: https://digitaltwin-frontend-eshvebaxf7f4gmg9.francecentral-01.azurewebsites.net"
echo "⏳ Build time: ~2-3 minutes"
echo ""

# Cleanup
rm -f frontend-deploy.zip
echo "🧹 Cleaned up deployment files"

