'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { CheckCircle, XCircle, Mail, Clock, User, Calendar } from 'lucide-react';

interface ReviewEmail {
  email_id?: string;
  message_id?: string;
  timestamp: string | number;
  sender_email: string;
  subject: string;
  reason?: string;
  status?: string;
  body_preview?: string;
  // Additional fields from the actual queue structure
  final_reason?: string;
  final_decision?: string;
  stage1_reason?: string;
  stage2_reasoning?: string;
  stage1_passed?: boolean;
  stage2_passed?: boolean;
  stage2_score?: number;
  whitelisted?: boolean;
  whitelist_reason?: string;
}

export default function EmailReviewDashboard() {
  const [reviewQueue, setReviewQueue] = useState<ReviewEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingEmails, setProcessingEmails] = useState<Set<string>>(new Set());
  const [selectedEmail, setSelectedEmail] = useState<ReviewEmail | null>(null);
  const [emailContent, setEmailContent] = useState<{[key: string]: string}>({});
  const [fetchingContent, setFetchingContent] = useState<Set<string>>(new Set());

  // Load review queue on component mount
  useEffect(() => {
    loadReviewQueue();
  }, []);

  // Helper function to get unique key for each email
  const getEmailKey = (email: ReviewEmail, index: number) => {
    const id = email.email_id || email.message_id;
    return id ? `${id}-${index}` : `email-${index}`;
  };

  // Deduplicate emails based on email_id/message_id
  const deduplicateEmails = (emails: ReviewEmail[]) => {
    const seen = new Set();
    return emails.filter((email, index) => {
      const id = email.email_id || email.message_id;
      if (!id) return true; // Keep emails without IDs
      
      if (seen.has(id)) {
        console.warn(`Duplicate email found with ID: ${id}, skipping duplicate`);
        return false;
      }
      seen.add(id);
      return true;
    });
  };

  const loadReviewQueue = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/gmail/review-queue');
      if (response.ok) {
        const data = await response.json();
        const deduplicatedQueue = deduplicateEmails(data.queue || []);
        setReviewQueue(deduplicatedQueue);
      } else {
        console.error('Failed to load review queue');
      }
    } catch (error) {
      console.error('Error loading review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailAction = async (email: ReviewEmail, action: 'approve' | 'deny') => {
    const emailId = email.email_id || email.message_id || '';
    
    try {
      setProcessingEmails(prev => new Set(prev).add(emailId));
      
      const response = await fetch('/api/gmail/review-action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email_id: emailId,
          action: action,
          feedback: action === 'approve' ? 'User approved' : 'User denied'
        }),
      });

      if (response.ok) {
        // Remove email from queue
        setReviewQueue(prev => prev.filter(e => (e.email_id || e.message_id) !== emailId));
        
        // Show success message with different text for approve vs deny
        if (action === 'approve') {
          console.log(`Email approved and sent for Google Drive processing`);
          // You could add a toast notification here for better UX
        } else {
          console.log(`Email denied and removed from queue`);
        }
      } else {
        console.error(`Failed to ${action} email`);
      }
    } catch (error) {
      console.error(`Error ${action}ing email:`, error);
    } finally {
      setProcessingEmails(prev => {
        const newSet = new Set(prev);
        newSet.delete(emailId);
        return newSet;
      });
    }
  };

  const formatTimestamp = (timestamp: string | number) => {
    try {
      // Handle both string timestamps and Unix timestamps
      const date = typeof timestamp === 'number' 
        ? new Date(timestamp * 1000) 
        : new Date(timestamp);
      
      if (isNaN(date.getTime())) {
        return String(timestamp);
      }
      
      return date.toLocaleString();
    } catch {
      return String(timestamp);
    }
  };

  const truncateSubject = (subject: string, maxLength: number = 50) => {
    return subject.length > maxLength ? subject.substring(0, maxLength) + '...' : subject;
  };

  const fetchEmailContent = async (email: ReviewEmail) => {
    const messageId = email.message_id || email.email_id;
    if (!messageId || emailContent[messageId] || fetchingContent.has(messageId)) {
      return; // Already fetched, fetching, or no ID
    }

    try {
      setFetchingContent(prev => new Set(prev).add(messageId));
      
      const response = await fetch(`/api/gmail/email-content?messageId=${messageId}&userId=test_user`);
      
      if (response.ok) {
        const data = await response.json();
        setEmailContent(prev => ({
          ...prev,
          [messageId]: data.content || 'No content available'
        }));
      } else {
        console.error('Failed to fetch email content');
        const errorMessage = response.status === 404 
          ? 'Email content fetching requires backend restart. Please restart the launcher to enable this feature.'
          : 'Failed to load email content';
        setEmailContent(prev => ({
          ...prev,
          [messageId]: errorMessage
        }));
      }
    } catch (error) {
      console.error('Error fetching email content:', error);
      setEmailContent(prev => ({
        ...prev,
        [messageId]: 'Error loading email content'
      }));
    } finally {
      setFetchingContent(prev => {
        const newSet = new Set(prev);
        newSet.delete(messageId);
        return newSet;
      });
    }
  };

  const handleEmailClick = (email: ReviewEmail) => {
    setSelectedEmail(email);
    // If email doesn't have body_preview, try to fetch it
    if (!email.body_preview) {
      fetchEmailContent(email);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p>Loading review queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Review Queue</h1>
          <p className="text-gray-600 mt-1">
            Review and approve emails that need manual attention
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Badge variant="outline" className="flex items-center space-x-1">
            <Clock className="h-4 w-4" />
            <span>{reviewQueue.length} pending</span>
          </Badge>
          <Button onClick={loadReviewQueue} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {/* Review Queue */}
      {reviewQueue.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No emails pending review</h3>
            <p className="text-gray-600">All emails have been processed!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {reviewQueue.map((email, index) => (
            <Card key={getEmailKey(email, index)} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  {/* Email Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button 
                            variant="ghost" 
                            className="p-0 h-auto font-semibold text-left hover:text-blue-600"
                            onClick={() => handleEmailClick(email)}
                          >
                            {truncateSubject(email.subject)}
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>{email.subject}</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="font-medium">From:</span> {email.sender_email}
                              </div>
                              <div>
                                <span className="font-medium">Date:</span> {formatTimestamp(email.timestamp)}
                              </div>
                              <div>
                                <span className="font-medium">Status:</span> 
                                <Badge className={`ml-2 ${email.final_decision === 'queued' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-700'}`}>
                                  {email.final_decision || email.status || 'Pending'}
                                </Badge>
                              </div>
                              <div>
                                <span className="font-medium">Score:</span> 
                                <span className="ml-2">
                                  {email.stage2_score ? `${(email.stage2_score * 100).toFixed(1)}%` : 'N/A'}
                                  {email.whitelisted && <span className="ml-2 text-green-600 text-sm">✓ Whitelisted</span>}
                                </span>
                              </div>
                            </div>
                            
                            {/* Review Reason Section */}
                            {(email.final_reason || email.reason) && (
                              <div className="mb-4">
                                <h4 className="font-medium mb-2">Review Reason:</h4>
                                <div className="bg-blue-50 p-3 rounded-lg">
                                  <p className="text-sm text-blue-800">
                                    {email.final_reason || email.reason}
                                  </p>
                                </div>
                              </div>
                            )}
                            
                            {/* Processing Details */}
                            {(email.stage1_reason || email.stage2_reasoning) && (
                              <div className="mb-4">
                                <h4 className="font-medium mb-2">Processing Details:</h4>
                                <div className="bg-gray-50 p-3 rounded-lg space-y-2">
                                  {email.stage1_reason && (
                                    <div className="text-sm">
                                      <span className="font-medium text-gray-700">Stage 1 Filter:</span>
                                      <span className={`ml-2 ${email.stage1_passed ? 'text-green-600' : 'text-red-600'}`}>
                                        {email.stage1_passed ? '✓ Passed' : '✗ Failed'} - {email.stage1_reason}
                                      </span>
                                    </div>
                                  )}
                                  {email.stage2_reasoning && (
                                    <div className="text-sm">
                                      <span className="font-medium text-gray-700">Stage 2 AI Filter:</span>
                                      <span className={`ml-2 ${email.stage2_passed ? 'text-green-600' : 'text-orange-600'}`}>
                                        {email.stage2_passed ? '✓ Passed' : '⚠ Queued for Review'} - {email.stage2_reasoning}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                            
                            <div>
                              <h4 className="font-medium mb-2">Email Content Preview:</h4>
                              <div className="bg-gray-50 p-4 rounded-lg">
                                {(() => {
                                  const messageId = email.message_id || email.email_id;
                                  const isFetching = messageId && fetchingContent.has(messageId);
                                  const fetchedContent = messageId ? emailContent[messageId] : null;
                                  
                                  // Show body_preview if available
                                  if (email.body_preview) {
                                    return (
                                      <pre className="whitespace-pre-wrap text-sm">
                                        {email.body_preview}
                                      </pre>
                                    );
                                  }
                                  
                                  // Show loading state while fetching
                                  if (isFetching) {
                                    return (
                                      <div className="text-center py-8 text-gray-500">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                                        <p className="text-sm">Loading email content...</p>
                                        <p className="text-xs mt-1">Fetching from Gmail API</p>
                                      </div>
                                    );
                                  }
                                  
                                  // Show fetched content if available
                                  if (fetchedContent) {
                                    return (
                                      <div>
                                        <div className="mb-2 text-xs text-green-600 font-medium">
                                          ✓ Content loaded from Gmail API
                                        </div>
                                        <pre className="whitespace-pre-wrap text-sm">
                                          {fetchedContent}
                                        </pre>
                                      </div>
                                    );
                                  }
                                  
                                  // Show placeholder for older format emails
                                  return (
                                    <div className="text-center py-8 text-gray-500">
                                      <Mail className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                      <p className="text-sm">Email content will load automatically</p>
                                      <p className="text-xs mt-1">Click this email again if content doesn't appear</p>
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                      <Badge className={email.final_decision === 'queued' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-700'}>
                        {email.final_decision || email.status || 'Pending Review'}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <User className="h-4 w-4" />
                        <span>{email.sender_email}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{formatTimestamp(email.timestamp)}</span>
                      </div>
                    </div>

                    {email.body_preview ? (
                      <p className="text-gray-700 mt-2 text-sm line-clamp-2">
                        {email.body_preview.substring(0, 150)}...
                      </p>
                    ) : (
                      <p className="text-gray-500 mt-2 text-sm italic">
                        📧 Email content preview not available (older format)
                      </p>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-2 ml-4">
                    <Button
                      onClick={() => handleEmailAction(email, 'approve')}
                      disabled={processingEmails.has(email.email_id || email.message_id || '')}
                      size="sm"
                      className="bg-green-600 hover:bg-green-700 text-white"
                    >
                      {processingEmails.has(email.email_id || email.message_id || '') ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Approve
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={() => handleEmailAction(email, 'deny')}
                      disabled={processingEmails.has(email.email_id || email.message_id || '')}
                      size="sm"
                      variant="destructive"
                    >
                      {processingEmails.has(email.email_id || email.message_id || '') ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 mr-1" />
                          Deny
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}