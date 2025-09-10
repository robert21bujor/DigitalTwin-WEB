import { getCurrentUserServer } from '@/lib/supabase-server';
import { spawn } from 'child_process';
import { NextResponse } from 'next/server';
import path from 'path';

// GET /api/admin/users-list - List users via Python script
export async function GET(request: Request) {
  try {
    // Enhanced debug logging
    console.log('🔍 Admin panel access attempt:');
    console.log('  Headers:', Object.fromEntries(request.headers.entries()));
    
    // Check admin permissions
    const currentUser = await getCurrentUserServer(request);
    
    console.log('  Current user result:', currentUser ? {
      username: currentUser.username,
      email: currentUser.email,
      admin_rights: currentUser.admin_rights,
      requires_password_reset: currentUser.requires_password_reset
    } : 'null');
    
    if (!currentUser) {
      console.log('❌ No user found - authentication failed');
      return NextResponse.json({ 
        error: 'Authentication failed - no user found', 
        debug: {
          message: 'No authenticated user found. Please check your login session.',
          hasAuthHeader: !!request.headers.get('Authorization'),
          suggestion: 'Try refreshing the page or logging in again'
        }
      }, { status: 401 });
    }
    
    if (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin') {
      console.log('❌ Access denied. Required: system_admin or super_admin');
      return NextResponse.json({ 
        error: 'Insufficient permissions', 
        debug: {
          hasUser: true,
          userRights: currentUser.admin_rights || 'none',
          username: currentUser.username || 'unknown',
          message: `User ${currentUser.username} has '${currentUser.admin_rights}' rights, but 'system_admin' or 'super_admin' required`,
          requiredRights: ['system_admin', 'super_admin']
        }
      }, { status: 403 });
    }

    // Call Python script to list users
    console.log('📞 Calling Python script to list users...');
    const result = await callPythonListUsers();
    console.log('📄 Python script result:', { success: result.success, hasData: !!result.data, error: result.error });
    
    if (result.success) {
      return NextResponse.json({ 
        profiles: result.data || [],
        authUsers: [] // We'll get this from Supabase directly if needed
      });
    } else {
      console.log('❌ Python script failed:', result.error);
      return NextResponse.json({ 
        error: 'Failed to load users', 
        debug: {
          pythonError: result.error,
          message: 'Python script execution failed',
          suggestion: 'Check server logs for detailed error information'
        }
      }, { status: 500 });
    }
  } catch (error: any) {
    console.error('Admin list users error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

async function callPythonListUsers(): Promise<{success: boolean, data?: any[], error?: string}> {
  return new Promise((resolve) => {
    const projectRoot = path.join(process.cwd(), '..');
    
    const python = spawn('python3', ['-c', `
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(r'${projectRoot}')
sys.path.append(str(project_root))

try:
    from Auth.User_management.admin_register import user_registration_service
    
    if not user_registration_service.supabase_client:
        print(json.dumps({"success": False, "error": "Database not connected"}))
        sys.exit(1)
    
    result = user_registration_service.supabase_client.table('user_profiles').select('*').order('created_at', desc=True).execute()
    
    users = []
    if result.data:
        for user in result.data:
            users.append({
                "id": user.get("id"),
                "auth_user_id": user.get("auth_user_id"), 
                "email": user.get("email"),
                "username": user.get("username"),
                "role": user.get("role"),
                "admin_rights": user.get("admin_rights", "none"),
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
                "metadata": user.get("metadata", {})
            })
    
    print(json.dumps({"success": True, "data": users}))
    
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
`]);

    let output = '';
    let error = '';

    python.stdout.on('data', (data) => {
      output += data.toString();
    });

    python.stderr.on('data', (data) => {
      error += data.toString();
    });

    python.on('close', (code) => {
      try {
        if (code === 0 && output.trim()) {
          const result = JSON.parse(output.trim());
          resolve(result);
        } else {
          resolve({ success: false, error: error || 'Python script failed' });
        }
      } catch (parseError) {
        resolve({ success: false, error: `Failed to parse Python output: ${output}` });
      }
    });

    python.on('error', (err) => {
      resolve({ success: false, error: `Failed to start Python process: ${err.message}` });
    });
  });
}