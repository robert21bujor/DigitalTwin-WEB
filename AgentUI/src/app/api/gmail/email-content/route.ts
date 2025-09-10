import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const messageId = searchParams.get('messageId');
    const userId = searchParams.get('userId') || 'test_user';

    if (!messageId) {
      return NextResponse.json(
        { error: 'Message ID is required' },
        { status: 400 }
      );
    }

    // Call Python backend to fetch email content
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/gmail/email-content/${messageId}?user_id=${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend email fetch error:', errorText);
      return NextResponse.json(
        { error: 'Failed to fetch email content from backend' },
        { status: response.status }
      );
    }

    const emailData = await response.json();
    
    return NextResponse.json({
      content: emailData.content || emailData.body || 'No content available',
      subject: emailData.subject,
      sender: emailData.sender_email || emailData.from,
      date: emailData.date || emailData.timestamp,
      success: true
    });

  } catch (error) {
    console.error('Error fetching email content:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}