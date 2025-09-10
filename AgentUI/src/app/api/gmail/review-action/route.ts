import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const REVIEW_QUEUE_FILE = path.join(process.cwd(), 'Gmail', 'email_filtering', 'review_queue.json');
const AUDIT_LOG_FILE = path.join(process.cwd(), 'Gmail', 'email_filtering', 'audit_log.jsonl');

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email_id, action, feedback } = body;

    if (!email_id || !action || !['approve', 'deny'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid request parameters' },
        { status: 400 }
      );
    }

    // Read current review queue
    if (!fs.existsSync(REVIEW_QUEUE_FILE)) {
      return NextResponse.json(
        { error: 'Review queue file not found' },
        { status: 404 }
      );
    }

    const fileContent = fs.readFileSync(REVIEW_QUEUE_FILE, 'utf-8');
    const reviewQueue = JSON.parse(fileContent);

    // Find the email in the queue
    const emailIndex = reviewQueue.findIndex((item: any) => 
      item.email_id === email_id || item.message_id === email_id
    );

    if (emailIndex === -1) {
      return NextResponse.json(
        { error: 'Email not found in review queue' },
        { status: 404 }
      );
    }

    const email = reviewQueue[emailIndex];

    // Log the user action to audit log
    const auditEntry = {
      timestamp: new Date().toISOString(),
      email_id: email_id,
      thread_id: email.thread_id || email_id,
      sender_email: email.sender_email,
      subject: email.subject,
      decision: action === 'approve' ? 'user_approved' : 'user_denied',
      stage: 'user_review',
      reason: `user_${action}`,
      details: feedback || `User ${action}d email via dashboard`,
      confidence_score: null,
      user_id: 'dashboard_user'
    };

    // Append to audit log (JSONL format)
    try {
      const auditLogEntry = JSON.stringify(auditEntry) + '\n';
      fs.appendFileSync(AUDIT_LOG_FILE, auditLogEntry);
    } catch (auditError) {
      console.warn('Failed to write to audit log:', auditError);
    }

    // Remove email from review queue
    reviewQueue.splice(emailIndex, 1);

    // Save updated review queue
    fs.writeFileSync(REVIEW_QUEUE_FILE, JSON.stringify(reviewQueue, null, 2));

    // If approved, trigger document processing
    if (action === 'approve') {
      try {
        // Call backend to process the approved email into a document
        const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
        const processResponse = await fetch(`${backendUrl}/api/gmail/process-approved-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message_id: email.message_id || email.email_id,
            user_id: 'test_user',
            sender_email: email.sender_email,
            subject: email.subject,
            timestamp: email.timestamp
          }),
        });

        if (processResponse.ok) {
          console.log(`Email ${email_id} approved and processing triggered successfully`);
        } else {
          const errorText = await processResponse.text();
          console.warn(`Email ${email_id} approved but processing failed:`, errorText);
        }
      } catch (processError) {
        console.warn(`Email ${email_id} approved but processing failed:`, processError);
      }
    }

    return NextResponse.json({
      success: true,
      action: action,
      email_id: email_id,
      message: `Email ${action}d successfully`
    });

  } catch (error) {
    console.error('Error processing review action:', error);
    return NextResponse.json(
      { error: 'Failed to process review action' },
      { status: 500 }
    );
  }
}