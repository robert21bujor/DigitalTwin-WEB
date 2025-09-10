# ClickUp OAuth Integration Setup Guide

This guide explains how to set up ClickUp OAuth integration for the Digital Twin platform.

## Overview

The ClickUp integration provides basic OAuth connection functionality that allows users to securely connect their ClickUp accounts. This is a foundational feature that prepares for future project management integrations.

**Current Scope:** OAuth connection only - no active ClickUp API operations are performed beyond authentication.

## Prerequisites

1. ClickUp account with workspace access
2. ClickUp app creation permissions
3. Access to environment configuration
4. Supabase project with service role access
5. Python `cryptography` library installed

## Step 1: Create ClickUp OAuth App

1. Go to ClickUp Settings → Integrations → ClickUp API
2. Click "Create App"
3. Fill in the app details:
   - **App Name**: Digital Twin Platform
   - **Description**: AI-powered digital twin platform integration
   - **Redirect URL**: `http://localhost:3001/auth/clickup/callback`
   - **Scopes**: Select minimal scopes (start with just `read`)

4. Save the app and note down:
   - **Client ID**        : QAYV04OINH1N0JUUPQ06F9MGL1900CEI
   - **Client Secret**    : 6L9MILESL1TOBCJSTWDFU7IN5LQ5EE26JJP2V7MXKF70AWBDMRNHUK9RSSO3G83N

## Step 2: Configure Environment Variables

Add the following environment variables to your `.env` file:

```bash
# ClickUp OAuth Configuration
CLICKUP_CLIENT_ID=your_clickup_client_id_here
CLICKUP_CLIENT_SECRET=your_clickup_client_secret_here
CLICKUP_REDIRECT_URI=http://localhost:3001/auth/clickup/callback

# ClickUp Security Configuration
CLICKUP_ENCRYPTION_KEY=your_strong_encryption_password_here

# Supabase Configuration (required for service role access)
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### Environment Variable Details

- **CLICKUP_CLIENT_ID**: Your ClickUp app's client ID
- **CLICKUP_CLIENT_SECRET**: Your ClickUp app's client secret (keep secure)
- **CLICKUP_REDIRECT_URI**: OAuth callback URL (must match ClickUp app config)
- **CLICKUP_ENCRYPTION_KEY**: Strong password for token encryption (generate a secure one)
- **SUPABASE_URL**: Your Supabase project URL
- **SUPABASE_ANON_KEY**: Your Supabase anonymous key (public)
- **SUPABASE_SERVICE_ROLE_KEY**: Your Supabase service role key (private, full access)

## Step 3: Database Setup

The ClickUp integration requires a `clickup_tokens` table in your Supabase database. 

### Required Table Schema

```sql
CREATE TABLE clickup_tokens (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  platform_user_id VARCHAR(255),
  provider VARCHAR(50) DEFAULT 'clickup',
  access_token TEXT NOT NULL, -- Encrypted by Supabase
  token_type VARCHAR(50) DEFAULT 'Bearer',
  expires_at TIMESTAMP,
  scopes TEXT,
  clickup_email VARCHAR(255),
  clickup_username VARCHAR(255),
  clickup_user_id VARCHAR(255),
  clickup_profile_data JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  connected_at TIMESTAMP DEFAULT NOW(),
  disconnected_at TIMESTAMP,
  last_verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_clickup_tokens_user_id ON clickup_tokens(user_id);
CREATE INDEX idx_clickup_tokens_active ON clickup_tokens(is_active);
CREATE INDEX idx_clickup_tokens_provider ON clickup_tokens(provider);
```

### Security Configuration

Ensure your Supabase instance has:

#### ✅ 1. Row Level Security (RLS) - Already Enabled
You've already enabled RLS for the `clickup_tokens` table. Great!

#### ✅ 2. Field-Level Encryption - Implemented in Application
The application now automatically encrypts `access_token` before storing in the database using:
- **Algorithm**: Fernet encryption (AES 128 in CBC mode with HMAC)
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Salt**: Hardcoded salt (consider using random salt in production)

#### ✅ 3. Service Role Key - Already Configured
Your service role key is configured via `SUPABASE_SERVICE_ROLE_KEY` environment variable.

### Additional Security Steps

1. **Find your Service Role Key in Supabase:**
   - Go to your Supabase project dashboard
   - Navigate to Settings → API
   - Copy the `service_role` secret key (NOT the anon public key)

2. **Generate a Strong Encryption Key:**
   ```bash
   # Generate a random 32-character password
   openssl rand -base64 32
   ```

3. **Set RLS Policies (if not already done):**
   ```sql
   -- Allow users to only access their own tokens
   CREATE POLICY "Users can only access their own tokens" ON clickup_tokens
   FOR ALL USING (auth.uid()::text = user_id);
   ```

## Step 4: Test the Integration

1. Start your application
2. Navigate to Settings → ClickUp Integration
3. Click "Connect ClickUp"
4. Complete the OAuth flow
5. Verify the connection shows as "Connected"

## Security Features

### Token Storage
- Access tokens are encrypted at rest in Supabase
- No tokens are logged or exposed in application logs
- Tokens are isolated per user with proper access controls

### OAuth Security
- State parameter validation prevents CSRF attacks
- Secure random state generation using `secrets.token_hex()`
- Short-lived authorization codes (10-minute expiration)
- Proper redirect URI validation

### Audit Trail
- Connection/disconnection events are logged
- Last verification timestamps tracked
- No sensitive data in audit logs

## API Endpoints

The integration provides these endpoints:

- `GET /api/clickup/auth-url?user_id={id}` - Get OAuth URL
- `POST /api/clickup/callback` - Handle OAuth callback
- `GET /api/clickup/status?user_id={id}` - Check connection status
- `POST /api/clickup/verify?user_id={id}` - Verify connection
- `POST /api/clickup/disconnect` - Disconnect integration

## Troubleshooting

### Common Issues

1. **Invalid Client ID/Secret**
   - Verify environment variables are set correctly
   - Check ClickUp app configuration matches

2. **Redirect URI Mismatch**
   - Ensure `CLICKUP_REDIRECT_URI` matches ClickUp app settings
   - Verify the callback page exists at the correct path

3. **Database Connection Issues**
   - Check Supabase credentials in environment
   - Verify `clickup_tokens` table exists with correct schema

4. **OAuth Flow Failures**
   - Check browser console for errors
   - Verify popup blockers aren't preventing OAuth window

### Debugging

Enable debug logging by setting:
```bash
LOG_LEVEL=DEBUG
```

Check logs for:
- OAuth URL generation
- Token exchange requests
- Database operations
- API endpoint calls

## Future Development

This basic OAuth integration prepares for future features such as:
- Task synchronization
- Project management integration
- Automated workflow creation
- Time tracking integration

The current implementation provides the authentication foundation needed for these advanced features.

## Support

For issues related to:
- ClickUp API: Check ClickUp API documentation
- OAuth setup: Review this guide and ClickUp app configuration
- Database issues: Check Supabase setup and table schema
- Application errors: Check application logs and error messages
