import { adminResetPassword } from '@/lib/supabase-admin';
import { getCurrentUserServer } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

// POST /api/admin/users/[userId]/reset-password - Force password reset
export async function POST(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    // Check admin permissions
    const currentUser = await getCurrentUserServer();
    if (!currentUser || (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const body = await request.json();
    const { authUserId } = body;

    if (!authUserId) {
      return NextResponse.json({ error: 'Missing authUserId' }, { status: 400 });
    }

    // Generate new temporary password
    const tempPassword = `Temp${Math.random().toString(36).slice(-8)}!`;

    await adminResetPassword(authUserId, tempPassword);

    return NextResponse.json({ 
      success: true, 
      tempPassword 
    });
  } catch (error: any) {
    console.error('Admin reset password error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}