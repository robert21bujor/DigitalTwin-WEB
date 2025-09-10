#!/bin/bash

# Azure App Service Deployment - Backend (FastAPI)
# Simple, cost-effective deployment for your AI Multi-Agent System

set -e

# Configuration
RESOURCE_GROUP="DigitalTwin"
BACKEND_APP_NAME="ai-agents-api"
LOCATION="francecentral"
PLAN_NAME="ai-agents-plan"

echo "🚀 Deploying AI Multi-Agent Backend to Azure App Service"
echo "=================================================="
echo "💰 Cost: ~$13-55/month (much cheaper than Container Apps!)"
echo ""

# Check Azure login
if ! az account show > /dev/null 2>&1; then
    echo "❌ Please login to Azure CLI first: az login"
    exit 1
fi

echo "✅ Using existing resource group: $RESOURCE_GROUP"

# Create App Service Plan (shared hosting)
echo "📦 Creating App Service Plan..."
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku B1 \
    --is-linux \
    --output table

# Create the Backend App Service
echo "🚀 Creating Backend App Service..."
az webapp create \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --runtime "PYTHON|3.11" \
    --output table

# Configure startup command for FastAPI
echo "⚙️ Configuring FastAPI startup..."
az webapp config set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "cd AgentUI/Backend && python -m uvicorn api:app --host 0.0.0.0 --port 8000"

# Set essential environment variables from .env file
echo "🔧 Setting environment variables..."

# Read and set key environment variables
while IFS= read -r line; do
    # Skip comments and empty lines
    if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
        continue
    fi
    
    # Extract key=value pairs
    if [[ $line =~ ^[^=]+= ]]; then
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        
        # Set important environment variables
        case $key in
            GLOBAL_LLM_SERVICE|AZURE_OPENAI_*|SUPABASE_*|ADMIN_*|MAX_TOKENS|TEMPERATURE|LOG_LEVEL|MEMORY_ENABLED)
                echo "Setting $key..."
                az webapp config appsettings set \
                    --name $BACKEND_APP_NAME \
                    --resource-group $RESOURCE_GROUP \
                    --settings "$key=$value" \
                    --output none
                ;;
        esac
    fi
done < .env

# Set additional required settings
az webapp config appsettings set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
        "PYTHON_ENABLE_GUNICORN_MULTICORE=true" \
        "PYTHONPATH=/home/site/wwwroot" \
    --output none

# Get the backend URL
BACKEND_URL=$(az webapp show \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query defaultHostName -o tsv)

echo ""
echo "✅ Backend App Service created successfully!"
echo "=================================================="
echo "🌐 Backend URL: https://$BACKEND_URL"
echo "📚 API Docs: https://$BACKEND_URL/docs"
echo "❤️  Health Check: https://$BACKEND_URL/api/health"
echo ""
echo "🔧 Next steps:"
echo "1. Deploy your code: az webapp up --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP"
echo "2. Or use Git deployment (recommended)"
echo ""
echo "💰 Monthly cost: ~$13-20 for B1 plan"
echo "🔑 Authentication: Built into your FastAPI app"
echo ""

