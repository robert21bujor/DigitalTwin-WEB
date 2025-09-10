'use client'

import MessageContent from '@/components/chat/MessageContent'
import { SettingsModal } from '@/components/dashboard/SettingsModal'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { chatService, type ChatParticipant, type Conversation, type Message } from '@/services/chatService'
import { useAuthStore } from '@/stores/auth'
import { AlertCircle, Bot, CheckCircle2, Edit, HelpCircle, Loader2, LogOut, MessageSquare, MoreVertical, Paperclip, Plus, RefreshCw, Search, Send, Settings, Trash2, Upload, Users, X } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'

function ChatPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, isAuthenticated, logout, isLoading: authLoading } = useAuthStore()
  
  // Chat state
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [previousConversationId, setPreviousConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [participants, setParticipants] = useState<ChatParticipant[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showNewChat, setShowNewChat] = useState(false)
  const [selectedParticipants, setSelectedParticipants] = useState<string[]>([])
  const [selectedAgent, setSelectedAgent] = useState<ChatParticipant | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  
  // Loading states
  const [loading, setLoading] = useState(true)
  const [sendingMessage, setSendingMessage] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [urlParamsProcessed, setUrlParamsProcessed] = useState(false)
  
  // File upload states
  const [uploadingFile, setUploadingFile] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [showFileUpload, setShowFileUpload] = useState(false)
  
  // Conversation settings states
  const [showConversationMenu, setShowConversationMenu] = useState(false)
  const [showEditTitleModal, setShowEditTitleModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingTitle, setEditingTitle] = useState('')
  const [isSavingTitle, setIsSavingTitle] = useState(false)
  const [isDeletingConversation, setIsDeletingConversation] = useState(false)
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messageInputRef = useRef<HTMLInputElement>(null)
  const conversationMenuRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/')
      return
    }

    initializeChat()
    
    return () => {
      chatService.cleanup()
    }
  }, [isAuthenticated, router])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Reset URL params processing when URL changes
  useEffect(() => {
    setUrlParamsProcessed(false)
  }, [searchParams])

  // Clear current conversation when agent changes
  useEffect(() => {
    if (!user) return
    
    // Clear current conversation when changing agents
    setSelectedConversation(null)
    setMessages([])
  }, [selectedAgent?.id, user?.id])

  // Handle URL parameters for direct chat/agent selection
  useEffect(() => {
    const agentParam = searchParams.get('agent')
    const modeParam = searchParams.get('mode')
    
    // Only process URL params once to prevent spam
    if (urlParamsProcessed || (!agentParam && !modeParam)) {
      return
    }
    
    if (agentParam && participants.length > 0) {
      console.log('🔍 Looking for agent:', agentParam)
      console.log('📋 Available participants:', participants.map(p => ({ name: p.name, agent_type: p.agent_type, id: p.id })))
      
      // Try to find agent by agent_type or by ID that contains the agent type
      const agent = participants.find(p => 
        p.agent_type === agentParam || 
        p.id.includes(agentParam) ||
        p.name.toLowerCase().includes(agentParam.replace(/_/g, ' '))
      )
      
      if (agent) {
        console.log('✅ Found agent for direct chat:', agent)
        setSelectedAgent(agent)
        continueOrStartConversationWithAgent(agent.id)
        setUrlParamsProcessed(true)
      } else {
        console.log('❌ Agent not found:', agentParam)
        toast.error(`Agent ${agentParam} not found`)
        setUrlParamsProcessed(true)
      }
    } else if (modeParam === 'strategic' || modeParam === 'team') {
      // Could handle special chat modes here
      toast.success(`${modeParam} chat mode activated!`)
      setUrlParamsProcessed(true)
    }
  }, [searchParams, participants, urlParamsProcessed])

  const initializeChat = async () => {
    if (!user) return
    
    try {
      setLoading(true)
      
      // Load conversations and participants using authenticated user ID
      const userId = user?.id || "guest"  // Use authenticated user ID
      const [conversationsData, participantsData] = await Promise.all([
        chatService.getConversations(userId),
        chatService.getAvailableParticipants(userId)
      ])
      
      setConversations(conversationsData)
      setParticipants(participantsData)
      
      // Set up real-time conversation updates
      const unsubscribe = chatService.subscribeToConversations(userId, (updatedConversations) => {
        setConversations(updatedConversations)
      })
      
      setError(null)
    } catch (err) {
      console.error('Failed to initialize chat:', err)
      setError('Failed to load chat data')
      toast.error('Failed to load chat data')
    } finally {
      setLoading(false)
    }
  }

  // Trigger title generation for previous conversation when switching
  const triggerTitleGeneration = async (conversationId: string) => {
    try {
      // Skip if no conversation ID or if it's a temporary/invalid ID
      if (!conversationId || conversationId === 'temp-conversation' || conversationId.length < 10) {
        return
      }

      // Check if conversation exists in our current conversations list first
      const conversationExists = conversations.some(conv => conv.id === conversationId)
      if (!conversationExists) {
        console.log(`⚠️ Conversation ${conversationId} not found in local state, but attempting title generation anyway...`)
        // Don't return - still try to generate title as conversation might exist in backend
      }

      const response = await fetch('http://localhost:8000/backend/conversations/actions/generate-title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.title) {
          // Update conversations list with new title
          setConversations(prev => 
            prev.map(conv => 
              conv.id === conversationId 
                ? { ...conv, title: data.title }
                : conv
            )
          )
        }
      } else if (response.status === 404) {
        console.log(`Conversation ${conversationId} not found, removing from local list`)
        // Remove the conversation from local state if it doesn't exist
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
      }
    } catch (error) {
      console.error('Failed to generate title:', error)
      // Don't show error to user - this is a background operation
    }
  }

  const selectConversation = async (conversation: Conversation) => {
    if (!user) return
    
    try {
      // Trigger title generation for previous conversation if switching away
      if (previousConversationId && previousConversationId !== conversation.id) {
        // Don't await - let it run in background
        triggerTitleGeneration(previousConversationId)
      }
      
      // Update previous conversation tracking
      setPreviousConversationId(selectedConversation?.id || null)
      
      setSelectedConversation(conversation)
      
      // Auto-select agent from conversation if not already selected
      if (!selectedAgent || !conversation.id.includes(selectedAgent.id)) {
        const parts = conversation.id.split('_')
        let agentId = ''
        
        if (parts.length >= 3) {
          for (let i = 1; i < parts.length - 1; i++) {
            if (parts[i].startsWith('agent.')) {
              agentId = parts.slice(i, -1).join('_')
              break
            }
          }
        }
        
        if (agentId) {
          const agent = participants.find(p => p.id === agentId)
          if (agent) {
            setSelectedAgent(agent)
          }
        }
      }
      
      // Load messages for this conversation (don't clear first to avoid flickering)
      const conversationMessages = await chatService.getMessages(conversation.id)
      setMessages(conversationMessages)
      
      // Subscribe to new messages in this conversation
      const unsubscribe = chatService.subscribeToMessages(conversation.id, (newMessage) => {
        setMessages(prev => [...prev, newMessage])
        
        // Show notification if message is from someone else
        if (newMessage.sender_id !== "5c1fc806-8459-47e4-9093-9de03c348406") {
          toast.success(`New message from ${newMessage.sender_name}`)
        }
      })
      
      // Focus on message input
      setTimeout(() => {
        messageInputRef.current?.focus()
      }, 100)
      
    } catch (err) {
      console.error('Failed to load conversation:', err)
      toast.error('Failed to load conversation')
    }
  }

  const sendMessage = async () => {
    if (!user || !selectedConversation || !newMessage.trim() || sendingMessage) return
    
    const messageContent = newMessage.trim()
    const messageTimestamp = new Date().toISOString()
    const userId = user.id  // PRIVACY FIX: Use actual authenticated user ID
    
    // Create user message for immediate display
    const userMessage = {
      id: `user-${Date.now()}`,
      conversation_id: selectedConversation.id,
      sender_id: userId,
      sender_name: user.username || 'You',
      sender_type: 'user' as const,
      content: messageContent,
      message_type: 'text',
      timestamp: messageTimestamp,
      metadata: {}
    }
    
    try {
      setSendingMessage(true)
      
      // Add user message to UI immediately
      setMessages(prev => [...prev, userMessage])
      
      // Clear input immediately for better UX
      setNewMessage('')
      
      // Add typing indicator
      const typingMessage = {
        id: `typing-${Date.now()}`,
        conversation_id: selectedConversation.id,
        sender_id: 'agent-typing',
        sender_name: 'Agent',
        sender_type: 'agent' as const,
        content: '...',
        message_type: 'typing',
        timestamp: new Date().toISOString(),
        metadata: { isTyping: true }
      }
      
      setMessages(prev => [...prev, typingMessage])
      
      // Send message to agent
      const { actualConversationId } = await chatService.sendMessage(
        selectedConversation.id,
        messageContent,
        userId,
        user.username || 'You',
        user.role,  // This becomes userRole in the service
        userId,  // Pass user ID for privacy
        true  // User is actively viewing this conversation
      )
      
      // Update selected conversation ID if it changed
      if (selectedConversation.id !== actualConversationId) {
        const updatedConversation = { ...selectedConversation, id: actualConversationId }
        setSelectedConversation(updatedConversation)
      }
      
      // Remove typing indicator and get updated messages using actual conversation ID
      const updatedMessages = await chatService.getMessages(actualConversationId)
      setMessages(updatedMessages)
      
      // Update conversation last message info
      const lastMessage = updatedMessages[updatedMessages.length - 1]
      if (lastMessage) {
        setConversations(prev => {
          const existingIndex = prev.findIndex(conv => conv.id === actualConversationId)
          
          if (existingIndex >= 0) {
            // Update existing conversation
            console.log(`🔄 Updating existing conversation: ${actualConversationId}`)
            return prev.map(conv => 
              conv.id === actualConversationId
                ? { ...conv, last_message: lastMessage, updated_at: new Date().toISOString() }
                : conv
            )
          } else {
            // Add new conversation if it doesn't exist
            console.log(`🆕 Adding new conversation to list: ${actualConversationId}`)
            const newConversation = {
              id: actualConversationId,
              participants: [userId, selectedAgent?.id || 'unknown'],
              participant_names: [user.username || 'You', selectedAgent?.name || 'Agent'],
              title: 'New Conversation',
              status: 'active' as const,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              last_message: lastMessage,
              unread_count: 0,
              context: {
                requester_role: user.role
              }
            }
            return [newConversation, ...prev]
          }
        })
      }
        
        // Trigger title generation after successful message exchange (after first exchange)
        if (actualConversationId && updatedMessages.length >= 2) {  // User + Agent message
          console.log(`📋 AUTO-TITLE: Setting up title generation trigger - conversationId: ${actualConversationId}, messages: ${updatedMessages.length}`)
          setTimeout(() => {
            console.log(`🎯 AUTO-TITLE: Executing title generation for conversation ${actualConversationId} after message ${updatedMessages.length}`)
            triggerTitleGeneration(actualConversationId)  // Use actualConversationId
          }, 3000)  // Increased delay to ensure message is fully saved
        } else {
          console.log(`⏭️ AUTO-TITLE: Skipping title generation - conversationId: ${actualConversationId}, messages: ${updatedMessages.length}`)
        }
        
        // Refresh conversations list to ensure consistency with backend
        setTimeout(async () => {
          try {
            const refreshedConversations = await chatService.getConversations(userId)
            setConversations(refreshedConversations)
            console.log(`🔄 Refreshed conversations list: ${refreshedConversations.length} conversations`)
          } catch (error) {
            console.error('Failed to refresh conversations:', error)
          }
        }, 500)  // Refresh sooner after message is processed
        
      } catch (err) {
        console.error('Failed to send message:', err)
      toast.error('Failed to send message')
      
      // Remove the user message and typing indicator on error
      setMessages(prev => prev.filter(msg => 
        msg.id !== userMessage.id && !msg.metadata?.isTyping
      ))
      
      // Restore the message in input
      setNewMessage(messageContent)
    } finally {
      setSendingMessage(false)
    }
  }

  // File upload handlers
  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Check file size (25MB limit for ClickUp)
    const maxSize = 25 * 1024 * 1024 // 25MB
    if (file.size > maxSize) {
      toast.error(`File too large. Maximum size is 25MB.`)
      return
    }

    // Check file type (basic validation)
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/plain',
      'text/csv',
      'image/png',
      'image/jpeg',
      'image/jpg'
    ]

    if (!allowedTypes.includes(file.type)) {
      toast.error('Unsupported file type. Please use PDF, DOCX, XLSX, CSV, TXT, PNG, or JPG files.')
      return
    }

    setSelectedFile(file)
    setShowFileUpload(true)
  }

  const uploadFileToClickUp = async () => {
    if (!selectedFile || !user || !selectedAgent) {
      toast.error('Missing required information for file upload')
      return
    }

    setUploadingFile(true)
    
    try {
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('user_id', user.id)
      formData.append('agent_id', selectedAgent.id)
      formData.append('conversation_id', selectedConversation?.id || '')
      formData.append('filename', selectedFile.name)

      // Upload file and get analysis
      const response = await fetch('/api/clickup/upload-file', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()

      if (result.success) {
        // Send a message about the successful upload
        const uploadMessage = `📎 **File uploaded to ClickUp successfully!**\n\n` +
          `**File:** ${selectedFile.name}\n` +
          `**Size:** ${(selectedFile.size / 1024).toFixed(1)} KB\n` +
          `${result.clickup_task_url ? `**ClickUp Task:** ${result.clickup_task_url}\n` : ''}` +
          `${result.analysis_summary ? `\n**Analysis:** ${result.analysis_summary}` : ''}`

        // Add upload success message to chat
        const successMessage = {
          id: `upload-success-${Date.now()}`,
          conversation_id: selectedConversation?.id || '',
          sender_id: user.id,
          sender_name: user.username || 'You',
          sender_type: 'user' as const,
          content: uploadMessage,
          message_type: 'text',
          timestamp: new Date().toISOString(),
          metadata: { isFileUpload: true }
        }

        setMessages(prev => [...prev, successMessage])

        toast.success('File uploaded to ClickUp successfully!')
      } else {
        toast.error(result.error || 'Failed to upload file')
      }
    } catch (error) {
      console.error('File upload error:', error)
      toast.error('Failed to upload file to ClickUp')
    } finally {
      setUploadingFile(false)
      setSelectedFile(null)
      setShowFileUpload(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const cancelFileUpload = () => {
    setSelectedFile(null)
    setShowFileUpload(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Conversation settings handlers
  const handleEditTitle = () => {
    if (!selectedConversation) return
    setEditingTitle(selectedConversation.title || 'New Conversation')
    setShowEditTitleModal(true)
    setShowConversationMenu(false)
  }

  const handleSaveTitle = async () => {
    if (!selectedConversation || !editingTitle.trim()) return
    
    setIsSavingTitle(true)
    try {
      // Call API to update conversation title
      const response = await fetch('http://localhost:8000/backend/conversations/actions/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          conversation_id: selectedConversation.id,
          title: editingTitle.trim() 
        })
      })

      if (!response.ok) throw new Error('Failed to update title')

      // Update local state
      const updatedConversation = { ...selectedConversation, title: editingTitle.trim() }
      setSelectedConversation(updatedConversation)
      
      // Update conversations list
      setConversations(prev => 
        prev.map(conv => 
          conv.id === selectedConversation.id 
            ? { ...conv, title: editingTitle.trim() }
            : conv
        )
      )
      
      setShowEditTitleModal(false)
      toast.success('Conversation title updated!')
    } catch (error) {
      console.error('Failed to update title:', error)
      toast.error('Failed to update conversation title')
    } finally {
      setIsSavingTitle(false)
    }
  }

  const handleDeleteConversation = () => {
    setShowDeleteModal(true)
    setShowConversationMenu(false)
  }

  const confirmDeleteConversation = async () => {
    if (!selectedConversation) return
    
    setIsDeletingConversation(true)
    try {
      // Call API to delete conversation
      const response = await fetch('http://localhost:8000/backend/conversations/actions/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: selectedConversation.id })
      })

      if (!response.ok) throw new Error('Failed to delete conversation')

      // Remove from local state
      setConversations(prev => prev.filter(conv => conv.id !== selectedConversation.id))
      setSelectedConversation(null)
      setMessages([])
      setShowDeleteModal(false)
      
      toast.success('Conversation deleted!')
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      toast.error('Failed to delete conversation')
    } finally {
      setIsDeletingConversation(false)
    }
  }

  const continueOrStartConversationWithAgent = async (participantId: string) => {
    if (!user) return
    
    try {
      const agent = participants.find(p => p.id === participantId)
      if (!agent) return
      
      const userId = user.id
      
      // Look for existing conversation with this agent
      const existingConversation = conversations.find(conv => 
        conv.participants.includes(participantId) && conv.participants.includes(userId)
      )
      
      if (existingConversation) {
        console.log(`🔄 Continuing existing conversation with ${agent.name}`)
        setSelectedAgent(agent)
        selectConversation(existingConversation)
      } else {
        console.log(`🆕 No existing conversation found, creating new conversation with ${agent.name}`)
        await createNewConversationWithAgent(participantId)
      }
    } catch (err) {
      console.error('Failed to continue or start conversation:', err)
      toast.error('Failed to open conversation')
    }
  }

  const createNewConversationWithAgent = async (participantId: string) => {
    if (!user) return
    
    try {
      const agent = participants.find(p => p.id === participantId)
      if (!agent) return
      
      console.log(`🆕 Creating new conversation with ${agent.name}`)
      
      // Create new conversation with user role context for knowledge sharing
      const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const userId = user.id  // PRIVACY FIX: Use actual authenticated user ID
      const conversation = await chatService.createConversation(
        [userId, participantId],  // Use real user ID for proper isolation
        `New Chat with ${agent?.name} - ${currentTime}`,
        user.role || 'team_member',
        'general'
      )
      
      setConversations(prev => [conversation, ...prev])
      selectConversation(conversation)
      
      // Set selected agent to filter conversations to this agent only
      setSelectedAgent(agent)
      
      // Immediately refresh conversations from backend to ensure sync
      setTimeout(async () => {
        try {
          const refreshedConversations = await chatService.getConversations(userId)
          setConversations(refreshedConversations)
          console.log(`🔄 Refreshed after new conversation: ${refreshedConversations.length} conversations`)
        } catch (error) {
          console.error('Failed to refresh conversations after creation:', error)
        }
      }, 300)
      
      toast.success(`Started new chat with ${agent?.name}!`)
    } catch (err) {
      console.error('Failed to start conversation:', err)
      toast.error('Failed to start conversation')
    }
  }

  const startConversationWithParticipant = async (participantId: string) => {
    // This function is now only used for explicit "New Chat" actions
    setShowNewChat(false)
    setSelectedAgent(null)
    await createNewConversationWithAgent(participantId)
  }

  const startGroupConversation = async () => {
    if (!user || selectedParticipants.length === 0) return
    
    try {
      const participantNames = selectedParticipants.map(id => 
        participants.find(p => p.id === id)?.name
      ).filter(Boolean)
      
      const conversation = await chatService.createConversation(
        [user.username, ...selectedParticipants],
        `Group chat: ${participantNames.join(', ')}`
      )
      
      setConversations(prev => [conversation, ...prev])
      selectConversation(conversation)
      setShowNewChat(false)
      setSelectedParticipants([])
      
      toast.success('Group conversation started!')
    } catch (err) {
      console.error('Failed to start group conversation:', err)
      toast.error('Failed to start group conversation')
    }
  }

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true)
      toast.loading('Signing out...', { id: 'logout' })
      await logout()
      await new Promise(resolve => setTimeout(resolve, 100))
      toast.success('Successfully signed out!', { id: 'logout' })
      router.replace('/')
    } catch (error) {
      console.error('Logout error:', error)
      toast.error('Failed to sign out. Please try again.', { id: 'logout' })
    } finally {
      setIsLoggingOut(false)
    }
  }

  const getDashboardRoute = () => {
    // All authenticated users go to manager dashboard
    return '/dashboard/manager'
  }

  const navigateToDashboard = () => {
    const dashboardRoute = getDashboardRoute()
    router.push(dashboardRoute)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today'
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday'
    } else {
      return date.toLocaleDateString()
    }
  }

  const filteredParticipants = participants.filter(participant =>
    participant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    participant.agent_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    participant.department?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group agents by department
  const groupAgentsByDepartment = (agents: ChatParticipant[]) => {
    const grouped: { [key: string]: ChatParticipant[] } = {}
    
    agents.forEach(agent => {
      const dept = agent.department || 'Other'
      if (!grouped[dept]) {
        grouped[dept] = []
      }
      grouped[dept].push(agent)
    })
    
    // Sort departments and agents within each department
    const sortedDepartments: { [key: string]: ChatParticipant[] } = {}
    Object.keys(grouped).sort().forEach(dept => {
      sortedDepartments[dept] = grouped[dept].sort((a, b) => a.name.localeCompare(b.name))
    })
    
    return sortedDepartments
  }

  const groupedAgents = groupAgentsByDepartment(filteredParticipants)

  // Close conversation menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (conversationMenuRef.current && !conversationMenuRef.current.contains(event.target as Node)) {
        setShowConversationMenu(false)
      }
    }

    if (showConversationMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showConversationMenu])

  // Trigger title generation for current conversation when leaving chat page
  useEffect(() => {
    return () => {
      // Cleanup: trigger title generation for current conversation when unmounting
      if (selectedConversation?.id) {
        triggerTitleGeneration(selectedConversation.id)
      }
    }
  }, [selectedConversation?.id])

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-lg">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  // Filter conversations by selected agent
  const filteredConversations = selectedAgent ? 
    conversations.filter(conversation => {
      // Extract agent ID from conversation ID
      const parts = conversation.id.split('_')
      if (parts.length >= 3) {
        for (let i = 1; i < parts.length - 1; i++) {
          if (parts[i].startsWith('agent.')) {
            const agentId = parts.slice(i, -1).join('_')
            return agentId === selectedAgent.id
          }
        }
      }
      
      // Fallback: check participants list
      if (conversation.participants.length > 1) {
        const otherParticipant = conversation.participants.find(p => p !== user?.id)
        return otherParticipant === selectedAgent.id
      }
      
      return false
    }).sort((a, b) => 
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    ) : 
    conversations.sort((a, b) => 
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Sidebar - Conversations */}
      <div className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div 
              className="flex items-center space-x-3 cursor-pointer hover:opacity-80 transition-opacity"
              onClick={navigateToDashboard}
              title="Go to Dashboard"
            >
              <Bot className="h-6 w-6 text-primary" />
              <h1 className="text-lg font-semibold">Agent Chat</h1>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm" onClick={() => setShowHelp(true)}>
                <HelpCircle className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowSettings(true)}>
                <Settings className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={handleLogout} disabled={isLoggingOut}>
                {isLoggingOut ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LogOut className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              onClick={() => setShowNewChat(!showNewChat)} 
              size="sm" 
              className="flex-1"
              variant="outline"
            >
              <Bot className="h-4 w-4 mr-2" />
              Change Agent
            </Button>
            <Button variant="outline" size="sm" onClick={initializeChat} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* New Chat Panel */}
        {showNewChat && (
          <div className="p-4 bg-gray-50 dark:bg-gray-900 border-b">
            <div className="space-y-3">
              <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
                <div className="flex items-start space-x-2">
                  <Bot className="h-4 w-4 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Knowledge Sharing Chat</p>
                    <p className="text-xs text-blue-700 dark:text-blue-300">
                      Chat with agents to access their expertise and knowledge. Ask about deals, campaigns, projects, or specific information they have access to.
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search agents by role or department..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              
              {selectedAgent ? (
                // Show selected agent with new chat button
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={selectedAgent.avatar} />
                      <AvatarFallback>
                        {selectedAgent.type === 'agent' ? <Bot className="h-5 w-5" /> : selectedAgent.name[0]}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{selectedAgent.name}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {selectedAgent.department} • {selectedAgent.specialization || selectedAgent.agent_type}
                      </p>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${
                      selectedAgent.status === 'online' ? 'bg-green-400' : 
                      selectedAgent.status === 'busy' ? 'bg-yellow-400' : 'bg-gray-400'
                    }`} />
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      onClick={() => {
                        startConversationWithParticipant(selectedAgent.id)
                        setShowNewChat(false)
                      }}
                      className="flex-1"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      New Chat
                    </Button>
                  </div>
                  
                  <Button 
                    variant="outline" 
                    onClick={() => setSelectedAgent(null)} 
                    className="w-full"
                  >
                    Select Different Agent
                  </Button>
                </div>
              ) : (
                // Show agent selection list organized by department
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {Object.entries(groupedAgents).map(([department, agents]) => (
                    <div key={department} className="space-y-2">
                      {/* Department Header */}
                      <div className="flex items-center space-x-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded-md">
                        <div className={`w-3 h-3 rounded-full ${
                          department === 'BusinessDev' ? 'bg-blue-500' :
                          department === 'Operations' ? 'bg-green-500' :
                          department === 'Sales' ? 'bg-purple-500' :
                          department === 'Marketing' ? 'bg-orange-500' :
                          department === 'Executive' ? 'bg-red-500' :
                          'bg-gray-500'
                        }`} />
                        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                          {department === 'BusinessDev' ? 'Business Development' : department} 
                          <span className="text-xs text-gray-500 ml-1">({agents.length})</span>
                        </h4>
                      </div>
                      
                      {/* Agents in this department */}
                      <div className="space-y-1 ml-4">
                        {agents.map(participant => (
                          <div 
                            key={participant.id} 
                            className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer border-l-2 border-gray-200 dark:border-gray-700 hover:border-blue-400"
                            onClick={() => {
                              setSelectedAgent(participant)
                              setSelectedConversation(null)
                              setMessages([])
                            }}
                          >
                            <Avatar className="h-7 w-7">
                              <AvatarImage src={participant.avatar} />
                              <AvatarFallback className="text-xs">
                                {participant.type === 'agent' ? <Bot className="h-3 w-3" /> : participant.name[0]}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{participant.name}</p>
                              <p className="text-xs text-gray-500 truncate">
                                {participant.specialization || participant.agent_type}
                              </p>
                            </div>
                            <div className={`w-2 h-2 rounded-full ${
                              participant.status === 'online' ? 'bg-green-400' : 
                              participant.status === 'busy' ? 'bg-yellow-400' : 'bg-gray-400'
                            }`} />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  
                  {Object.keys(groupedAgents).length === 0 && (
                    <div className="text-center py-6 text-gray-500">
                      <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No agents found matching your search</p>
                    </div>
                  )}
                </div>
              )}
              
              <Button variant="outline" onClick={() => {
                setShowNewChat(false)
                setSelectedAgent(null)
              }} className="w-full">
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="p-3 bg-red-50 border-b border-red-200 flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* New Chat Button for Selected Agent */}
        {selectedAgent && !showNewChat && (
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <Button 
              onClick={() => startConversationWithParticipant(selectedAgent.id)}
              className="w-full"
              size="sm"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>
        )}

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : filteredConversations.length > 0 ? (
            filteredConversations.map(conversation => (
              <div
                key={conversation.id}
                className={`p-4 border-b border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900 ${
                  selectedConversation?.id === conversation.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                }`}
                onClick={() => selectConversation(conversation)}
              >
                <div className="flex items-center space-x-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback>
                      {conversation.participants.length > 2 ? (
                        <Users className="h-5 w-5" />
                      ) : (
                        <Bot className="h-5 w-5" />
                      )}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium truncate">
                        {conversation.title || conversation.participant_names.filter(name => name !== user.username).join(', ')}
                      </p>
                      {conversation.last_message && (
                        <p className="text-xs text-gray-500">
                          {formatTime(conversation.last_message.timestamp)}
                        </p>
                      )}
                    </div>
                    
                    {conversation.last_message && (
                      <p className="text-sm text-gray-500 truncate">
                        {conversation.last_message.sender_name}: {conversation.last_message.content}
                      </p>
                    )}
                    
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-gray-400">
                        {conversation.participants.length} participants
                      </p>
                      {conversation.unread_count > 0 && (
                        <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-1">
                          {conversation.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MessageSquare className="h-12 w-12 text-gray-300 mb-4" />
              {selectedAgent ? (
                <>
                  <p className="text-gray-500 mb-2">No conversations with {selectedAgent.name}</p>
                  <p className="text-sm text-gray-400">Start your first conversation with this agent</p>
                </>
              ) : (
                <>
                  <p className="text-gray-500 mb-2">No conversations yet</p>
                  <p className="text-sm text-gray-400">Select an agent to view your conversation history</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedConversation ? (
          <>
            {/* Chat Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback>
                      {selectedConversation.participants.length > 2 ? (
                        <Users className="h-5 w-5" />
                      ) : (
                        <Bot className="h-5 w-5" />
                      )}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <h2 className="font-semibold">
                      {selectedConversation.title || selectedConversation.participant_names.filter(name => name !== user.username).join(', ')}
                    </h2>
                    <p className="text-sm text-gray-500">
                      {selectedConversation.participants.length} participants • {selectedConversation.status}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="relative">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => setShowConversationMenu(!showConversationMenu)}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                    
                    {/* Dropdown Menu */}
                    {showConversationMenu && (
                      <div 
                        ref={conversationMenuRef}
                        className="absolute right-0 top-full mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-50"
                      >
                        <div className="py-1">
                          <button
                            onClick={handleEditTitle}
                            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit Title
                          </button>
                          <button
                            onClick={handleDeleteConversation}
                            className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Conversation
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[calc(100vh-200px)]">
              {messages.map((message, index) => {
                const isOwnMessage = message.sender_type === 'user'
                const showDate = index === 0 || formatDate(messages[index - 1].timestamp) !== formatDate(message.timestamp)
                // Create a truly unique key that combines ID, timestamp, and index as fallback
                const messageKey = message.id ? 
                  `${message.id}-${index}` : 
                  `msg-${index}-${message.timestamp || Date.now()}-${message.sender_id}`
                
                return (
                  <div key={messageKey}>
                    {showDate && (
                      <div className="flex justify-center">
                        <span className="bg-gray-200 dark:bg-gray-700 text-xs px-3 py-1 rounded-full">
                          {formatDate(message.timestamp)}
                        </span>
                      </div>
                    )}
                    
                    <div className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}>
                      <div className={`flex space-x-3 max-w-2xl lg:max-w-4xl ${isOwnMessage ? 'flex-row-reverse space-x-reverse' : ''}`}>
                        {!isOwnMessage && (
                          <Avatar className="h-8 w-8">
                            <AvatarFallback>
                              {message.sender_type === 'agent' ? <Bot className="h-4 w-4" /> : message.sender_name[0]}
                            </AvatarFallback>
                          </Avatar>
                        )}
                        
                        <div className={`rounded-xl px-6 py-4 shadow-sm ${
                          isOwnMessage 
                            ? 'bg-blue-500 text-white' 
                            : message.metadata?.isTyping 
                              ? 'bg-gray-100 dark:bg-gray-600 border-2 border-dashed border-gray-300 dark:border-gray-500'
                              : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
                        }`}>
                          {!isOwnMessage && (
                            <p className="text-xs font-medium mb-2 opacity-80">{message.sender_name}</p>
                          )}
                          
                          {message.metadata?.isTyping ? (
                            <div className="flex items-center space-x-2">
                              <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                              </div>
                              <p className="text-sm text-gray-500 ml-2">typing...</p>
                            </div>
                          ) : (
                            <MessageContent content={message.content} />
                          )}
                          
                          {!message.metadata?.isTyping && (
                            <div className="flex items-center justify-end mt-2 space-x-1">
                              <p className={`text-xs ${isOwnMessage ? 'text-blue-100 opacity-80' : 'text-gray-500'}`}>
                                {formatTime(message.timestamp)}
                              </p>
                              {isOwnMessage && (
                                <CheckCircle2 className="h-3 w-3 text-blue-100 opacity-80" />
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center space-x-3">
                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.png,.jpg,.jpeg"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                {/* Upload button */}
                <Button
                  onClick={handleFileUpload}
                  disabled={sendingMessage || uploadingFile}
                  size="sm"
                  variant="outline"
                  title="Upload file to ClickUp"
                >
                  <Paperclip className="h-4 w-4" />
                </Button>
                
                <Input
                  ref={messageInputRef}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about projects, deals, campaigns, or any information they have..."
                  disabled={sendingMessage}
                  className="flex-1"
                />
                <Button 
                  onClick={sendMessage} 
                  disabled={!newMessage.trim() || sendingMessage}
                  size="sm"
                >
                  {sendingMessage ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              {selectedAgent ? (
                <>
                  <Bot className="h-16 w-16 text-blue-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Chat with {selectedAgent.name}
                  </h3>
                  <p className="text-gray-500 mb-4">
                    {filteredConversations.length > 0 
                      ? "Select a conversation from the left to continue, or start a new chat"
                      : "No previous conversations found. Start a new chat to begin."
                    }
                  </p>
                  <p className="text-sm text-gray-400 mb-4">
                    {selectedAgent.department} • {selectedAgent.specialization || selectedAgent.agent_type}
                  </p>
                  <Button onClick={() => continueOrStartConversationWithAgent(selectedAgent.id)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Start New Chat
                  </Button>
                </>
              ) : (
                <>
                  <MessageSquare className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    {user.username}, welcome to Agent Chat!
                  </h3>
                  <p className="text-gray-500 mb-4">
                    Select a conversation or start a new chat with an agent
                  </p>
                  <Button onClick={() => setShowNewChat(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Start New Chat
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Edit Title Modal */}
      <Dialog open={showEditTitleModal} onOpenChange={setShowEditTitleModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Conversation Title</DialogTitle>
            <DialogDescription>
              Give this conversation a meaningful name to help you find it later.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              placeholder="Enter conversation title..."
              className="w-full"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !isSavingTitle) {
                  handleSaveTitle()
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowEditTitleModal(false)}
              disabled={isSavingTitle}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveTitle}
              disabled={!editingTitle.trim() || isSavingTitle}
            >
              {isSavingTitle ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Title'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone and all messages will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowDeleteModal(false)}
              disabled={isDeletingConversation}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmDeleteConversation}
              disabled={isDeletingConversation}
            >
              {isDeletingConversation ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Conversation
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Help Modal */}
      <Dialog open={showHelp} onOpenChange={setShowHelp}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5" />
              Chat Commands & Features
            </DialogTitle>
            <DialogDescription>
              Complete guide to all available chat functionalities and command formats
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Email & File Search */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                🔍 Email & File Search
              </h3>
              <div className="space-y-2">
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">Email Search:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-blue-100 px-1 rounded">emails john</code> - Find emails from John</div>
                    <div><code className="bg-blue-100 px-1 rounded">emails from jane</code> - Find emails from Jane (explicit)</div>
                    <div><code className="bg-blue-100 px-1 rounded">recent emails</code> - Find latest emails</div>
                    <div><code className="bg-blue-100 px-1 rounded">show me emails</code> - General email search</div>
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">File Search:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-green-100 px-1 rounded">find files about Amazon</code> - Semantic file search</div>
                    <div><code className="bg-green-100 px-1 rounded">latest marketing reports</code> - Recent file filtering</div>
                    <div><code className="bg-green-100 px-1 rounded">Executive documents</code> - Department-specific search</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Calendar Integration */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                📅 Calendar Integration
              </h3>
              <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                <div className="text-sm space-y-1">
                  <div><code className="bg-purple-100 px-1 rounded">today</code> / <code className="bg-purple-100 px-1 rounded">What's today?</code> - Show today's events</div>
                  <div><code className="bg-purple-100 px-1 rounded">tomorrow</code> / <code className="bg-purple-100 px-1 rounded">Tomorrow's meetings</code> - Show tomorrow's events</div>
                  <div><code className="bg-purple-100 px-1 rounded">this week</code> / <code className="bg-purple-100 px-1 rounded">next 7 days</code> - Show upcoming events</div>
                  <div><code className="bg-purple-100 px-1 rounded">Find meeting with John</code> - Search events by keywords</div>
                  <div><code className="bg-purple-100 px-1 rounded">my calendar</code> - General calendar view</div>
                </div>
              </div>
            </div>

            {/* Task Management */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                📋 Task Management
              </h3>
              <div className="space-y-2">
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">General Commands:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-orange-100 px-1 rounded">/my tasks</code> / <code className="bg-orange-100 px-1 rounded">/show tasks</code> - View your assigned tasks</div>
                    <div><code className="bg-orange-100 px-1 rounded">create task [description]</code> - Create new task</div>
                    <div><code className="bg-orange-100 px-1 rounded">task update [id] [status]</code> - Update task progress</div>
                  </div>
                </div>
                
                <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">Executive (CMO) Commands:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-red-100 px-1 rounded">CREATE TASK [division] [description]</code></div>
                    <div><code className="bg-red-100 px-1 rounded">VIEW TASKS</code> - See all division tasks</div>
                    <div><code className="bg-red-100 px-1 rounded">ANALYZE [topic]</code> - Strategic analysis</div>
                    <div><code className="bg-red-100 px-1 rounded">COORDINATE [initiative]</code> - Cross-department projects</div>
                  </div>
                </div>

                <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">Manager Commands:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-yellow-100 px-1 rounded">ASSIGN TASK [agent] [description]</code></div>
                    <div><code className="bg-yellow-100 px-1 rounded">VIEW TEAM</code> - Department status</div>
                    <div><code className="bg-yellow-100 px-1 rounded">REVIEW SUBMISSIONS</code> - Approve agent work</div>
                    <div><code className="bg-yellow-100 px-1 rounded">GUIDE [agent] [feedback]</code> - Provide guidance</div>
                  </div>
                </div>

                <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                  <div className="font-medium text-sm mb-2">Agent Commands:</div>
                  <div className="text-sm space-y-1">
                    <div><code className="bg-blue-100 px-1 rounded">VIEW MY TASKS</code> / <code className="bg-blue-100 px-1 rounded">TASK STATUS</code> - Personal task list</div>
                    <div><code className="bg-blue-100 px-1 rounded">UPDATE TASK [id] [status]</code> - Update progress</div>
                    <div><code className="bg-blue-100 px-1 rounded">ASK CLARIFICATION [question]</code> - Get guidance</div>
                    <div><code className="bg-blue-100 px-1 rounded">SUBMIT WORK [description]</code> - Submit for review</div>
                  </div>
                </div>
              </div>
            </div>

            {/* System Commands */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                🔧 System Commands
              </h3>
              <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                <div className="text-sm space-y-1">
                  <div><code className="bg-gray-100 px-1 rounded">WHOAMI</code> - View profile & authentication status</div>
                  <div><code className="bg-gray-100 px-1 rounded">MEMORY</code> - Check memory permissions</div>
                  <div><code className="bg-gray-100 px-1 rounded">AGENTS</code> - View accessible agents</div>
                  <div><code className="bg-gray-100 px-1 rounded">HELP</code> - Show help message</div>
                </div>
              </div>
            </div>

            {/* Tips & Notes */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                💡 Tips & Notes
              </h3>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-3 rounded-lg">
                <div className="text-sm space-y-2">
                  <div><strong>Smart Search:</strong> Use natural language - "Show me files about Amazon" works better than keywords</div>
                  <div><strong>Username Support:</strong> Search "emails john" finds both john@domain.com and john.doe@domain.com</div>
                  <div><strong>Short Queries:</strong> For best results, use concise commands like "emails john" instead of long phrases</div>
                  <div><strong>Multi-language:</strong> Supports both English and Romanian queries</div>
                  <div><strong>Role-based:</strong> Available commands depend on your role (Executive/Manager/Agent)</div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* File Upload Dialog */}
      <Dialog open={showFileUpload} onOpenChange={setShowFileUpload}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload File to ClickUp
            </DialogTitle>
            <DialogDescription>
              Upload and analyze a file, then attach it to a ClickUp task.
            </DialogDescription>
          </DialogHeader>
          
          {selectedFile && (
            <div className="space-y-4">
              <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <Paperclip className="h-5 w-5 text-gray-500" />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{selectedFile.name}</div>
                    <div className="text-xs text-gray-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'Unknown type'}
                    </div>
                  </div>
                  <Button
                    onClick={cancelFileUpload}
                    size="sm"
                    variant="ghost"
                    disabled={uploadingFile}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <div className="text-sm text-gray-600 dark:text-gray-400">
                This file will be:
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Analyzed for content and keywords</li>
                  <li>Uploaded to your ClickUp workspace</li>
                  <li>Attached to a relevant task or new task</li>
                  <li>Summarized in this chat conversation</li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button
              onClick={cancelFileUpload}
              variant="outline"
              disabled={uploadingFile}
            >
              Cancel
            </Button>
            <Button
              onClick={uploadFileToClickUp}
              disabled={uploadingFile || !selectedFile}
            >
              {uploadingFile ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload to ClickUp
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Modal */}
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  )
} 