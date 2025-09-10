import { v4 as uuidv4 } from 'uuid'

export interface Message {
  id: string
  conversation_id: string
  sender_id: string
  sender_name: string
  sender_type: 'user' | 'agent'
  content: string
  message_type: string
  timestamp: string
  metadata: Record<string, any>
}

export interface Conversation {
  id: string
  participants: string[]
  participant_names: string[]
  title: string | null
  status: 'active' | 'archived' | 'closed'
  created_at: string
  updated_at: string
  last_message?: Message
  unread_count: number
  context?: {
    requester_role?: string
    requester_department?: string
  }
}

export interface ChatParticipant {
  id: string
  name: string
  type: 'user' | 'agent'
  agent_type?: string
  status: 'online' | 'busy' | 'offline'
  avatar?: string
  department?: string
  specialization?: string
}

export interface KnowledgeRequest {
  query: string
  requester_role: string
  requester_department?: string
  context?: any
}

// Simple API interfaces for the new backend
interface SimpleChatMessage {
  agent_id: string
  message: string
  sender_name?: string
  conversation_id?: string  // Add optional conversation_id
  user_id: string  // CRITICAL: Add user_id for privacy
  user_role?: string  // Add user_role for companion matching
  is_viewing_conversation?: boolean  // Whether user is currently on this agent's chat page
}

interface SimpleChatResponse {
  agent_id: string
  agent_name: string
  message: string
  timestamp: string
  conversation_id: string
}

interface SimpleAgentInfo {
  id: string
  name: string
  role: string
  department: string
  status: string
  capabilities: string[]
  specialization: string
}

class ChatService {
  private apiUrl = 'http://localhost:8000'
  private conversations = new Map<string, Conversation>()
  private messages = new Map<string, Message[]>()

  constructor() {
    console.log('🚀 Simple Chat Service initialized')
  }

  // Get available chat participants (agents from simple API)
  async getAvailableParticipants(currentUserId: string): Promise<ChatParticipant[]> {
    try {
      const response = await fetch(`${this.apiUrl}/api/agents`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const agents: SimpleAgentInfo[] = await response.json()
      
      console.log('🔍 All available agents:', agents.map(a => ({ name: a.name, department: a.department, role: a.role })))
      
      // Show ALL agents (no filtering) and make them all online
      console.log('✅ Showing all agents from all departments:', agents.map(a => ({ name: a.name, department: a.department, role: a.role })))
      
      return agents.map((agent: SimpleAgentInfo) => ({
        id: agent.id,
        name: agent.name,
        type: 'agent' as const,
        agent_type: agent.role,
        status: 'online', // Make all agents show as online
        avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${agent.id}`,
        department: agent.department,
        specialization: agent.specialization
      }))
    } catch (error) {
      console.error('Failed to fetch agents:', error)
      return []
    }
  }

  // Get conversations (enhanced with persistence and AI titles)
  async getConversations(userId: string): Promise<Conversation[]> {
    try {
      const response = await fetch(`${this.apiUrl}/api/conversations/${userId}`)
      if (!response.ok) {
        if (response.status === 404) {
          return []
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      const conversationsData = data.conversations || []
      const conversations: Conversation[] = []
      
      // Convert API response format to our format
      for (const conv of conversationsData) {
        
        // Handle last_message (either from database or memory format)
        let lastMessage = undefined
        if (conv.last_message) {
          lastMessage = {
            id: conv.last_message.id || 'temp-id',
            conversation_id: conv.id,
            sender_id: conv.last_message.sender_id,
            sender_name: conv.last_message.metadata?.sender_name || conv.last_message.sender_name || conv.last_message.sender_id,
            sender_type: (conv.last_message.metadata?.sender_type || conv.last_message.sender_type || 'agent') as 'user' | 'agent',
            content: conv.last_message.content,
            message_type: conv.last_message.message_type || 'text',
            timestamp: conv.last_message.timestamp,
            metadata: conv.last_message.metadata || {}
          }
        }

        const conversation: Conversation = {
          id: conv.id,
          participants: conv.metadata?.agent_id ? [userId, conv.metadata.agent_id] : [userId],
          participant_names: [userId, conv.agent_info?.name || conv.metadata?.agent_name || 'Unknown Agent'],
          title: conv.title || 'New Conversation',
          status: (conv.status as 'active' | 'archived' | 'closed') || 'active',
          created_at: conv.created_at || new Date().toISOString(),
          updated_at: conv.updated_at || new Date().toISOString(),
          last_message: lastMessage,
          unread_count: 0,
          context: {
            requester_role: userId,
            requester_department: conv.metadata?.user_department
          }
        }
        
        conversations.push(conversation)
        this.conversations.set(conversation.id, conversation)
      }
      
      const sortedConversations = conversations.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      
      return sortedConversations
    } catch (error) {
      console.error('❌ Failed to fetch conversations:', error)
      return []
    }
  }

  // Get messages for a conversation
  async getMessages(conversationId: string): Promise<Message[]> {
    // Always try to fetch from server first to ensure we have the latest messages
    // Only use cache as fallback if server request fails
    
    try {
      // Extract user from conversation ID (handle different formats)
      let userId = ''
      if (conversationId.includes('_agent.')) {
        userId = conversationId.substring(0, conversationId.indexOf('_agent.'))
      } else if (conversationId.includes('_')) {
        userId = conversationId.substring(0, conversationId.lastIndexOf('_'))
      } else {
        return []
      }
      
      const response = await fetch(`${this.apiUrl}/api/conversations/${userId}/${conversationId}/messages`)
      if (!response.ok) {
        if (response.status === 404) {
          return []
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      const messagesData = data.messages || []
      
      const messages: Message[] = messagesData.map((msg: any) => ({
        id: msg.id,
        conversation_id: msg.conversation_id,
        sender_id: msg.sender_id,
        sender_name: msg.sender_name,
        sender_type: msg.sender_type as 'user' | 'agent',
        content: msg.content,
        message_type: msg.message_type || 'text',
        timestamp: msg.timestamp,
        metadata: msg.metadata || {}
      }))
      
      this.messages.set(conversationId, messages)
      return messages
    } catch (error) {
      console.error('❌ Failed to fetch messages:', error)
      // Return cached messages if available, even on error
      return this.messages.get(conversationId) || []
    }
  }

  // Send a message (simplified - no complex routing)
  async sendMessage(conversationId: string, content: string, senderId: string, senderName: string, userRole?: string, userId?: string, isViewingConversation?: boolean): Promise<{message: Message, actualConversationId: string}> {
    const message: Message = {
      id: uuidv4(),
      conversation_id: conversationId,
      sender_id: senderId,
      sender_name: senderName,
      sender_type: 'user',
      content,
      message_type: 'text',
      timestamp: new Date().toISOString(),
      metadata: { userRole }
    }

    // Extract agent ID from conversation ID
    // Format: {user}_{agent_id}_{unique_suffix}
    // Agent IDs start with "agent."
    const parts = conversationId.split('_')
    if (parts.length < 3) {
      throw new Error(`Invalid conversation ID format: ${conversationId}`)
    }
    
    // Find the agent ID part (starts with "agent.")
    let agentId = ''
    for (let i = 1; i < parts.length - 1; i++) { // Skip first (user) and last (suffix)
      if (parts[i].startsWith('agent.')) {
        // Reconstruct agent ID in case it contains underscores
        agentId = parts.slice(i, -1).join('_') // Exclude the last part (suffix)
        break
      }
    }
    
    if (!agentId) {
      throw new Error(`No agent ID found in conversation ID: ${conversationId}`)
    }
    
    console.log(`📤 Sending message to agent: ${agentId} (conversation: ${conversationId})`)
    
    try {
      // Send to simple backend
      const chatRequest: SimpleChatMessage = {
        agent_id: agentId,
        message: content,
        sender_name: senderName,
        conversation_id: conversationId !== 'temp-conversation' ? conversationId : undefined,  // Only pass real conversation IDs
        user_id: userId || senderId,  // Use provided userId or fallback to senderId for backward compatibility
        user_role: userRole,  // Add user role for companion matching
        is_viewing_conversation: isViewingConversation ?? false  // Default to false (send notifications) if not specified
      }
      
      const response = await fetch(`${this.apiUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chatRequest)
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const chatResponse: SimpleChatResponse = await response.json()
      
      // Get the actual conversation ID from the response (may include unique suffix)
      const actualConversationId = chatResponse.conversation_id
      
      // Create agent response message with correct conversation ID
      const agentMessage: Message = {
        id: uuidv4(),
        conversation_id: actualConversationId,
        sender_id: agentId,
        sender_name: chatResponse.agent_name,
        sender_type: 'agent',
        content: chatResponse.message,
        message_type: 'text',
        timestamp: chatResponse.timestamp,
        metadata: {}
      }
      
      // Update user message to use correct conversation ID
      message.conversation_id = actualConversationId
      
      // Store both messages with the correct conversation ID
      const conversationMessages = this.messages.get(actualConversationId) || []
      const updatedMessages = [...conversationMessages, message, agentMessage]
      this.messages.set(actualConversationId, updatedMessages)
      
      // If conversation ID changed, move conversation data to new ID
      if (conversationId !== actualConversationId) {
        const conversation = this.conversations.get(conversationId)
        if (conversation) {
          // Update conversation with new ID
          conversation.id = actualConversationId
          conversation.last_message = agentMessage
          conversation.updated_at = agentMessage.timestamp
          
          // Store under new ID and remove old entry
          this.conversations.set(actualConversationId, conversation)
          this.conversations.delete(conversationId)
          
          // Also clear old messages cache
          this.messages.delete(conversationId)
        }
      } else {
        // Update existing conversation
        const conversation = this.conversations.get(actualConversationId)
        if (conversation) {
          conversation.last_message = agentMessage
          conversation.updated_at = agentMessage.timestamp
          this.conversations.set(actualConversationId, conversation)
        }
      }

      return { message, actualConversationId }
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  // Create a new conversation (with backend persistence)
  async createConversation(participants: string[], title: string, requesterRole?: string, requesterDepartment?: string): Promise<Conversation> {
    const userId = participants[0]
    const agentId = participants[1]
    
    console.log(`🆕 Creating new conversation between ${userId} and ${agentId}`)
    
    try {
      // Call backend API to create conversation
      const response = await fetch(`${this.apiUrl}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          agent_id: agentId,
          title: title
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`)
      }
      
      const data = await response.json()
      
      console.log(`✅ Backend created conversation: ${data.id}`)
      
      // Format response to match our Conversation interface
      const conversation: Conversation = {
        id: data.id,
        participants: data.participants,
        participant_names: [userId, data.agent_info?.name || 'Agent'],
        title: data.title,
        status: data.status as 'active' | 'archived' | 'closed',
        created_at: data.created_at,
        updated_at: data.updated_at,
        unread_count: 0,
        context: {
          requester_role: requesterRole,
          requester_department: requesterDepartment
        }
      }
      
      // Cache the conversation locally
      this.conversations.set(conversation.id, conversation)
      
      return conversation
      
    } catch (error) {
      console.error('❌ Failed to create conversation:', error)
      
      // Fallback to local conversation creation if backend fails
      const uniqueSuffix = Math.random().toString(36).substring(2, 10)
      const conversationId = `${userId}_${agentId}_${uniqueSuffix}`
      
      console.log(`🔄 Falling back to local conversation: ${conversationId}`)
      
      const conversation: Conversation = {
        id: conversationId,
        participants,
        participant_names: participants,
        title,
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        unread_count: 0,
        context: {
          requester_role: requesterRole,
          requester_department: requesterDepartment
        }
      }

      this.conversations.set(conversation.id, conversation)
      return conversation
    }
  }

  // Simplified agent query (direct chat)
  async queryAgent(agentId: string, query: string, requesterRole: string, context?: any): Promise<void> {
    // This is now handled by sendMessage - no separate querying needed
    console.log(`Direct message to ${agentId}: ${query}`)
  }

  // Subscribe to messages (simplified - no real-time for now)
  subscribeToMessages(conversationId: string, callback: (message: Message) => void): () => void {
    // For the simple version, we'll poll for new messages
    const interval = setInterval(async () => {
      try {
        const messages = await this.getMessages(conversationId)
        const currentMessages = this.messages.get(conversationId) || []
        
        // Check for new messages
        if (messages.length > currentMessages.length) {
          const newMessages = messages.slice(currentMessages.length)
          newMessages.forEach(callback)
          this.messages.set(conversationId, messages)
        }
      } catch (error) {
        // Ignore polling errors
      }
    }, 10000) // Poll every 10 seconds (reduced from 2 seconds)
    
    return () => clearInterval(interval)
  }

  // Subscribe to conversation updates (simplified)
  subscribeToConversations(userId: string, callback: (conversations: Conversation[]) => void): () => void {
    // For the simple version, we'll poll for conversation updates
    const interval = setInterval(async () => {
      try {
        const conversations = await this.getConversations(userId)
        callback(conversations)
      } catch (error) {
        // Ignore polling errors
      }
    }, 5000) // Poll every 5 seconds for more responsive updates
    
    return () => clearInterval(interval)
  }

  // Cleanup (simplified)
  cleanup() {
    console.log('🧹 Simple chat service cleanup')
  }

  // Check connection (always true for simple version)
  isConnected(): boolean {
    return true
  }
}

export const chatService = new ChatService() 