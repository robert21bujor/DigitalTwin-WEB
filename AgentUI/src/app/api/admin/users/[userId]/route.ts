import { adminDeleteUser, adminToggleUserStatus, adminUpdateUserRole } from '@/lib/supabase-admin';
import { getCurrentUserServer } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

// DELETE /api/admin/users/[userId] - Delete user
export async function DELETE(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    // Check admin permissions
    const currentUser = await getCurrentUserServer();
    if (!currentUser || (currentUser.admin_rights !== 'system_admin' && currentUser.admin_rights !== 'super_admin')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const authUserId = searchParams.get('authUserId');

    if (!authUserId) {
      return NextResponse.json({ error: 'Missing authUserId parameter' }, { status: 400 });
    }

    // Prevent self-deletion
    if (params.userId === currentUser.id) {
      return NextResponse.json({ error: 'Cannot delete your own account' }, { status: 400 });
    }

    await adminDeleteUser(params.userId);

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('Admin delete user error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// PATCH /api/admin/users/[userId] - Update user status or role
export async function PATCH(
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
    const { isActive, role, adminRights } = body;

    // Handle status toggle
    if (typeof isActive === 'boolean') {
      await adminToggleUserStatus(params.userId, isActive);
      return NextResponse.json({ success: true });
    }

    // Handle role/admin rights update
    if (role !== undefined || adminRights !== undefined) {
      if (!role || !adminRights) {
        return NextResponse.json({ error: 'Both role and adminRights are required for role updates' }, { status: 400 });
      }

      await adminUpdateUserRole(params.userId, role, adminRights);
      return NextResponse.json({ success: true });
    }

    return NextResponse.json({ error: 'No valid update parameters provided' }, { status: 400 });
  } catch (error: any) {
    console.error('Admin update user error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}