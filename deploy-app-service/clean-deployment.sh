#!/bin/bash

# Clean Deployment - Start Fresh with Both App Services
# Apply all lessons learned for a bulletproof deployment

set -e

echo "🧹 CLEAN DEPLOYMENT - AI Multi-Agent System"
echo "============================================"
echo "🎯 Starting fresh with lessons learned!"
echo ""

# Configuration
RESOURCE_GROUP="DigitalTwin"
LOCATION="francecentral"
PLAN_NAME="ai-agents-plan"
BACKEND_APP="digitaltwin-api-clean"
FRONTEND_APP="digitaltwin-web-clean"

# Step 1: Clean up existing problematic services
echo "🗑️  Step 1: Cleaning up old services..."
echo "Deleting digitaltwin..."
az webapp delete --name digitaltwin --resource-group $RESOURCE_GROUP || echo "Backend not found (OK)"

echo "Deleting digitaltwin-frontend..."
az webapp delete --name digitaltwin-frontend --resource-group $RESOURCE_GROUP || echo "Frontend not found (OK)"

echo "✅ Old services cleaned up"
echo ""

# Step 2: Create App Service Plan (if needed)
echo "📦 Step 2: Creating App Service Plan..."
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku B1 \
    --is-linux \
    --output table || echo "Plan already exists (OK)"

echo "✅ App Service Plan ready"
echo ""

# Step 3: Create Backend App Service (Python/FastAPI)
echo "🐍 Step 3: Creating Backend App Service..."
az webapp create \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --runtime "PYTHON|3.11" \
    --output table

# Configure backend settings (lessons learned)
echo "⚙️ Configuring backend settings..."
az webapp config set \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --startup-file "python -m pip install -r requirements.txt && python -m uvicorn AgentUI.Backend.api:app --host 0.0.0.0 --port 8000"

# Enable application logging
az webapp log config \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --application-logging filesystem \
    --level information

echo "✅ Backend App Service created"
echo ""

# Step 4: Create Frontend App Service (Node.js/Next.js)  
echo "🌐 Step 4: Creating Frontend App Service..."
az webapp create \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --runtime "NODE|20-lts" \
    --output table

# Configure frontend settings
echo "⚙️ Configuring frontend settings..."
az webapp config set \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --startup-file "npm install && npm run build && npm start"

# Enable application logging
az webapp log config \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --application-logging filesystem \
    --level information

echo "✅ Frontend App Service created"
echo ""

# Step 5: Set Environment Variables
echo "🔧 Step 5: Setting environment variables..."

# Backend environment variables
echo "Setting backend environment variables..."
while IFS= read -r line; do
    if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
        continue
    fi
    
    if [[ $line =~ ^[^=]+= ]]; then
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        
        case $key in
            GLOBAL_LLM_SERVICE|AZURE_OPENAI_*|SUPABASE_*|ADMIN_*|MAX_TOKENS|TEMPERATURE|LOG_LEVEL|MEMORY_ENABLED|ENABLE_*|JWT_SECRET)
                echo "  Setting $key for backend..."
                az webapp config appsettings set \
                    --name $BACKEND_APP \
                    --resource-group $RESOURCE_GROUP \
                    --settings "$key=$value" \
                    --output none
                ;;
        esac
    fi
done < .env

# Frontend environment variables  
echo "Setting frontend environment variables..."
BACKEND_URL="https://$BACKEND_APP-randomstring.azurewebsites.net"

# Get actual backend URL
BACKEND_URL=$(az webapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)
BACKEND_URL="https://$BACKEND_URL"

az webapp config appsettings set \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --settings \
        "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
        "NODE_ENV=production" \
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
    --output none

# Add Supabase vars to frontend from .env
while IFS= read -r line; do
    if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
        continue
    fi
    
    if [[ $line =~ ^[^=]+= ]]; then
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        
        case $key in
            NEXT_PUBLIC_SUPABASE_*|SUPABASE_URL|SUPABASE_ANON_KEY)
                echo "  Setting $key for frontend..."
                az webapp config appsettings set \
                    --name $FRONTEND_APP \
                    --resource-group $RESOURCE_GROUP \
                    --settings "$key=$value" \
                    --output none
                ;;
        esac
    fi
done < .env

echo "✅ Environment variables configured"
echo ""

# Get URLs for deployment
BACKEND_URL="https://$(az webapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)"
FRONTEND_URL="https://$(az webapp show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)"

echo "🎉 CLEAN APP SERVICES CREATED!"
echo "=============================="
echo "🐍 Backend:  $BACKEND_URL"
echo "🌐 Frontend: $FRONTEND_URL"
echo ""
echo "📋 Next Steps:"
echo "1. Deploy backend code: ./deploy-app-service/deploy-clean-backend.sh"
echo "2. Deploy frontend code: ./deploy-app-service/deploy-clean-frontend.sh" 
echo "3. Test your AI Multi-Agent System!"
echo ""
echo "💡 Apps are clean, configured, and ready for code deployment!"
echo ""
