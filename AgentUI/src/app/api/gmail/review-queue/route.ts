import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const REVIEW_QUEUE_FILE = path.join(process.cwd(), 'Gmail', 'email_filtering', 'review_queue.json');

export async function GET(request: NextRequest) {
  try {
    // Check if review queue file exists
    if (!fs.existsSync(REVIEW_QUEUE_FILE)) {
      return NextResponse.json({ queue: [] });
    }

    // Read and parse the review queue file
    const fileContent = fs.readFileSync(REVIEW_QUEUE_FILE, 'utf-8');
    const reviewQueue = JSON.parse(fileContent);

    // Filter for pending items only
    const pendingItems = reviewQueue.filter((item: any) => 
      item.status === 'pending' || !item.status
    );

    return NextResponse.json({ 
      queue: pendingItems,
      total: pendingItems.length
    });

  } catch (error) {
    console.error('Error reading review queue:', error);
    return NextResponse.json(
      { error: 'Failed to load review queue' },
      { status: 500 }
    );
  }
}