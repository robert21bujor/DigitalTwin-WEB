import { adminCreateUser, adminListUsers } from '@/lib/supabase-admin';
import { getCurrentUserServer } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

// GET /api/admin/users - List all users
export async function GET() {
  try {
    // Check admin permissions
    const currentUser = await getCurrentUserServer();
    if (!currentUser || (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const { profiles, authUsers } = await adminListUsers();
    
    return NextResponse.json({ profiles, authUsers });
  } catch (error: any) {
    console.error('Admin list users error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// POST /api/admin/users - Create new user
export async function POST(request: NextRequest) {
  try {
    // Check admin permissions
    const currentUser = await getCurrentUserServer();
    if (!currentUser || (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const body = await request.json();
    const { email, username, role, adminRights } = body;

    if (!email || !username || !role) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Generate temporary password
    const tempPassword = `Temp${Math.random().toString(36).slice(-8)}!`;

    const result = await adminCreateUser({
      email,
      password: tempPassword,
      username,
      role,
      admin_rights: adminRights || 'none',
      created_by: currentUser.username
    });

    return NextResponse.json({ 
      success: true, 
      user: result.user,
      tempPassword: result.password
    });
  } catch (error: any) {
    console.error('Admin create user error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}