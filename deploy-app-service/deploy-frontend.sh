#!/bin/bash

# Azure App Service Deployment - Frontend (Next.js)
# Simple, cost-effective deployment

set -e

# Configuration
RESOURCE_GROUP="DigitalTwin"
FRONTEND_APP_NAME="ai-agents-web"
PLAN_NAME="ai-agents-plan"
BACKEND_APP_NAME="ai-agents-api"

echo "🌐 Deploying AI Multi-Agent Frontend to Azure App Service"
echo "=================================================="

# Get backend URL for frontend configuration
BACKEND_URL=$(az webapp show \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query defaultHostName -o tsv 2>/dev/null || echo "backend-not-found")

echo "🔗 Backend URL: https://$BACKEND_URL"

# Create the Frontend App Service
echo "🚀 Creating Frontend App Service..."
az webapp create \
    --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --runtime "NODE|18-lts" \
    --output table

# Set frontend environment variables
echo "🔧 Setting frontend environment variables..."

# Read Supabase settings from .env
SUPABASE_URL=$(grep "NEXT_PUBLIC_SUPABASE_URL=" .env | cut -d'=' -f2-)
SUPABASE_ANON_KEY=$(grep "NEXT_PUBLIC_SUPABASE_ANON_KEY=" .env | cut -d'=' -f2-)

az webapp config appsettings set \
    --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        "NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL" \
        "NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
        "NEXT_PUBLIC_API_URL=https://$BACKEND_URL" \
        "NODE_ENV=production" \
        "NEXT_TELEMETRY_DISABLED=1" \
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
    --output none

# Configure Node.js startup
az webapp config set \
    --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "cd AgentUI && npm start"

# Get the frontend URL
FRONTEND_URL=$(az webapp show \
    --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query defaultHostName -o tsv)

echo ""
echo "✅ Frontend App Service created successfully!"
echo "=================================================="
echo "🌐 Frontend URL: https://$FRONTEND_URL"
echo "🔗 Connected to Backend: https://$BACKEND_URL"
echo ""
echo "🔧 Next steps:"
echo "1. Deploy your code: az webapp up --name $FRONTEND_APP_NAME --resource-group $RESOURCE_GROUP"
echo "2. Or use Git deployment (recommended)"
echo ""
echo "💰 Total monthly cost: ~$25-40 (both apps on shared plan)"
echo "🎉 Much simpler than Container Apps!"
echo ""

