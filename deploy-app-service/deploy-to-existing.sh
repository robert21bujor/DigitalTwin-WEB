#!/bin/bash

# Deploy to Existing Azure App Service - Backend (FastAPI)
# Deploy your AI Multi-Agent System to the existing 'digitaltwin' App Service

set -e

# Configuration (using your existing App Service)
RESOURCE_GROUP="DigitalTwin"
BACKEND_APP_NAME="digitaltwin"
LOCATION="francecentral"

echo "🚀 Deploying AI Multi-Agent Backend to Azure App Service"
echo "=================================================="
echo "🎯 App Service: $BACKEND_APP_NAME"
echo "🌍 URL: https://digitaltwin-hyhmh2eqbtdpg6ad.francecentral-01.azurewebsites.net"
echo ""

# Check Azure login
if ! az account show > /dev/null 2>&1; then
    echo "❌ Please login to Azure CLI first: az login"
    exit 1
fi

echo "✅ Using existing App Service: $BACKEND_APP_NAME"

# Configure runtime and startup command for FastAPI
echo "⚙️ Configuring Python 3.11 runtime..."
az webapp config set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --linux-fx-version "PYTHON|3.11" \
    --output none

echo "⚙️ Configuring FastAPI startup command..."
az webapp config set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "cd AgentUI/Backend && python -m uvicorn api:app --host 0.0.0.0 --port 8000" \
    --output none

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
            GLOBAL_LLM_SERVICE|AZURE_OPENAI_*|SUPABASE_*|ADMIN_*|MAX_TOKENS|TEMPERATURE|LOG_LEVEL|MEMORY_ENABLED|ENABLE_*|JWT_SECRET)
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

# Set additional required settings for App Service
echo "🔧 Configuring App Service settings..."
az webapp config appsettings set \
    --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
        "PYTHON_ENABLE_GUNICORN_MULTICORE=false" \
        "PYTHONPATH=/home/site/wwwroot" \
        "WEBSITE_WEBDEPLOY_USE_SCM=false" \
    --output none

echo ""
echo "✅ App Service configured successfully!"
echo "=================================================="
echo "🌐 Backend URL: https://digitaltwin-hyhmh2eqbtdpg6ad.francecentral-01.azurewebsites.net"
echo "📚 API Docs: https://digitaltwin-hyhmh2eqbtdpg6ad.francecentral-01.azurewebsites.net/docs"
echo "❤️  Health Check: https://digitaltwin-hyhmh2eqbtdpg6ad.francecentral-01.azurewebsites.net/api/health"
echo ""
echo "🚀 Ready for code deployment!"
echo ""

