// ============================================================================
// Core Types for Agent Communication Interface
// ============================================================================

export interface User {
  id: string;                    // Primary key from user_profiles.id
  auth_user_id?: string;         // Foreign key to auth.users.id
  email: string;
  username: string;              // Unique username for Google token assignment
  role: UserRole;
  admin_rights?: AdminRights;
  agent_assignments: AgentAssignment[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
  metadata: Record<string, any>;
  theme?: 'light' | 'dark';
  requires_password_reset?: boolean;  // Indicates if user must change password
  is_first_login?: boolean;           // Indicates if this is user's first login
}

export enum AdminRights {
  NONE = "none",
  ADMIN = "admin",
  SUPER_ADMIN = "super_admin",
  SYSTEM_ADMIN = "system_admin",
}

// Keep in sync with Authentication/role_constants.py COMPANY_ROLES
export enum UserRole {
  NONE = "none",
  CMO = "cmo",
  CEO = "ceo", 
  CTO = "cto",
  CFO = "cfo",
  PRODUCT_MANAGER = "product_manager",
  DIGITAL_MANAGER = "digital_manager",
  CONTENT_MANAGER = "content_manager",
  BUSINESS_DEV_MANAGER = "business_dev_manager",
  OPERATIONS_MANAGER = "operations_manager",
  POSITIONING_AGENT = "positioning_agent",
  PERSONA_AGENT = "persona_agent",
  GTM_AGENT = "gtm_agent",
  COMPETITOR_AGENT = "competitor_agent",
  LAUNCH_AGENT = "launch_agent",
  SEO_AGENT = "seo_agent",
  SEM_AGENT = "sem_agent",
  LANDING_AGENT = "landing_agent",
  ANALYTICS_AGENT = "analytics_agent",
  FUNNEL_AGENT = "funnel_agent",
  CONTENT_AGENT = "content_agent",
  BRAND_AGENT = "brand_agent",
  SOCIAL_AGENT = "social_agent",
  COMMUNITY_AGENT = "community_agent",
  IPM_AGENT = "ipm_agent",
  BDM_AGENT = "bdm_agent",
  PRESALES_ENGINEER_AGENT = "presales_engineer_agent",
  ADVISORY_BOARD_MANAGER_AGENT = "advisory_board_manager_agent",
  HEAD_OF_OPERATIONS_AGENT = "head_of_operations_agent",
  SENIOR_CSM_AGENT = "senior_csm_agent",
  SENIOR_DELIVERY_CONSULTANT_AGENT = "senior_delivery_consultant_agent",
  DELIVERY_CONSULTANT_BG_AGENT = "delivery_consultant_bg_agent",
  DELIVERY_CONSULTANT_HU_AGENT = "delivery_consultant_hu_agent",
  DELIVERY_CONSULTANT_EN_AGENT = "delivery_consultant_en_agent",
  REPORTING_MANAGER_AGENT = "reporting_manager_agent",
  REPORTING_SPECIALIST_AGENT = "reporting_specialist_agent",
  LEGAL_AGENT = "legal_agent",
  EMPLOYEE = "employee",
  CONTRACTOR = "contractor",
  INTERN = "intern",
}

export enum AgentType {
  IPM_AGENT = "ipm_agent",
  BDM_AGENT = "bdm_agent",
  PRESALES_ENGINEER = "presales_engineer",
  HEAD_OF_OPERATIONS = "head_of_operations",
  SENIOR_CSM = "senior_csm",
  DELIVERY_CONSULTANT_EN = "delivery_consultant_en",
  DELIVERY_CONSULTANT_BG = "delivery_consultant_bg",
  DELIVERY_CONSULTANT_HU = "delivery_consultant_hu",
  LEGAL_AGENT = "legal_agent",
  REPORTING_MANAGER = "reporting_manager",
  REPORTING_SPECIALIST = "reporting_specialist",
}

export interface AgentAssignment {
  agent_type: AgentType;
  access_level: string;
  memory_read_access: string[];
  memory_write_access: string[];
  assigned_at: string;
  assigned_by: string;
}

export interface AgentInfo {
  agent_id: string;
  user_name: string;
  role: string;
  department?: string;
  capabilities: string[];
  status: "online" | "offline" | "busy" | "away";
  channel: string;
  supports_intents: MessageIntent[];
  created_at: string;
  last_seen: string;
  metadata: Record<string, any>;
}

export enum MessageIntent {
  GET_ROADMAP = "get_roadmap",
  ASSIGN_TASK = "assign_task",
  UPDATE_TASK_STATUS = "update_task_status",
  REQUEST_TASK_HELP = "request_task_help",
  SHARE_INSIGHTS = "share_insights",
  REQUEST_KNOWLEDGE = "request_knowledge",
  PROVIDE_CONTEXT = "provide_context",
  REQUEST_REVIEW = "request_review",
  PROVIDE_FEEDBACK = "provide_feedback",
  SCHEDULE_MEETING = "schedule_meeting",
  AGENT_STATUS = "agent_status",
  SYSTEM_HEALTH = "system_health",
  ERROR_REPORT = "error_report",
}

export interface MessagePayload {
  content: Record<string, any>;
  attachments?: any[];
  priority?: "low" | "medium" | "high" | "urgent";
  context?: Record<string, any>;
}

export interface AgentMessage {
  message_id: string;
  conversation_id: string;
  sender_id: string;
  recipient_id: string;
  intent: MessageIntent;
  payload: MessagePayload;
  timestamp: string;
  ttl?: number;
  priority?: "low" | "medium" | "high" | "urgent";
  requires_response?: boolean;
  parent_message_id?: string;
  metadata?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: "user" | "agent";
  timestamp: Date;
  agentInfo?: AgentInfo;
  intent?: MessageIntent;
  status?: "sending" | "sent" | "delivered" | "error";
  metadata?: Record<string, any>;
}

export interface Conversation {
  id: string;
  participants: string[];
  title?: string;
  last_message?: ChatMessage;
  updated_at: Date;
  status: "active" | "archived" | "closed";
  metadata?: Record<string, any>;
}

export interface Department {
  name: string;
  display_name: string;
  description: string;
  manager_name: string;
  agents: AgentInfo[];
  memory_collection: string;
  skills: string[];
  routing_keywords: string[];
  subdepartments?: Department[];
}

export interface DashboardMetrics {
  total_agents: number;
  active_agents: number;
  total_conversations: number;
  messages_today: number;
  response_time_avg: number;
  system_health: "healthy" | "warning" | "error";
}

export interface AgentActivity {
  agent_id: string;
  activity_type: "message" | "task" | "status_change";
  description: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

// ============================================================================
// UI-specific Types
// ============================================================================

export interface ChatUIState {
  isConnected: boolean;
  isTyping: boolean;
  currentAgent?: AgentInfo;
  messages: ChatMessage[];
  error?: string;
}

export interface DashboardState {
  selectedDepartment?: string;
  selectedAgent?: string;
  view: "overview" | "agents" | "conversations" | "metrics";
  filters: {
    status?: string;
    department?: string;
    timeRange?: string;
  };
}

export interface NotificationMessage {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  timestamp: Date;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface AgentCompanionState {
  isActive: boolean;
  assignedAgent?: AgentInfo;
  quickActions: string[];
  recentConversations: Conversation[];
  status: "online" | "offline" | "connecting";
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AgentDiscoveryResponse {
  agents: AgentInfo[];
  departments: Department[];
  total_count: number;
}

export interface ConversationHistoryResponse {
  conversations: Conversation[];
  messages: Record<string, ChatMessage[]>;
  pagination: {
    total: number;
    page: number;
    limit: number;
  };
}

// ============================================================================
// WebSocket Types
// ============================================================================

export interface WebSocketMessage {
  type: "message" | "status" | "notification" | "system";
  data: any;
  timestamp: string;
}

export interface TypingIndicator {
  agent_id: string;
  is_typing: boolean;
  timestamp: string;
}

export interface AgentStatusUpdate {
  agent_id: string;
  status: "online" | "offline" | "busy" | "away";
  timestamp: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// Form Types
// ============================================================================

export interface LoginForm {
  email: string;
  password: string;
}

export interface MessageForm {
  content: string;
  intent?: MessageIntent;
  priority?: "low" | "medium" | "high" | "urgent";
  recipient_id?: string;
}

export interface AgentSearchFilters {
  role?: string;
  department?: string;
  status?: string;
  capabilities?: string[];
  search_term?: string;
} 