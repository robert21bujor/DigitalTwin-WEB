-- Notification System Database Schema
-- ===================================
-- 
-- Creates tables for the notification system:
-- - notifications: Core notification data
-- - notification_preferences: User notification preferences
-- - notification_subscriptions: User subscriptions to resources
--
-- Compatible with Supabase (PostgreSQL)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Notification severity enum
CREATE TYPE notification_severity AS ENUM ('info', 'warn', 'critical');

-- Notification channel enum  
CREATE TYPE notification_channel AS ENUM ('in_app', 'email', 'push');

-- Delivery state enum
CREATE TYPE delivery_state AS ENUM ('pending', 'sent', 'failed', 'read', 'archived');

-- Digest frequency enum
CREATE TYPE digest_frequency AS ENUM ('realtime', 'hourly_digest', 'daily_digest');

-- Core notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID DEFAULT NULL,  -- For multi-tenant support
    recipient_user_id UUID NOT NULL,
    type VARCHAR(255) NOT NULL,  -- event_key like 'chat.message.created'
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    resource_type VARCHAR(100) DEFAULT NULL,
    resource_id VARCHAR(255) DEFAULT NULL,
    severity notification_severity DEFAULT 'info',
    channels notification_channel[] DEFAULT '{}',
    delivery_state delivery_state DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ DEFAULT NULL,
    archived_at TIMESTAMPTZ DEFAULT NULL,
    source_event_id VARCHAR(255) NOT NULL UNIQUE  -- For idempotency
);

-- User notification preferences table
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID DEFAULT NULL,
    user_id UUID NOT NULL,
    notification_type VARCHAR(255) NOT NULL,  -- event_key or '*' for all
    channel notification_channel NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours JSONB DEFAULT NULL,  -- {tz, start_hour, end_hour}
    frequency digest_frequency DEFAULT 'realtime',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, notification_type, channel)
);

-- User notification subscriptions table
CREATE TABLE notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID DEFAULT NULL,
    user_id UUID NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    notify_on TEXT[] DEFAULT '{}',  -- Array of event types
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, resource_type, resource_id)
);

-- Indexes for performance
CREATE INDEX idx_notifications_recipient_state_created ON notifications(recipient_user_id, delivery_state, created_at DESC);
CREATE INDEX idx_notifications_source_event ON notifications(source_event_id);
CREATE INDEX idx_notifications_type_created ON notifications(type, created_at DESC);
CREATE INDEX idx_notifications_resource ON notifications(resource_type, resource_id);
CREATE INDEX idx_notification_preferences_user ON notification_preferences(user_id);
CREATE INDEX idx_notification_subscriptions_user ON notification_subscriptions(user_id);
CREATE INDEX idx_notification_subscriptions_resource ON notification_subscriptions(resource_type, resource_id);

-- Row Level Security (RLS) policies for Supabase
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own notifications
CREATE POLICY "Users can view own notifications" ON notifications
    FOR SELECT USING (
        recipient_user_id = auth.uid()
    );

-- Policy: Users can update their own notifications (mark as read/archived)
CREATE POLICY "Users can update own notifications" ON notifications
    FOR UPDATE USING (
        recipient_user_id = auth.uid()
    );

-- Policy: System can insert notifications for any user (backend service)
CREATE POLICY "System can insert notifications" ON notifications
    FOR INSERT WITH CHECK (true);

-- Policy: Users can manage their own preferences
CREATE POLICY "Users can manage own preferences" ON notification_preferences
    FOR ALL USING (
        user_id = auth.uid()
    );

-- Policy: Users can manage their own subscriptions
CREATE POLICY "Users can manage own subscriptions" ON notification_subscriptions
    FOR ALL USING (
        user_id = auth.uid()
    );

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_notification_preferences_updated_at 
    BEFORE UPDATE ON notification_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get unread notification count
CREATE OR REPLACE FUNCTION get_unread_count(user_uuid UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER 
        FROM notifications 
        WHERE recipient_user_id = user_uuid 
        AND delivery_state IN ('pending', 'sent')
        AND archived_at IS NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(notification_ids UUID[])
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE notifications 
    SET delivery_state = 'read', read_at = NOW()
    WHERE id = ANY(notification_ids) 
    AND recipient_user_id = auth.uid()
    AND delivery_state IN ('pending', 'sent');
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to archive notifications
CREATE OR REPLACE FUNCTION archive_notifications(notification_ids UUID[])
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE notifications 
    SET delivery_state = 'archived', archived_at = NOW()
    WHERE id = ANY(notification_ids) 
    AND recipient_user_id = auth.uid();
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create default notification preferences for new users
CREATE OR REPLACE FUNCTION create_default_notification_preferences()
RETURNS TRIGGER AS $$
BEGIN
    -- Create default preferences for common notification types
    INSERT INTO notification_preferences (user_id, notification_type, channel, enabled, frequency) VALUES
    (NEW.id, '*', 'in_app', true, 'realtime'),
    (NEW.id, 'chat.agent.response', 'in_app', true, 'realtime'),
    (NEW.id, 'chat.message.created', 'in_app', true, 'hourly_digest'),
    (NEW.id, 'task.assigned', 'in_app', true, 'realtime'),
    (NEW.id, 'task.due.soon', 'in_app', true, 'realtime'),
    (NEW.id, 'task.overdue', 'in_app', true, 'realtime'),
    (NEW.id, 'agent.task.completed', 'in_app', true, 'realtime'),
    (NEW.id, 'agent.task.failed', 'in_app', true, 'realtime'),
    (NEW.id, '*', 'email', false, 'daily_digest'),
    (NEW.id, 'task.overdue', 'email', true, 'realtime'),
    (NEW.id, 'auth.password.reset.required', 'email', true, 'realtime');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: The trigger for default preferences should be added to the user_profiles table
-- This would typically be done in the main user management migration:
-- CREATE TRIGGER create_default_notification_preferences_trigger
--     AFTER INSERT ON user_profiles
--     FOR EACH ROW EXECUTE FUNCTION create_default_notification_preferences();

COMMENT ON TABLE notifications IS 'Core notification storage with delivery tracking';
COMMENT ON TABLE notification_preferences IS 'User preferences for notification delivery channels and frequency';
COMMENT ON TABLE notification_subscriptions IS 'User subscriptions to specific resources for notifications';
COMMENT ON COLUMN notifications.source_event_id IS 'Unique identifier for idempotency - prevents duplicate notifications';
COMMENT ON COLUMN notification_preferences.notification_type IS 'Event type or * for all notifications';
COMMENT ON COLUMN notification_preferences.quiet_hours IS 'JSON: {timezone, start_hour, end_hour} for quiet period';
COMMENT ON COLUMN notification_subscriptions.notify_on IS 'Array of event types to notify about for this resource';
