#!/bin/bash

# Deploy Frontend to Azure App Service using Git
# This script prepares and deploys your Next.js frontend

set -e

echo "🚀 Preparing Frontend Deployment"
echo "================================="

# Variables (update after you get the Git URL from Azure Portal)
FRONTEND_GIT_URL="https://digitaltwin-frontend-eshvebaxf7f4gmg9.scm.francecentral-01.azurewebsites.net:443/digitaltwin-frontend.git"
FRONTEND_APP_NAME="digitaltwin-frontend"

# Create temporary deployment directory
DEPLOY_DIR="./temp-frontend-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

echo "📦 Copying frontend files..."

# Copy Next.js frontend files
cp -r AgentUI/package*.json $DEPLOY_DIR/
cp -r AgentUI/next.config.js $DEPLOY_DIR/
cp -r AgentUI/tailwind.config.js $DEPLOY_DIR/
cp -r AgentUI/tsconfig.json $DEPLOY_DIR/
cp -r AgentUI/postcss.config.js $DEPLOY_DIR/
cp -r AgentUI/src/ $DEPLOY_DIR/

# Create deployment configuration
cat > $DEPLOY_DIR/.deployment << EOF
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
EOF

# Create web.config for Azure App Service
cat > $DEPLOY_DIR/web.config << EOF
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="iisnode" path="server.js" verb="*" modules="iisnode"/>
    </handlers>
    <rewrite>
      <rules>
        <rule name="NodeInspector" patternSyntax="ECMAScript" stopProcessing="true">
          <match url="^server.js\/debug[\/]?" />
        </rule>
        <rule name="StaticContent">
          <action type="Rewrite" url="public{REQUEST_URI}"/>
        </rule>
        <rule name="DynamicContent">
          <conditions>
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="True"/>
          </conditions>
          <action type="Rewrite" url="server.js"/>
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
EOF

echo "✅ Frontend files prepared in: $DEPLOY_DIR"
echo ""
echo "🚀 Starting Git deployment..."

# Navigate to deployment directory
cd $DEPLOY_DIR

# Initialize Git repository
git init
git add .
git commit -m "Frontend deployment - Next.js AI Multi-Agent System"

# Add Azure remote and deploy
git remote add azure $FRONTEND_GIT_URL
echo "📤 Pushing to Azure App Service..."
git push azure main --force

echo ""
echo "🎉 Frontend deployment initiated!"
echo "📍 Your frontend will be available at:"
echo "https://digitaltwin-frontend-eshvebaxf7f4gmg9.francecentral-01.azurewebsites.net"
echo ""
echo "⏳ Build time: ~3-5 minutes"
echo "🔍 Monitor deployment: Azure Portal → digitaltwin-frontend → Deployment Center"
