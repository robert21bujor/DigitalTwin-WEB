# Notifications Catalog

## Detected Stack
- **Backend**: FastAPI + Python
- **Database**: Supabase (PostgreSQL) 
- **Frontend**: Next.js + React + TypeScript
- **Real-time**: To be implemented (WebSocket)

## Notification Events

### 1. Chat & Communication

#### `chat.message.created`
- **Description**: New chat message received from agent or user
- **Severity**: info
- **Default Channels**: in_app, email (digest)
- **Template Variables**: `{sender_name}`, `{message_preview}`, `{agent_name}`, `{conversation_title}`
- **Recipients**: conversation participants, mentioned users
- **Aggregation**: Group by conversation_id within 5 minutes
- **Retention**: 30 days

#### `chat.agent.response`
- **Description**: Agent has responded to user message
- **Severity**: info  
- **Default Channels**: in_app, push
- **Template Variables**: `{agent_name}`, `{response_preview}`, `{conversation_title}`
- **Recipients**: message sender
- **Aggregation**: None (immediate delivery)
- **Retention**: 30 days

#### `chat.conversation.created`
- **Description**: New conversation started with agent
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{agent_name}`, `{user_name}`, `{conversation_title}`
- **Recipients**: conversation participants
- **Aggregation**: None
- **Retention**: 90 days

### 2. Agent Activities

#### `agent.task.started`
- **Description**: Agent has started working on a task
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{agent_name}`, `{task_title}`, `{task_priority}`
- **Recipients**: task assignee, watchers
- **Aggregation**: Group by agent_id within 10 minutes
- **Retention**: 90 days

#### `agent.task.completed`
- **Description**: Agent has completed a task
- **Severity**: info
- **Default Channels**: in_app, email
- **Template Variables**: `{agent_name}`, `{task_title}`, `{completion_summary}`
- **Recipients**: task assignee, watchers, managers
- **Aggregation**: None
- **Retention**: 90 days

#### `agent.task.failed`
- **Description**: Agent task execution failed
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{agent_name}`, `{task_title}`, `{error_summary}`
- **Recipients**: task assignee, admins
- **Aggregation**: None
- **Retention**: 90 days

### 3. System & Integration Events

#### `system.gmail.sync.completed`
- **Description**: Gmail synchronization completed
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{email_count}`, `{sync_duration}`, `{new_documents}`
- **Recipients**: user who initiated sync
- **Aggregation**: Latest only per user
- **Retention**: 7 days

#### `system.gmail.sync.failed`
- **Description**: Gmail synchronization failed
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{error_message}`, `{retry_time}`
- **Recipients**: user who initiated sync, admins
- **Aggregation**: None
- **Retention**: 30 days

#### `integration.clickup.upload.success`
- **Description**: File uploaded to ClickUp successfully
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{filename}`, `{clickup_task_url}`, `{analysis_summary}`
- **Recipients**: uploader
- **Aggregation**: Group by user_id within 5 minutes
- **Retention**: 30 days

#### `integration.clickup.upload.failed`
- **Description**: File upload to ClickUp failed
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{filename}`, `{error_message}`
- **Recipients**: uploader, admins
- **Aggregation**: None
- **Retention**: 30 days

### 4. Authentication & Security

#### `auth.user.login`
- **Description**: User successfully logged in
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{user_name}`, `{login_time}`, `{ip_address}`
- **Recipients**: user (security log)
- **Aggregation**: Latest only per day
- **Retention**: 90 days

#### `auth.password.reset.required`
- **Description**: User required to reset password on login
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{user_name}`, `{reset_reason}`
- **Recipients**: affected user
- **Aggregation**: None
- **Retention**: 30 days

#### `auth.user.role.changed`
- **Description**: User role or permissions changed
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{user_name}`, `{old_role}`, `{new_role}`, `{changed_by}`
- **Recipients**: affected user, admins
- **Aggregation**: None
- **Retention**: 180 days

### 5. System Management (**INFERRED**)

#### `system.maintenance.scheduled`
- **Description**: System maintenance scheduled
- **Severity**: warn
- **Default Channels**: in_app, email
- **Template Variables**: `{start_time}`, `{duration}`, `{affected_services}`
- **Recipients**: all active users
- **Aggregation**: None
- **Retention**: 30 days

#### `system.backup.completed`
- **Description**: System backup completed
- **Severity**: info
- **Default Channels**: in_app
- **Template Variables**: `{backup_size}`, `{completion_time}`
- **Recipients**: admins
- **Aggregation**: Latest only per day
- **Retention**: 7 days

### 6. Task Management (**INFERRED**)

#### `task.assigned`
- **Description**: Task assigned to user or agent
- **Severity**: info
- **Default Channels**: in_app, email
- **Template Variables**: `{task_title}`, `{assignee_name}`, `{due_date}`, `{priority}`
- **Recipients**: assignee, task creator
- **Aggregation**: Group by assignee within 30 minutes
- **Retention**: 90 days

#### `task.due.soon`
- **Description**: Task due within 24 hours
- **Severity**: warn
- **Default Channels**: in_app, email, push
- **Template Variables**: `{task_title}`, `{due_time}`, `{priority}`
- **Recipients**: assignee, watchers
- **Aggregation**: None (bypass quiet hours for critical)
- **Retention**: 30 days

#### `task.overdue`
- **Description**: Task is past due date
- **Severity**: critical
- **Default Channels**: in_app, email, push
- **Template Variables**: `{task_title}`, `{overdue_by}`, `{assignee_name}`
- **Recipients**: assignee, manager, watchers
- **Aggregation**: None (bypass quiet hours)
- **Retention**: 90 days

### 7. Department & Team Events (**INFERRED**)

#### `team.member.added`
- **Description**: New member added to team/department
- **Severity**: info
- **Default Channels**: in_app, email
- **Template Variables**: `{member_name}`, `{team_name}`, `{role}`, `{added_by}`
- **Recipients**: team members, managers
- **Aggregation**: Group by team within 1 hour
- **Retention**: 180 days

#### `department.announcement`
- **Description**: Department-wide announcement
- **Severity**: info
- **Default Channels**: in_app, email
- **Template Variables**: `{title}`, `{content}`, `{department}`, `{sender}`
- **Recipients**: department members
- **Aggregation**: None
- **Retention**: 90 days

## Event Priorities

### Critical (bypass quiet hours)
- `task.overdue`
- `system.security.breach`
- `auth.suspicious.activity`

### High (limited quiet hours bypass)
- `task.due.soon`
- `agent.task.failed`
- `integration.*.failed`

### Normal (respect quiet hours)
- All other events

## Default Notification Preferences

### Realtime (in_app + push)
- `chat.agent.response`
- `task.assigned`
- Critical/High priority events

### Hourly Digest
- `chat.message.created`
- `agent.task.completed`
- `integration.*.success`

### Daily Digest
- `auth.user.login`
- `system.backup.completed`
- Low priority info events

## Retention Policies

- **Critical events**: 180 days
- **High priority**: 90 days  
- **Normal priority**: 30 days
- **Info/Debug events**: 7 days

---

*Note: Items marked as **INFERRED** were not found in the current codebase but are common patterns for this type of platform and should be implemented when those features are added.*
