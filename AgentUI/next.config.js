/** @type {import('next').NextConfig} */
const path = require('path')
const { loadEnvConfig } = require('@next/env')

// Load .env from parent directory FIRST
const projectDir = process.cwd()
const envDir = path.join(projectDir, '..')
loadEnvConfig(envDir)

// Also manually load with dotenv as backup
require('dotenv').config({ path: path.join(envDir, '.env') })

const nextConfig = {
  // Disable React Strict Mode to prevent OAuth callback double execution
  reactStrictMode: false,
  
  // Explicitly set environment variables for Next.js
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    SUPABASE_URL: process.env.SUPABASE_URL,
    SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY,
  },
  
  // Experimental features
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },
  
  // Suppress font preload warnings
  webpack: (config, { dev }) => {
    if (dev) {
      config.infrastructureLogging = {
        level: 'error',
      }
    }
    return config
  },
}

module.exports = nextConfig 
// Webpack aliases fix for Azure Static Web Apps path mapping
