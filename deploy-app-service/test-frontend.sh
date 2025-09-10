#!/bin/bash

# Quick test deployment with minimal Next.js setup
# This will help isolate the startup issue

set -e

echo "🔧 Creating minimal test deployment"
echo "=================================="

FRONTEND_APP_NAME="digitaltwin-frontend"
RESOURCE_GROUP="DigitalTwin"

# Create minimal test directory
TEST_DIR="./test-frontend"
rm -rf $TEST_DIR
mkdir -p $TEST_DIR

# Create minimal package.json
cat > $TEST_DIR/package.json << 'EOF'
{
  "name": "digitaltwin-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "echo 'Hello World Test' && node -e 'console.log(\"Node.js works!\")'"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
EOF

# Create minimal page
mkdir -p $TEST_DIR/pages
cat > $TEST_DIR/pages/index.js << 'EOF'
export default function Home() {
  return <h1>🎉 Frontend Test Success!</h1>
}
EOF

# Create next.config.js
cat > $TEST_DIR/next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    missingSuspenseWithCSRBailout: false
  }
}

module.exports = nextConfig
EOF

echo "📦 Creating test deployment ZIP..."
cd $TEST_DIR
zip -r ../frontend-test.zip . 
cd ..

echo "📤 Deploying test version..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $FRONTEND_APP_NAME \
    --src-path frontend-test.zip \
    --type zip

echo ""
echo "🔧 Test deployment complete!"
echo "📍 Test URL: https://digitaltwin-frontend-eshvebaxf7f4gmg9.francecentral-01.azurewebsites.net"
echo "⏳ Wait 2-3 minutes then check the URL"
echo ""
echo "If this works, the issue is with your main app configuration."
echo "If this fails, the issue is with the Azure App Service setup."

# Cleanup
rm -rf $TEST_DIR frontend-test.zip

