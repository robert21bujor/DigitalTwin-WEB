#!/bin/bash

# Deploy Frontend Code to Clean App Service
# Simple, reliable deployment using ZIP method

set -e

echo "🌐 Deploying Frontend Code (Clean)"
echo "=================================="

RESOURCE_GROUP="DigitalTwin"
FRONTEND_APP="digitaltwin-web-clean"

# Create clean deployment package
echo "📦 Creating frontend deployment package..."
DEPLOY_DIR="./clean-frontend-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy Next.js frontend files only
cp -r AgentUI/package*.json $DEPLOY_DIR/
cp -r AgentUI/next.config.js $DEPLOY_DIR/
cp -r AgentUI/tailwind.config.js $DEPLOY_DIR/
cp -r AgentUI/tsconfig.json $DEPLOY_DIR/
cp -r AgentUI/postcss.config.js $DEPLOY_DIR/
cp -r AgentUI/src/ $DEPLOY_DIR/

# Create deployment configuration
cat > $DEPLOY_DIR/.deployment << 'EOF'
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
EOF

# Create ZIP
echo "🔧 Creating deployment ZIP..."
cd $DEPLOY_DIR
zip -r ../frontend-clean.zip . 
cd ..

echo "📤 Deploying to Azure..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $FRONTEND_APP \
    --src-path frontend-clean.zip \
    --type zip

# Get frontend URL
FRONTEND_URL="https://$(az webapp show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)"

echo ""
echo "✅ Frontend deployment complete!"
echo "==============================="
echo "🌐 Frontend URL: $FRONTEND_URL"
echo ""
echo "⏳ Wait 3-5 minutes for build to complete"
echo "🔍 Monitor: Azure Portal → $FRONTEND_APP → Log stream"

# Cleanup
rm -rf $DEPLOY_DIR frontend-clean.zip
