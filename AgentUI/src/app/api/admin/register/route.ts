import { getCurrentUserServer } from '@/lib/supabase-server';
import { spawn } from 'child_process';
import { NextRequest, NextResponse } from 'next/server';
import path from 'path';

// POST /api/admin/register - Create user via Python script
export async function POST(request: NextRequest) {
  try {
    // Check admin permissions
    const currentUser = await getCurrentUserServer(request);
    if (!currentUser || (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const body = await request.json();
    const { email, password, role, adminRights } = body;

    if (!email || !password || !role) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Call Python registration script
    const result = await callPythonRegistration(email, password, role, adminRights || 'none');
    
    if (result.success) {
      return NextResponse.json({ 
        success: true, 
        user: result.data,
        message: 'User created successfully via Python registration service'
      });
    } else {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
  } catch (error: any) {
    console.error('Admin register error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

async function callPythonRegistration(email: string, password: string, role: string, adminRights: string): Promise<{success: boolean, data?: any, error?: string}> {
  return new Promise((resolve) => {
    const projectRoot = path.join(process.cwd(), '..');
    const scriptPath = path.join(projectRoot, 'Auth', 'User_management', 'user_registration_api.py');
    
    // Create a Python API script if it doesn't exist
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
    
    # Get command line arguments
    email = '${email}'
    password = '${password}'
    role = '${role}'
    admin_rights = '${adminRights}'
    username = email.split('@')[0]
    
    # Create user
    result = user_registration_service.create_user_account(
        email=email,
        password=password,
        username=username,
        role=role,
        admin_rights=admin_rights
    )
    
    print(json.dumps(result))
    
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