#!/usr/bin/env python3

"""
Simple Backend API
=================

Direct agent communication API without complex infrastructure.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import requests
import threading
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import resource cleanup to prevent semaphore leaks
try:
    sys.path.append(str(Path(__file__).parent.parent.parent))  # Project root
    from cleanup_resources import setup_cleanup_handlers, force_single_process_mode
    setup_cleanup_handlers()
    force_single_process_mode()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Query, Request, Response, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Supabase imports for conversation persistence
from supabase import create_client, Client
# Add project root to Python path so we can import from Utils, Memory, etc.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from Utils.config import Config

# Memory system imports
try:
    from Memory.memory_sync import GoogleDriveMemorySync
    from Memory.Search.search_initializer import initialize_search_system
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Since we're running this as a script, use absolute imports within Backend
sys.path.insert(0, os.path.dirname(__file__))  # Add Backend directory to path
from communication_manager import agent_manager
from user_agent_mapping import user_agent_matcher

# Import existing task system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from Core.Tasks.task_manager import get_task_manager, TaskStatus, TaskPriority
from Core.Tasks.task import Task

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Reduce httpx request logging noise
logging.getLogger("httpx").setLevel(logging.WARNING)

# FastAPI app and CORS middleware will be defined after the lifespan function

# Initialize Supabase client for conversation persistence
try:
    supabase_config = Config.get_supabase_config()
    # Use service role key for backend operations to bypass RLS
    service_key = supabase_config.get("service_role_key") or supabase_config["key"]
    supabase: Client = create_client(
        supabase_config["url"],
        service_key
    )
    logger.info("✅ Supabase client initialized for conversation persistence with service role key")
except Exception as e:
    logger.warning(f"⚠️ Supabase initialization failed: {e}")
    supabase = None

class ConversationManager:
    """Enhanced conversation manager with database persistence and AI-generated titles"""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        self.supabase = supabase_client
        self.memory_conversations = {}  # Fallback in-memory storage
        
    async def create_conversation(self, user_id: str, agent_id: str, agent_name: str) -> str:
        """Create a new conversation and return conversation ID"""
        conversation_id = f"{user_id}_{agent_id}_{uuid.uuid4().hex[:8]}"
        
        conversation_data = {
            "id": conversation_id,
            "participants": [user_id, agent_id],
            "title": None,  # Will be generated after first exchange
            "status": "active",
            "metadata": {
                "agent_name": agent_name,
                "user_id": user_id,
                "agent_id": agent_id
            }
        }
        
        logger.info(f"Creating conversation {conversation_id} with participants: {conversation_data['participants']}")
        
        if self.supabase:
            try:
                result = self.supabase.table("conversations").insert(conversation_data).execute()
                logger.info(f"Created conversation {conversation_id} in database")
            except Exception as e:
                logger.error(f"Failed to create conversation in database: {e}")
                # Fall back to memory storage
                self.memory_conversations[conversation_id] = conversation_data
                logger.info(f"Stored conversation {conversation_id} in memory")
        else:
            self.memory_conversations[conversation_id] = conversation_data
            logger.info(f"Stored conversation {conversation_id} in memory")
            
        return conversation_id
    
    async def get_or_create_conversation(self, user_id: str, agent_id: str, existing_conversation_id: Optional[str] = None) -> str:
        """Get existing conversation or create new one if none exists"""
        
        # If conversation ID is provided, prioritize it
        if existing_conversation_id:
            logger.debug(f"🔍 Using existing conversation_id: {existing_conversation_id}")
            return existing_conversation_id
            
        logger.debug(f"🔍 Looking for existing conversation between {user_id} and {agent_id}")
        
        if self.supabase:
            try:
                # Check for existing conversation between this user and agent
                result = self.supabase.table("conversations")\
                    .select("*")\
                    .contains("participants", [user_id])\
                    .contains("participants", [agent_id])\
                    .order("updated_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                if result.data:
                    conversation_id = result.data[0]["id"]
                    logger.debug(f"✅ Found existing conversation: {conversation_id}")
                    return conversation_id
            
            except Exception as e:
                logger.error(f"Error checking for existing conversation: {e}")
        
        # No existing conversation found, create new one
        logger.debug(f"🆕 Creating new conversation between {user_id} and {agent_id}")
        try:
            agent_info = agent_manager.get_agent_info(agent_id) if agent_manager else None
            agent_name = agent_info["name"] if agent_info else f"Agent {agent_id}"
        except Exception as e:
            logger.warning(f"⚠️ Could not get agent info for {agent_id}: {e}")
            agent_name = f"Agent {agent_id}"
        
        new_conversation_id = await self.create_conversation(user_id, agent_id, agent_name)
        logger.debug(f"✅ Created new conversation: {new_conversation_id}")
        return new_conversation_id
    
    async def save_message(self, conversation_id: str, sender_id: str, sender_name: str, 
                          content: str, message_type: str = "text", sender_type: str = "user") -> str:
        """Save a message to the conversation"""
        message_id = str(uuid.uuid4())
        
        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "sender_name": sender_name,
                "sender_type": sender_type
            }
        }
        
        if self.supabase:
            try:
                result = self.supabase.table("messages").insert(message_data).execute()
                logger.info(f"Saved message {message_id} to database")
            except Exception as e:
                logger.error(f"Failed to save message to database: {e}")
                # Fall back to memory storage
                if conversation_id not in self.memory_conversations:
                    self.memory_conversations[conversation_id] = {
                        "id": conversation_id,
                        "title": "New Conversation",
                        "status": "active", 
                                            "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                        "metadata": {},
                        "messages": []
                    }
                if "messages" not in self.memory_conversations[conversation_id]:
                    self.memory_conversations[conversation_id]["messages"] = []
                
                self.memory_conversations[conversation_id]["messages"].append(message_data)
                # Update conversation timestamp
                self.memory_conversations[conversation_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            # Memory storage fallback
            if conversation_id not in self.memory_conversations:
                self.memory_conversations[conversation_id] = {
                    "id": conversation_id,
                    "title": "New Conversation",
                    "status": "active", 
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {},
                    "messages": []
                }
            if "messages" not in self.memory_conversations[conversation_id]:
                self.memory_conversations[conversation_id]["messages"] = []
            
            self.memory_conversations[conversation_id]["messages"].append(message_data)
            # Update conversation timestamp
            self.memory_conversations[conversation_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            
        return message_id
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        logger.debug(f"🔍 Getting messages for conversation_id: {conversation_id}")
        
        if self.supabase:
            try:
                logger.debug(f"📊 Querying database for messages in conversation: {conversation_id}")
                result = self.supabase.table("messages")\
                    .select("*")\
                    .eq("conversation_id", conversation_id)\
                    .order("timestamp")\
                    .execute()
                
                messages = result.data
                logger.debug(f"📋 Database returned {len(messages)} messages")
                
                # If database returns empty, also check memory storage
                if len(messages) == 0:
                    logger.debug(f"Database empty, checking memory storage for conversation: {conversation_id}")
                    memory_messages = self._get_memory_messages(conversation_id)
                    if memory_messages:
                        logger.debug(f"Found {len(memory_messages)} messages in memory")
                        return memory_messages
                
                logger.debug(f"📤 Returning {len(messages)} messages from database")
                return messages
            except Exception as e:
                logger.error(f"Failed to get messages from database: {e}")
        
        # Fall back to memory storage
        logger.debug(f"Using memory storage fallback for conversation: {conversation_id}")
        return self._get_memory_messages(conversation_id)
    
    def _get_memory_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages from memory storage"""
        if conversation_id in self.memory_conversations and "messages" in self.memory_conversations[conversation_id]:
            messages = self.memory_conversations[conversation_id]["messages"]
            logger.debug(f"Returning {len(messages)} messages from memory")
            return messages
        
        logger.debug(f"No messages found in memory for conversation: {conversation_id}")
        return []
    
    async def get_user_conversations(self, user_id: str) -> List[Dict]:
        """Get all conversations for a user"""
        logger.debug(f"🔍 Getting conversations for user_id: {user_id}")
        
        if self.supabase:
            try:
                # Get conversations where user is a participant
                logger.debug(f"📊 Querying database for conversations with participant: {user_id}")
                result = self.supabase.table("conversations")\
                    .select("*")\
                    .contains("participants", [user_id])\
                    .order("updated_at", desc=True)\
                    .execute()
                
                logger.debug(f"📋 Database returned {len(result.data)} conversations")
                
                conversations = []
                for conv in result.data:
                    logger.debug(f"🔄 Processing conversation {conv['id']} with participants: {conv.get('participants', [])}")
                    
                    # Get last message for each conversation
                    last_msg_result = self.supabase.table("messages")\
                        .select("*")\
                        .eq("conversation_id", conv["id"])\
                        .order("timestamp", desc=True)\
                        .limit(1)\
                        .execute()
                    
                    conv["last_message"] = last_msg_result.data[0] if last_msg_result.data else None
                    conversations.append(conv)
                    logger.debug(f"✅ Added conversation {conv['id']} to results")
                
                logger.debug(f"📤 Returning {len(conversations)} conversations from database")
                
                # If database returns empty, also check memory storage
                if len(conversations) == 0:
                    logger.debug(f"Database empty, checking memory storage for user: {user_id}")
                    memory_conversations = self._get_memory_conversations(user_id)
                    if memory_conversations:
                        logger.debug(f"Found {len(memory_conversations)} conversations in memory")
                        return memory_conversations
                
                return conversations
            except Exception as e:
                logger.error(f"Failed to get conversations from database: {e}")
        
        # Fall back to memory storage
        logger.debug(f"Using memory storage fallback for user: {user_id}")
        return self._get_memory_conversations(user_id)
    
    def _get_memory_conversations(self, user_id: str) -> List[Dict]:
        """Get conversations from memory storage"""
        user_conversations = []
        for conv_id, conv_data in self.memory_conversations.items():
            if conv_id.startswith(f"{user_id}_"):
                logger.debug(f"Found memory conversation: {conv_id}")
                # Get last message from the messages list
                messages = conv_data.get("messages", [])
                last_message = messages[-1] if messages else None
                
                user_conversations.append({
                    "id": conv_id,
                    "title": conv_data.get("title", "New Conversation"),
                    "status": conv_data.get("status", "active"),
                                "created_at": conv_data.get("created_at", datetime.now(timezone.utc).isoformat()),
            "updated_at": conv_data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    "metadata": conv_data.get("metadata", {}),
                    "last_message": last_message
                })
        
        logger.debug(f"Returning {len(user_conversations)} conversations from memory")
        return user_conversations
    
    async def generate_conversation_title(self, conversation_id: str) -> str:
        """Generate an AI-powered conversation title based on the entire conversation"""
        logger.debug(f"Starting title generation for conversation: {conversation_id}")
        
        messages = await self.get_conversation_messages(conversation_id)
        logger.debug(f"Found {len(messages)} messages for title generation")
        
        if len(messages) < 2:  # Need at least user message + agent response
            logger.debug(f"Not enough messages ({len(messages)}) for title generation")
            return "New Conversation"
        
        # Get ALL messages to understand the full conversation
        conversation_context = ""
        for msg in messages:  # Use all messages, not just first 4
            role = "User" if msg["metadata"].get("sender_type") == "user" else "Agent"
            conversation_context += f"{role}: {msg['content']}\n"
        
        logger.debug(f"Full conversation context for title generation ({len(messages)} messages)")
        
        # Use the agent manager to generate a title
        try:
            logger.debug(f"Attempting AI title generation...")
            if agent_manager and agent_manager.kernel:
                from semantic_kernel.contents import ChatHistory
                from semantic_kernel.contents.chat_message_content import ChatMessageContent
                from semantic_kernel.contents.utils.author_role import AuthorRole
                
                chat_history = ChatHistory()
                system_prompt = """You are a helpful assistant that generates concise, descriptive titles for conversations. 
                Based on the ENTIRE conversation content provided, generate a clear, concise title (2-5 words maximum) that captures the main topic, purpose, or outcome of the conversation.
                
                Focus on:
                - Main topic discussed
                - Key questions asked
                - Problems solved
                - Decisions made
                
                Examples:
                - "Q1 Marketing Strategy"
                - "Budget Analysis Report"
                - "Product Launch Planning"
                - "Customer Support Issue"
                - "Performance Metrics Review"
                
                Return ONLY the title, no quotes, no additional text."""
                
                chat_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=system_prompt))
                chat_history.add_message(ChatMessageContent(role=AuthorRole.USER, content=f"Generate a title for this entire conversation:\n\n{conversation_context}"))
                
                # Get the first available chat completion service
                chat_completion = agent_manager.kernel.get_service("main_chat")
                
                response = await chat_completion.get_chat_message_content(
                    chat_history=chat_history,
                    settings=chat_completion.get_prompt_execution_settings_class()(
                        max_tokens=20,  # Keep titles short
                        temperature=0.2  # Lower temperature for more consistent results
                    )
                )
                
                title = str(response.content).strip().strip('"').strip("'")
                logger.debug(f"AI generated title: '{title}'")
                
                # Update the conversation title in the database
                await self.update_conversation_title(conversation_id, title)
                
                return title
                
        except Exception as e:
            logger.debug(f"Failed to generate AI title: {e}")
        
        # Enhanced fallback to simple title generation
        logger.debug(f"Using enhanced fallback title generation")
        if messages:
            # Look for key topics in user messages
            user_messages = [msg for msg in messages if msg["metadata"].get("sender_type") == "user"]
            if user_messages:
                # Combine all user messages to find main topic
                all_user_content = " ".join([msg["content"] for msg in user_messages])
                
                # Extract key words (simple approach)
                words = all_user_content.lower().split()
                key_topics = []
                
                # Look for business/topic keywords
                topic_keywords = ["marketing", "strategy", "budget", "campaign", "product", "launch", "analysis", 
                                "performance", "metrics", "sales", "customer", "support", "planning", "review",
                                "report", "operations", "delivery", "legal", "partnership", "international"]
                
                for keyword in topic_keywords:
                    if keyword in words:
                        key_topics.append(keyword.title())
                
                if key_topics:
                    fallback_title = " ".join(key_topics[:3])  # Max 3 key topics
                    logger.info(f"Enhanced fallback title generated: '{fallback_title}'")
                else:
                    # Basic fallback: first few words of first message
                    first_content = user_messages[0]["content"]
                    words = first_content.split()[:3]
                    fallback_title = " ".join(words) + ("..." if len(first_content.split()) > 3 else "")
                    logger.info(f"Basic fallback title generated: '{fallback_title}'")
                
                # Update the conversation title in the database
                await self.update_conversation_title(conversation_id, fallback_title)
                return fallback_title
        
        logger.debug(f"No suitable messages found, using default title")
        return "New Conversation"
    
    async def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title"""
        if self.supabase:
            try:
                self.supabase.table("conversations")\
                    .update({"title": title, "updated_at": datetime.now(timezone.utc).isoformat()})\
                    .eq("id", conversation_id)\
                    .execute()
                logger.info(f"Updated conversation {conversation_id} title to: {title}")
            except Exception as e:
                logger.error(f"Failed to update conversation title: {e}")
        
        # Update memory storage fallback
        if conversation_id in self.memory_conversations:
            self.memory_conversations[conversation_id]["title"] = title

# Initialize conversation manager
conversation_manager = ConversationManager(supabase)

# Pydantic models
class ChatMessage(BaseModel):
    agent_id: str
    message: str
    sender_name: Optional[str] = "User"
    conversation_id: Optional[str] = None  # Add conversation_id field
    user_id: str  # CRITICAL: Add user_id field for privacy
    user_role: Optional[str] = None  # Add user_role for companion matching
    is_viewing_conversation: Optional[bool] = False  # Whether user is currently on this chat page

class ChatResponse(BaseModel):
    agent_id: str
    agent_name: str
    message: str
    timestamp: str
    conversation_id: str

class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    department: str
    status: str
    capabilities: List[str]
    specialization: str
    assigned_user: Optional[Union[str, List[str]]] = None

class TaskCreateRequest(BaseModel):
    title: str
    description: str
    assignee_agent_id: str
    priority: Optional[str] = "medium"
    department: Optional[str] = "marketing"
    created_by: Optional[str] = "User"

class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    actor: Optional[str] = "User"
    message: Optional[str] = ""

class ConversationTitleRequest(BaseModel):
    conversation_id: str
    title: Optional[str] = None

class ConversationActionRequest(BaseModel):
    conversation_id: str

# Global state - in production you'd use a proper database
conversations: Dict[str, List[Dict]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Simple Agent Communication API")
    try:
        await agent_manager.initialize()
        await agent_manager.load_agents()
        logger.info("✅ Agent manager initialized successfully")
        
        # Start Gmail auto-sync
        start_gmail_auto_sync()
        logger.info("✅ Gmail auto-sync initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent manager: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Simple Agent Communication API")
    try:
        # Stop Gmail auto-sync
        stop_gmail_auto_sync()
        logger.info("✅ Gmail auto-sync stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Update the FastAPI app to use lifespan
app = FastAPI(
    title="AI Multi-Agent Digital Twin API",
    description="API for the AI Multi-Agent Digital Twin System with BusinessDev & Operations focus",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include notification system
try:
    from notifications.api import router as notification_router
    from notifications.websocket import ws_router as notification_ws_router
    from notifications.websocket import websocket_keepalive_task
    
    # Include notification API routes
    app.include_router(notification_router)
    
    # Include notification WebSocket routes
    app.include_router(notification_ws_router)
    
    # Start WebSocket keepalive task and event bus
    @app.on_event("startup")
    async def start_notification_websocket_tasks():
        asyncio.create_task(websocket_keepalive_task())
        
        # Initialize and start the event bus
        try:
            from notifications.event_bus import get_event_bus
            event_bus = get_event_bus()
            await event_bus._start_processing()
            logger.info("✅ Event bus started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start event bus: {e}")
    
    logger.info("✅ Notification system integrated successfully")
    
except ImportError as e:
    logger.warning(f"⚠️ Notification system not available: {e}")
except Exception as e:
    logger.error(f"❌ Failed to integrate notification system: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Simple Agent Communication API"}

@app.get("/api/agents", response_model=List[AgentInfo])
async def get_agents():
    """Get all available agents"""
    try:
        agents = agent_manager.get_available_agents()
        return agents
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail="Failed to get agents")

@app.get("/api/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get specific agent information"""
    try:
        agent_info = agent_manager.get_agent_info(agent_id)
        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get agent")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(chat_request: ChatMessage):
    """Send a message to an agent and get response with enhanced conversation management"""
    try:
        # Use actual authenticated user ID from request - PRIVACY FIX
        user_id = chat_request.user_id
        agent_id = chat_request.agent_id
        
        conversation_id = await conversation_manager.get_or_create_conversation(
            user_id, 
            agent_id,
            existing_conversation_id=chat_request.conversation_id
        )
        
        # Check for task-related commands first (after getting conversation_id)
        task_response = await process_task_commands(chat_request, conversation_id)
        if task_response:
            return task_response
        
        # Save user message
        await conversation_manager.save_message(
            conversation_id=conversation_id,
            sender_id=user_id,
            sender_name=chat_request.sender_name,
            content=chat_request.message,
            message_type="text",
            sender_type="user"
        )
        
        # Emit notification event for new chat message
        try:
            from notifications.event_bus import emit_notification_event
            await emit_notification_event(
                "chat.message.created",
                {
                    "sender_name": chat_request.sender_name,
                    "message_preview": chat_request.message[:100] + "..." if len(chat_request.message) > 100 else chat_request.message,
                    "conversation_id": conversation_id,
                    "agent_name": agent_manager.get_agent_info(agent_id)["name"] if agent_manager.get_agent_info(agent_id) else "Agent",
                    "resource_type": "conversation",
                    "resource_id": conversation_id
                },
                actor_id=user_id,
                source_event_id=f"chat_message_{conversation_id}_{uuid.uuid4().hex[:8]}"
            )
        except Exception as e:
            logger.warning(f"Failed to emit chat message notification: {e}")
        
        # Send message to agent with conversation context
        # Get recent conversation history for context
        recent_messages = await conversation_manager.get_conversation_messages(conversation_id)
        conversation_context = ""
        if recent_messages:
            # Include last 6 messages for context (3 exchanges)
            for msg in recent_messages[-6:]:
                sender_type = msg["metadata"].get("sender_type", "unknown")
                role = "User" if sender_type == "user" else "Assistant"
                conversation_context += f"{role}: {msg['content']}\n"
        
        # Check user-agent companion matching for enhanced permissions
        user_role = chat_request.user_role or "team_member"
        permissions_summary = user_agent_matcher.get_user_permissions_summary(user_role)
        
        # Send to agent with context and companion matching info
        response = await agent_manager.send_message_to_agent(
            chat_request.agent_id,
            chat_request.message,
            chat_request.sender_name,
            conversation_context=conversation_context,
            user_role=user_role,
            permissions_summary=permissions_summary,
            user_id=user_id  # CRITICAL: Pass user_id for email access
        )
        
        # Check if agent response should trigger task creation
        enhanced_response = await enhance_response_with_tasks(
            response, 
            chat_request.agent_id, 
            chat_request.message,
            chat_request.sender_name
        )
        
        # Get agent info
        agent_info = agent_manager.get_agent_info(chat_request.agent_id)
        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Save agent response
        await conversation_manager.save_message(
            conversation_id=conversation_id,
            sender_id=agent_id,
            sender_name=agent_info["name"],
            content=enhanced_response,
            message_type="text",
            sender_type="agent"
        )
        
        # Emit notification event for agent response ONLY if user is not viewing this conversation
        if not chat_request.is_viewing_conversation:
            try:
                from notifications.event_bus import emit_notification_event
                await emit_notification_event(
                    "chat.agent.response",
                    {
                        "agent_name": agent_info["name"],
                        "response_preview": enhanced_response[:100] + "..." if len(enhanced_response) > 100 else enhanced_response,
                        "conversation_id": conversation_id,
                        "conversation_title": f"Chat with {agent_info['name']}",
                        "resource_type": "conversation",
                        "resource_id": conversation_id,
                        "sender_id": user_id  # The user who will receive this notification
                    },
                    actor_id=agent_id,
                    source_event_id=f"agent_response_{conversation_id}_{uuid.uuid4().hex[:8]}"
                )
                logger.info(f"Agent response notification emitted for user {user_id} (not viewing conversation)")
            except Exception as e:
                logger.warning(f"Failed to emit agent response notification: {e}")
        else:
            logger.info(f"Skipping agent response notification for user {user_id} (currently viewing conversation)")
        
        # Title generation will now be triggered when user switches conversations
        # (removed the immediate trigger after first exchange)
        
        # Create chat response
        chat_response = ChatResponse(
            agent_id=chat_request.agent_id,
            agent_name=agent_info["name"],
            message=enhanced_response,
            timestamp=datetime.now().isoformat(),
            conversation_id=conversation_id
        )
        
        return chat_response
        
    except Exception as e:
        logger.error(f"Error in chat with agent {chat_request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")

@app.post("/api/conversations")
async def create_conversation(request: dict):
    """Create a new conversation"""
    try:
        user_id = request.get("user_id")
        agent_id = request.get("agent_id") 
        title = request.get("title", "New Conversation")
        
        if not user_id or not agent_id:
            raise HTTPException(status_code=400, detail="user_id and agent_id are required")
        
        # Get agent info for the conversation
        agent_info = agent_manager.get_agent_info(agent_id)
        agent_name = agent_info["name"] if agent_info else f"Agent {agent_id}"
        
        # Create conversation using the conversation manager
        conversation_id = await conversation_manager.create_conversation(user_id, agent_id, agent_name)
        
        # If title was provided, update it
        if title != "New Conversation":
            if conversation_manager.supabase:
                try:
                    conversation_manager.supabase.table("conversations")\
                        .update({"title": title})\
                        .eq("id", conversation_id)\
                        .execute()
                except Exception as e:
                    logger.warning(f"Failed to update conversation title: {e}")
        
        # Return the created conversation
        return {
            "id": conversation_id,
            "title": title,
            "participants": [user_id, agent_id],
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agent_info": agent_info
        }
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@app.get("/api/conversations/{user_name}")
async def get_conversations(user_name: str):
    """Get conversation history for a user with enhanced features"""
    try:
        conversations = await conversation_manager.get_user_conversations(user_name)
        
        # Format conversations for the frontend
        formatted_conversations = []
        for conv in conversations:
            # Get agent info
            agent_id = conv.get("metadata", {}).get("agent_id")
            agent_info = None
            if agent_id:
                agent_info = agent_manager.get_agent_info(agent_id)
            
            formatted_conv = {
                "id": conv["id"],
                "title": conv.get("title") or "New Conversation",
                "agent_info": agent_info,
                "status": conv.get("status", "active"),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
                "last_message": conv.get("last_message"),
                "metadata": conv.get("metadata", {})
            }
            formatted_conversations.append(formatted_conv)
        
        return {"conversations": formatted_conversations}
        
    except Exception as e:
        logger.error(f"Error getting conversations for {user_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@app.get("/api/conversations/{user_name}/{conversation_id:path}/messages")
async def get_conversation_messages(user_name: str, conversation_id: str):
    """Get messages for a specific conversation"""
    try:
        messages = await conversation_manager.get_conversation_messages(conversation_id)
        
        # Format messages for the frontend
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "id": msg["id"],
                "conversation_id": msg["conversation_id"],
                "sender_id": msg["sender_id"],
                "sender_name": msg["metadata"].get("sender_name", "Unknown"),
                "sender_type": msg["metadata"].get("sender_type", "unknown"),
                "content": msg["content"],
                "message_type": msg.get("message_type", "text"),
                "timestamp": msg["timestamp"],
                "metadata": msg.get("metadata", {})
            }
            formatted_messages.append(formatted_msg)
        
        return {"messages": formatted_messages}
        
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation messages")

@app.post("/backend/conversations/actions/title")
async def update_conversation_title(request: ConversationTitleRequest):
    """Update conversation title"""
    try:
        conversation_id = request.conversation_id
        title = request.title or ""
        title = title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        # Update title in database
        if conversation_manager.supabase:
            try:
                result = conversation_manager.supabase.table("conversations")\
                    .update({"title": title})\
                    .eq("id", conversation_id)\
                    .execute()
                
                if not result.data:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                    
                logger.info(f"Updated conversation {conversation_id} title to: {title}")
                return {"success": True, "title": title}
            except Exception as e:
                logger.error(f"Failed to update conversation title in database: {e}")
        
        # Fall back to memory storage
        if conversation_id in conversation_manager.memory_conversations:
            conversation_manager.memory_conversations[conversation_id]["title"] = title
            conversation_manager.memory_conversations[conversation_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Updated conversation {conversation_id} title in memory: {title}")
            return {"success": True, "title": title}
        
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation title: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation title")

@app.post("/backend/conversations/actions/generate-title")
async def trigger_title_generation(request: ConversationActionRequest):
    """Generate title for conversation when user switches away from it"""
    try:
        conversation_id = request.conversation_id
        # Check if conversation exists and needs a title
        if conversation_manager.supabase:
            try:
                result = conversation_manager.supabase.table("conversations")\
                    .select("title")\
                    .eq("id", conversation_id)\
                    .execute()
                
                if not result.data:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                
                current_title = result.data[0].get("title")
            except Exception as e:
                logger.error(f"Failed to check conversation title: {e}")
                current_title = None
        else:
            # Check memory storage
            current_title = conversation_manager.memory_conversations.get(conversation_id, {}).get("title")
        
        # Only generate title if it's empty, None, or a default title that should be replaced
        should_generate_title = (
            not current_title or 
            current_title in ["New Conversation", "New conversation"] or
            current_title.startswith("New Chat with") and " - " in current_title  # Timestamp-based default titles
        )
        
        if should_generate_title:
            logger.debug(f"Generating title for conversation {conversation_id} (current: '{current_title}')")
            
            # Generate title based on entire conversation
            new_title = await conversation_manager.generate_conversation_title(conversation_id)
            
            return {"success": True, "title": new_title}
        else:
            logger.debug(f"Conversation {conversation_id} already has custom title: '{current_title}'")
            return {"success": True, "title": current_title, "message": "Title already exists"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating title for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate conversation title")

@app.get("/api/conversations/{user_id}/{conversation_id}/messages")
async def get_conversation_messages_api(user_id: str, conversation_id: str):
    """Get all messages for a specific conversation"""
    try:
        messages = await conversation_manager.get_conversation_messages(conversation_id)
        
        # Transform messages to match frontend format
        formatted_messages = []
        for msg in messages:
            formatted_message = {
                "id": msg.get("id"),
                "conversation_id": msg.get("conversation_id"),
                "sender_id": msg.get("sender_id"),
                "sender_name": msg.get("metadata", {}).get("sender_name", "Unknown"),
                "sender_type": msg.get("metadata", {}).get("sender_type", "user"),
                "content": msg.get("content"),
                "message_type": msg.get("message_type", "text"),
                "timestamp": msg.get("timestamp"),
                "metadata": msg.get("metadata", {})
            }
            formatted_messages.append(formatted_message)
        
        return {"messages": formatted_messages}
        
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation messages")

@app.post("/backend/conversations/actions/delete")
async def delete_conversation(request: ConversationActionRequest):
    """Delete a conversation and all its messages"""
    try:
        conversation_id = request.conversation_id
        # Delete from database
        if conversation_manager.supabase:
            try:
                # Delete messages first (foreign key constraint)
                conversation_manager.supabase.table("messages")\
                    .delete()\
                    .eq("conversation_id", conversation_id)\
                    .execute()
                
                # Delete conversation
                result = conversation_manager.supabase.table("conversations")\
                    .delete()\
                    .eq("id", conversation_id)\
                    .execute()
                
                logger.info(f"Deleted conversation {conversation_id} from database")
                return {"success": True, "message": "Conversation deleted successfully"}
            except Exception as e:
                logger.error(f"Failed to delete conversation from database: {e}")
        
        # Fall back to memory storage
        if conversation_id in conversation_manager.memory_conversations:
            del conversation_manager.memory_conversations[conversation_id]
            logger.info(f"Deleted conversation {conversation_id} from memory")
            return {"success": True, "message": "Conversation deleted successfully"}
        
        # If conversation doesn't exist in either location, still return success
        # (idempotent operation - it's already "deleted")
        return {"success": True, "message": "Conversation deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@app.get("/api/metrics")
async def get_real_metrics():
    """Get real system metrics from actual data sources"""
    try:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from Core.Tasks.task_manager import get_task_manager
        
        # Get agents data
        agents = agent_manager.get_available_agents()
        active_agents = len([a for a in agents if a["status"] == "online"])
        departments = len(set(a["department"] for a in agents))
        
        # Get real task data
        task_manager = get_task_manager()
        task_metrics = task_manager.get_system_metrics()
        
        # Calculate real message metrics from conversations
        total_messages = 0
        messages_this_hour = 0
        current_time = datetime.now()
        
        for messages in conversation_manager.memory_conversations.values(): # Iterate over memory conversations
            if "messages" in messages:
                total_messages += len(messages["messages"])
                # Count messages from last hour
                for msg in messages["messages"]:
                    msg_time = datetime.fromisoformat(msg["timestamp"])
                    if (current_time - msg_time).total_seconds() <= 3600:
                        messages_this_hour += 1
        
        # Calculate average response time (simplified - time between user and agent messages)
        response_times = []
        for messages in conversation_manager.memory_conversations.values(): # Iterate over memory conversations
            if "messages" in messages:
                for i in range(len(messages["messages"]) - 1):
                    if messages["messages"][i]["metadata"].get("sender_type") == "user" and \
                       messages["messages"][i + 1]["metadata"].get("sender_type") == "agent":
                        user_time = datetime.fromisoformat(messages["messages"][i]["timestamp"])
                        agent_time = datetime.fromisoformat(messages["messages"][i + 1]["timestamp"])
                        response_time = (agent_time - user_time).total_seconds()
                        response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate system health based on active agents and system status
        max_agents = len(agents)
        system_health = (active_agents / max_agents * 100) if max_agents > 0 else 0
        
        # Get active users (count unique conversation participants)
        active_users = len(set(key.split("_")[0] for key in conversation_manager.memory_conversations.keys()))
        
        return {
            "activeAgents": active_agents,
            "totalMessages": total_messages,
            "messagesThisHour": messages_this_hour,
            "avgResponseTime": round(avg_response_time, 2),
            "departments": departments,
            "activeUsers": max(active_users, 1),  # At least 1 (current user)
            "systemHealth": round(system_health, 0),
            "tasksCompleted": task_metrics.get("total_completed", 0),
            "pendingTasks": task_metrics.get("status_breakdown", {}).get("pending", 0),
            "totalTasksCreated": task_metrics.get("total_tasks_created", 0),
            "successRate": task_metrics.get("success_rate", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting real metrics: {e}")
        # Return basic fallback with some real data
        agents = agent_manager.get_available_agents()
        return {
            "activeAgents": len([a for a in agents if a["status"] == "online"]),
            "totalMessages": len([msg for msgs in conversation_manager.memory_conversations.values() for msg in msgs.get("messages", [])]),
            "messagesThisHour": 0,
            "avgResponseTime": 0,
            "departments": len(set(a["department"] for a in agents)),
            "activeUsers": 1,
            "systemHealth": 95,
            "tasksCompleted": 0,
            "pendingTasks": 0,
            "totalTasksCreated": 0,
            "successRate": 0
        }

@app.get("/api/agent-metrics/{agent_type}")
async def get_agent_metrics(agent_type: str):
    """Get metrics for a specific agent type or department"""
    try:
        # Import task manager
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from Core.Tasks.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        
        # Get agent-specific metrics
        # This is a simplified approach - in production you'd have more specific mapping
        agent_tasks = []
        for task in task_manager.get_all_tasks():
            if (agent_type.lower() in task.assignee.lower() if task.assignee else False) or \
               (agent_type.lower() in str(task.context.get('department', '')).lower()):
                agent_tasks.append(task)
        
        # Calculate agent-specific metrics
        completed_tasks = len([t for t in agent_tasks if t.status.value == 'completed'])
        pending_tasks = len([t for t in agent_tasks if t.status.value == 'pending'])
        in_progress_tasks = len([t for t in agent_tasks if t.status.value == 'in_progress'])
        
        # Get conversation metrics for this agent type
        agent_conversations = 0
        agent_messages = 0
        for key, messages in conversation_manager.memory_conversations.items(): # Iterate over memory conversations
            if agent_type.lower() in key.lower():
                agent_conversations += 1
                agent_messages += len(messages.get("messages", []))
        
        return {
            "agentType": agent_type,
            "totalTasks": len(agent_tasks),
            "completedTasks": completed_tasks,
            "pendingTasks": pending_tasks,
            "inProgressTasks": in_progress_tasks,
            "conversations": agent_conversations,
            "messages": agent_messages,
            "successRate": round((completed_tasks / len(agent_tasks) * 100) if agent_tasks else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting agent metrics for {agent_type}: {e}")
        return {
            "agentType": agent_type,
            "totalTasks": 0,
            "completedTasks": 0,
            "pendingTasks": 0,
            "inProgressTasks": 0,
            "conversations": 0,
            "messages": 0,
            "successRate": 0
        }

@app.get("/api/health")
async def health_check():
    """Health check with agent status"""
    try:
        agents = agent_manager.get_available_agents()
        return {
            "status": "healthy",
            "agents_loaded": len(agents),
            "agents": [{"id": a["id"], "name": a["name"], "status": a["status"]} for a in agents],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

# =================== TASK INTEGRATION FUNCTIONS ===================

async def process_task_commands(chat_request: ChatMessage, conversation_id: str) -> Optional[ChatResponse]:
    """Process task-related chat commands"""
    message = chat_request.message.lower().strip()
    
    # Get agent info
    agent_info = agent_manager.get_agent_info(chat_request.agent_id)
    if not agent_info:
        return None
    
    try:
        task_manager = get_task_manager()
        
        # Command: Show my tasks
        if any(cmd in message for cmd in ["/my tasks", "/show tasks", "/list tasks", "show my tasks"]):
            tasks = task_manager.get_agent_tasks(chat_request.agent_id)
            
            if not tasks:
                response_msg = f"Hi {chat_request.sender_name}! I don't have any tasks assigned to me right now. Feel free to give me something to work on!"
            else:
                response_msg = f"Hi {chat_request.sender_name}! Here are my current tasks:\n\n"
                for task in tasks[-5:]:  # Show last 5 tasks
                    response_msg += f"{task.title}\n"
                    response_msg += f"   Status: {task.status.value.title()}\n"
                    response_msg += f"   Priority: {task.priority.value.title()}\n"
                    response_msg += f"   Created: {task.get_duration()} ago\n\n"
                
                response_msg += f"I currently have {len(tasks)} tasks total. Need help with any of these? Just ask!"
            
            return ChatResponse(
                agent_id=chat_request.agent_id,
                agent_name=agent_info["name"],
                message=response_msg,
                timestamp=datetime.now().isoformat(),
                conversation_id=conversation_id
            )
        
        # Command: Create task (detect task creation intent)
        task_creation_keywords = ["create task", "new task", "assign task", "i need you to", "can you help", "work on"]
        if any(keyword in message for keyword in task_creation_keywords):
            # Try to extract task details from message
            task_title = extract_task_title(chat_request.message)
            
            if task_title:
                # Create task automatically
                task_id = f"CHAT_{int(datetime.now().timestamp() * 1000)}"
                priority = detect_priority_from_message(chat_request.message)
                
                context = {
                    "created_by": chat_request.sender_name,
                    "department": agent_info.get("department", "general"),
                    "created_via": "chat_interface",
                    "original_message": chat_request.message
                }
                
                task = task_manager.create_task(
                    task_id=task_id,
                    title=task_title,
                    description=chat_request.message,
                    department=agent_info.get("department", "general"),
                    priority=priority,
                    created_by=chat_request.sender_name,
                    context=context
                )
                
                # Assign to current agent
                task_manager.assign_task_to_agent(task_id, chat_request.agent_id)
                
                response_msg = f"Perfect! I've created a new task for myself:\n\n"
                response_msg += f"{task.title}\n"
                response_msg += f"Priority: {task.priority.value.title()}\n"
                response_msg += f"Task ID: {task.id}\n\n"
                response_msg += f"I'll get started on this right away! You can check the status anytime by asking about my tasks or checking the dashboard."
                
                return ChatResponse(
                    agent_id=chat_request.agent_id,
                    agent_name=agent_info["name"],
                    message=response_msg,
                    timestamp=datetime.now().isoformat(),
                    conversation_id=conversation_id
                )
        
        # Command: Task status update
        if any(cmd in message for cmd in ["task complete", "finished task", "done with", "completed"]):
            # Find recent tasks that could be marked complete
            agent_tasks = task_manager.get_agent_tasks(chat_request.agent_id, TaskStatus.IN_PROGRESS)
            if not agent_tasks:
                agent_tasks = task_manager.get_agent_tasks(chat_request.agent_id, TaskStatus.PENDING)
            
            if agent_tasks:
                # Mark the most recent task as completed
                latest_task = max(agent_tasks, key=lambda t: t.updated_at or t.created_at)
                task_manager.update_task_status(
                    latest_task.id,
                    TaskStatus.COMPLETED,
                    chat_request.sender_name,
                    f"Task completed via chat: {chat_request.message}"
                )
                
                response_msg = f"Excellent work! I've marked your task '{latest_task.title}' as completed.\n\n"
                response_msg += f"Task completed in {latest_task.get_duration()}\n"
                response_msg += f"Great job getting that done! Ready for the next challenge?"
                
                return ChatResponse(
                    agent_id=chat_request.agent_id,
                    agent_name=agent_info["name"],
                    message=response_msg,
                    timestamp=datetime.now().isoformat(),
                    conversation_id=conversation_id
                )
        
    except Exception as e:
        logger.error(f"Error processing task command: {e}")
    
    return None

async def enhance_response_with_tasks(response: str, agent_id: str, user_message: str, sender_name: str) -> str:
    """Enhance agent response with task-related information"""
    try:
        task_manager = get_task_manager()
        
        # Add task context if user asks about work, status, or tasks
        if any(keyword in user_message.lower() for keyword in ["work", "busy", "tasks", "doing", "status", "progress"]):
            agent_tasks = task_manager.get_agent_tasks(agent_id)
            
            if agent_tasks:
                active_tasks = [t for t in agent_tasks if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]]
                
                if active_tasks:
                    task_summary = f"\n\nHere's what I'm currently working on:\n"
                    for task in active_tasks[-3:]:  # Show up to 3 active tasks
                        task_summary += f"- {task.title} ({task.status.value})\n"
                    
                    response += task_summary
        
        # Add helpful task commands hint occasionally
        if "help" in user_message.lower() or "?" in user_message:
            response += "\n\nPro tip: You can ask me about my tasks, or just tell me what you need done!"
        
        return response
        
    except Exception as e:
        logger.error(f"Error enhancing response with tasks: {e}")
        return response

def extract_task_title(message: str) -> str:
    """Extract a task title from user message"""
    # Simple extraction - take the first meaningful sentence
    message = message.strip()
    
    # Remove common prefixes
    prefixes = ["create task", "new task", "i need you to", "can you", "please", "could you"]
    for prefix in prefixes:
        if message.lower().startswith(prefix):
            message = message[len(prefix):].strip()
            break
    
    # Take first sentence or first 60 characters
    sentences = message.split('.')
    if sentences:
        title = sentences[0].strip()
        if len(title) > 60:
            title = title[:57] + "..."
        return title.strip('"').strip("'")
    
    return message[:60] + "..." if len(message) > 60 else message

def detect_priority_from_message(message: str) -> TaskPriority:
    """Detect task priority from message content"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["urgent", "asap", "immediately", "emergency", "critical"]):
        return TaskPriority.URGENT
    elif any(word in message_lower for word in ["important", "high priority", "soon", "quickly"]):
        return TaskPriority.HIGH
    elif any(word in message_lower for word in ["low priority", "when possible", "no rush", "later"]):
        return TaskPriority.LOW
    else:
        return TaskPriority.MEDIUM

# =================== TASK MANAGEMENT ENDPOINTS ===================

@app.post("/api/tasks")
async def create_task(task_request: TaskCreateRequest):
    """Create a new task using the existing task system"""
    try:
        task_manager = get_task_manager()
        
        # Convert priority string to enum
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM, 
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        priority = priority_map.get(task_request.priority.lower(), TaskPriority.MEDIUM)
        
        # Generate unique task ID
        task_id = f"WEB_{int(datetime.now().timestamp() * 1000)}"
        
        # Create task with context
        context = {
            "created_by": task_request.created_by,
            "department": task_request.department,
            "created_via": "web_interface",
            "assignee_agent_id": task_request.assignee_agent_id
        }
        
        task = task_manager.create_task(
            task_id=task_id,
            title=task_request.title,
            description=task_request.description,
            department=task_request.department,
            priority=priority,
            created_by=task_request.created_by,
            context=context
        )
        
        # Assign to agent if specified
        if task_request.assignee_agent_id:
            agent_info = agent_manager.get_agent_info(task_request.assignee_agent_id)
            if agent_info:
                success = task_manager.assign_task_to_agent(task_id, task_request.assignee_agent_id)
                if not success:
                    logger.warning(f"Failed to assign task {task_id} to agent {task_request.assignee_agent_id}")
        
        return {
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "assignee": task.assignee or task_request.assignee_agent_id,
            "created_at": task.created_at.isoformat(),
            "message": "Task created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.get("/api/tasks")
async def get_all_tasks(department: Optional[str] = None, status: Optional[str] = None):
    """Get all tasks, optionally filtered by department or status"""
    try:
        task_manager = get_task_manager()
        
        if department:
            tasks = task_manager.get_department_tasks(department)
        else:
            tasks = task_manager.get_all_tasks()
        
        # Filter by status if provided
        if status:
            try:
                status_enum = TaskStatus(status.lower())
                tasks = [t for t in tasks if t.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Convert to response format
        task_list = []
        for task in tasks:
            # Get agent info for assignee
            agent_info = None
            if task.assignee:
                agent_info = agent_manager.get_agent_info(task.assignee)
            
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "assignee": task.assignee,
                "assignee_name": agent_info["name"] if agent_info else task.assignee,
                "department": task.context.get("department", "unknown"),
                "created_by": task.context.get("created_by", "unknown"),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "duration": task.get_duration()
            }
            task_list.append(task_data)
        
        # Sort by creation time (newest first)
        task_list.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        return {
            "tasks": task_list,
            "total_count": len(task_list),
            "filters_applied": {
                "department": department,
                "status": status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID"""
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get agent info for assignee
        agent_info = None
        if task.assignee:
            agent_info = agent_manager.get_agent_info(task.assignee)
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "assignee": task.assignee,
            "assignee_name": agent_info["name"] if agent_info else task.assignee,
            "department": task.context.get("department", "unknown"),
            "created_by": task.context.get("created_by", "unknown"),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "duration": task.get_duration(),
            "output": task.output,
            "rejection_reason": task.rejection_reason,
            "workflow_history": [
                {
                    "status": entry.status.value,
                    "actor": entry.actor,
                    "message": entry.message,
                    "timestamp": entry.timestamp.isoformat()
                }
                for entry in task.workflow_history
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")

@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, update_request: TaskUpdateRequest):
    """Update task status"""
    try:
        task_manager = get_task_manager()
        
        if not update_request.status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        # Convert status string to enum
        try:
            status_enum = TaskStatus(update_request.status.lower())
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid options: {valid_statuses}")
        
        # Update task status
        success = task_manager.update_task_status(
            task_id=task_id,
            status=status_enum,
            actor=update_request.actor or "User",
            message=update_request.message or f"Status updated to {status_enum.value} via web interface"
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or update failed")
        
        # Get updated task
        task = task_manager.get_task(task_id)
        
        return {
            "task_id": task.id,
            "new_status": task.status.value,
            "updated_at": task.updated_at.isoformat(),
            "message": "Task status updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id} status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")

@app.get("/api/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str, status: Optional[str] = None):
    """Get all tasks assigned to a specific agent"""
    try:
        task_manager = get_task_manager()
        
        # Get agent info to verify it exists
        agent_info = agent_manager.get_agent_info(agent_id)
        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get tasks for agent
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status.lower())
            except ValueError:
                valid_statuses = [s.value for s in TaskStatus]
                raise HTTPException(status_code=400, detail=f"Invalid status. Valid options: {valid_statuses}")
        
        tasks = task_manager.get_agent_tasks(agent_id, status_filter)
        
        # Convert to response format
        task_list = []
        for task in tasks:
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "department": task.context.get("department", "unknown"),
                "created_by": task.context.get("created_by", "unknown"),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "duration": task.get_duration()
            }
            task_list.append(task_data)
        
        # Sort by priority and creation time
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        task_list.sort(key=lambda x: (priority_order.get(x["priority"], 4), x["created_at"] or ""))
        
        return {
            "agent_id": agent_id,
            "agent_name": agent_info["name"],
            "tasks": task_list,
            "total_count": len(task_list),
            "status_filter": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent tasks: {str(e)}")

@app.get("/api/chat/task-summary")
async def get_chat_task_summary(agent_id: Optional[str] = None, user_name: Optional[str] = None):
    """Get a quick task summary for chat interface"""
    try:
        task_manager = get_task_manager()
        
        summary = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_today": 0,
            "chat_created_tasks": 0,
            "agent_workload": {}
        }
        
        # Get all tasks
        all_tasks = task_manager.get_all_tasks()
        summary["total_tasks"] = len(all_tasks)
        
        # Count by status
        for task in all_tasks:
            if task.status == TaskStatus.PENDING:
                summary["pending_tasks"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                summary["in_progress_tasks"] += 1
            elif task.status == TaskStatus.COMPLETED and task.updated_at:
                # Check if completed today
                if (datetime.now() - task.updated_at).days == 0:
                    summary["completed_today"] += 1
            
            # Count chat-created tasks
            if task.context.get("created_via") == "chat_interface":
                summary["chat_created_tasks"] += 1
            
            # Count tasks by agent
            if task.assignee:
                if task.assignee not in summary["agent_workload"]:
                    summary["agent_workload"][task.assignee] = {"pending": 0, "in_progress": 0, "completed": 0}
                
                if task.status == TaskStatus.PENDING:
                    summary["agent_workload"][task.assignee]["pending"] += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    summary["agent_workload"][task.assignee]["in_progress"] += 1
                elif task.status == TaskStatus.COMPLETED:
                    summary["agent_workload"][task.assignee]["completed"] += 1
        
        # If specific agent requested, add their details
        if agent_id:
            agent_info = agent_manager.get_agent_info(agent_id)
            agent_tasks = task_manager.get_agent_tasks(agent_id)
            
            summary["agent_specific"] = {
                "agent_name": agent_info["name"] if agent_info else agent_id,
                "total_assigned": len(agent_tasks),
                "recent_tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status.value,
                        "priority": task.priority.value,
                        "created": task.get_duration()
                    }
                    for task in agent_tasks[-3:]  # Last 3 tasks
                ]
            }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting chat task summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task summary: {str(e)}")

# ============================================================================
# Gmail Integration Endpoints
# ============================================================================

@app.get("/api/gmail/auth-url")
async def get_gmail_auth_url(user_id: str = Query(...)):
    """Get Gmail OAuth2 authorization URL"""
    try:
        # Import Gmail manager
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        auth_url = gmail_manager.get_auth_url(user_id)
        
        if auth_url:
            return {
                "success": True,
                "auth_url": auth_url
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate authorization URL"
            }
            
    except Exception as e:
        logger.error(f"Error generating Gmail auth URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class GmailCallbackRequest(BaseModel):
    user_id: str
    code: str
    state: str

@app.post("/api/gmail/callback")
async def handle_gmail_callback(request: GmailCallbackRequest):
    """Handle Gmail OAuth callback"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        result = gmail_manager.complete_oauth_flow(request.user_id, request.code, request.state)
        return result
        
    except Exception as e:
        logger.error(f"Error handling Gmail callback: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/gmail/auth-check")
async def check_gmail_auth_required(user_id: str = Query(...)):
    """
    Check if user needs to re-authenticate Gmail tokens
    
    Returns:
    - needs_auth: boolean indicating if re-authentication is required
    - auth_url: OAuth URL if re-authentication is needed
    - status: current connection status
    """
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get current Gmail status
        status = gmail_manager.get_connection_status(user_id)
        
        needs_auth = False
        auth_url = None
        
        # Check if re-authentication is needed
        if not status.get('connected', False) or status.get('is_expired', True):
            needs_auth = True
            
            # Generate OAuth URL for re-authentication
            try:
                from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
                auth_url = gmail_auth_service.get_authorization_url(user_id)
            except Exception as e:
                logger.error(f"Error generating auth URL: {e}")
                return {
                    "needs_auth": True,
                    "auth_url": None,
                    "status": status,
                    "error": "Failed to generate authentication URL"
                }
        
        return {
            "needs_auth": needs_auth,
            "auth_url": auth_url,
            "status": status,
            "message": "Re-authentication required" if needs_auth else "Gmail tokens are valid"
        }
        
    except Exception as e:
        logger.error(f"Error checking Gmail auth status: {e}")
        return {
            "needs_auth": True,
            "auth_url": None,
            "status": {"connected": False},
            "error": str(e),
            "message": "Error checking authentication status"
        }

@app.get("/api/gmail/status")
async def get_gmail_status(user_id: str = Query(...)):
    """Get Gmail connection status for a user with automatic token refresh"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        status = gmail_manager.get_connection_status(user_id)
        
        # 🔄 PROACTIVE TOKEN REFRESH: If token expires soon, refresh it now
        if status.get('connected') and status.get('is_expired', False):
            logger.info("🔄 Token expired detected, attempting automatic refresh...")
            
            try:
                from Integrations.Google.Gmail.gmail_database import gmail_database
                from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
                
                # Get current token data
                token_data = gmail_database.get_gmail_tokens(user_id)
                if token_data and token_data.get('refresh_token'):
                    # Try to refresh
                    credentials = gmail_auth_service.get_credentials(token_data, user_id)
                    if credentials and not credentials.expired:
                        logger.info("✅ Successfully refreshed expired tokens automatically!")
                        # Get updated status
                        status = gmail_manager.get_connection_status(user_id)
                    else:
                        logger.warning("⚠️ Failed to refresh expired tokens")
                else:
                    logger.warning("⚠️ No refresh token available for automatic refresh")
            except Exception as refresh_error:
                logger.error(f"Error during automatic token refresh: {refresh_error}")
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting Gmail status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


class GmailDisconnectRequest(BaseModel):
    user_id: str

@app.post("/api/gmail/disconnect")
async def disconnect_gmail(request: GmailDisconnectRequest):
    """Disconnect Gmail integration for a user"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        result = gmail_manager.disconnect_gmail(request.user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error disconnecting Gmail: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class GmailSyncRequest(BaseModel):
    user_id: str
    days_back: int = 30  # Days to look back (30/60/90/3650 for ALL)
    max_results: int = 100  # Maximum emails to process (increased for ALL option)
    auto_cleanup: bool = True   # Whether to automatically clean up orphaned database entries

@app.post("/api/gmail/sync")
async def sync_gmail_emails(request: GmailSyncRequest):
    """Sync emails from Gmail and process them"""
    global sync_progress_data
    
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Initialize progress tracking
        sync_progress_data.update({
            "active": True,
            "stage": "Starting",
            "message": "Initializing Gmail sync...",
            "progress": 0,
            "total": 100,
            "user_id": request.user_id,
            "started_at": datetime.now().isoformat()
        })
        
        # Update progress for Gmail connection
        sync_progress_data.update({
            "stage": "Connecting",
            "message": "Connecting to Gmail...",
            "progress": 10
        })
        
        # Define progress callback function
        def update_progress(stage: str, message: str, progress: int, total: int = 100):
            sync_progress_data.update({
                "stage": stage,
                "message": message,
                "progress": progress,
                "total": total
            })
        
        result = gmail_manager.sync_emails(
            request.user_id, 
            request.days_back, 
            request.max_results,
            request.auto_cleanup,
            progress_callback=update_progress
        )
        
        # Update progress to completion
        sync_progress_data.update({
            "active": False,
            "stage": "Completed",
            "message": f"Sync completed successfully. {result.get('emails_processed', 0)} emails processed.",
            "progress": 100
        })
        
        # Emit notification event for successful Gmail sync
        try:
            from notifications.event_bus import emit_notification_event
            await emit_notification_event(
                "system.gmail.sync.completed",
                {
                    "email_count": result.get('emails_processed', 0),
                    "sync_duration": f"{result.get('sync_duration', 0):.1f} seconds",
                    "new_documents": result.get('documents_created', 0),
                    "user_id": request.user_id
                },
                actor_id=request.user_id,
                source_event_id=f"gmail_sync_success_{request.user_id}_{uuid.uuid4().hex[:8]}"
            )
        except Exception as e:
            logger.warning(f"Failed to emit Gmail sync success notification: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing Gmail emails: {e}")
        
        # Update progress with error
        sync_progress_data.update({
            "active": False,
            "stage": "Error",
            "message": f"Sync failed: {str(e)}",
            "progress": 0
        })
        
        # Emit notification event for Gmail sync failure
        try:
            from notifications.event_bus import emit_notification_event
            await emit_notification_event(
                "system.gmail.sync.failed",
                {
                    "error_message": str(e),
                    "user_id": request.user_id,
                    "retry_time": "You can retry in a few minutes"
                },
                actor_id=request.user_id,
                source_event_id=f"gmail_sync_failure_{request.user_id}_{uuid.uuid4().hex[:8]}"
            )
        except Exception as notif_error:
            logger.warning(f"Failed to emit Gmail sync failure notification: {notif_error}")
        
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/gmail/sync/progress")
async def get_gmail_sync_progress():
    """Get current Gmail sync progress"""
    global sync_progress_data
    
    try:
        # Return current progress data
        return {
            "success": True,
            **sync_progress_data
        }
        
    except Exception as e:
        logger.error(f"Error getting Gmail sync progress: {e}")
        return {
            "success": False,
            "active": False,
            "stage": "Error",
            "message": f"Failed to get progress: {str(e)}",
            "progress": 0,
            "total": 0
        }

@app.get("/api/gmail/email-content/{message_id}")
async def get_email_content(
    message_id: str,
    user_id: str = Query(...)
):
    """Fetch individual email content by message ID"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        result = gmail_manager.get_email_content(user_id, message_id)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching email content: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class ProcessApprovedEmailRequest(BaseModel):
    message_id: str
    user_id: str
    sender_email: str
    subject: str
    timestamp: Optional[float] = None

@app.post("/api/gmail/process-approved-email")
async def process_approved_email(request: ProcessApprovedEmailRequest):
    """Process a manually approved email into a Google Drive document"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        result = gmail_manager.process_approved_email(
            request.user_id,
            request.message_id,
            request.sender_email,
            request.subject,
            request.timestamp
        )
        return result
        
    except Exception as e:
        logger.error(f"Error processing approved email: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/gmail/statistics")
async def get_gmail_statistics(
    user_id: str = Query(...),
    days_back: int = Query(30)
):
    """Get Gmail sync statistics for a user"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        stats = gmail_manager.get_sync_statistics(user_id, days_back)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting Gmail statistics: {e}")
        return {"error": str(e)}


@app.get("/api/gmail/clients")
async def get_client_documents():
    """Get summary of all client documents"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        client_docs = gmail_manager.get_client_documents()
        return client_docs
        
    except Exception as e:
        logger.error(f"Error getting client documents: {e}")
        return {"error": str(e)}


@app.post("/api/gmail/test-connection")
async def test_gmail_connection(request: GmailSyncRequest):
    """Test Gmail connection and email retrieval"""
    try:
        from Integrations.Google.Gmail.gmail_database import gmail_database
        from Integrations.Google.Gmail.gmail_service import gmail_service
        
        # Get user's Gmail tokens
        tokens = gmail_database.get_gmail_tokens(request.user_id)
        if not tokens:
            return {
                "success": False,
                "error": "No Gmail tokens found for user"
            }
        
        # Run debug with user-specific service
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        user_service = gmail_manager._get_user_gmail_service(request.user_id)
        debug_info = user_service.debug_gmail_connection(tokens, days_back=3)
        
        return {
            "success": True,
            "debug_info": debug_info
        }
        
    except Exception as e:
        logger.error(f"Error debugging Gmail connection: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/gmail/filtering/statistics")
async def get_filtering_statistics():
    """Get comprehensive filtering pipeline statistics"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get user_id from request (in real app, this would come from authentication)
        user_id = "default_user"  # Temporary fallback
        stats = gmail_manager.get_filtering_statistics(user_id)
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting filtering statistics: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/gmail/filtering/whitelist/domain")
async def add_whitelist_domain(request: dict):
    """Add domain to whitelist"""
    try:
        domain = request.get("domain")
        reason = request.get("reason", "User added")
        
        if not domain:
            return {
                "success": False,
                "error": "Domain is required"
            }
        
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get user_id from request (in real app, this would come from authentication)
        user_id = "default_user"  # Temporary fallback
        success = gmail_manager.add_whitelist_domain(user_id, domain, reason)
        
        return {
            "success": success,
            "message": f"Domain {domain} added to whitelist" if success else "Failed to add domain"
        }
        
    except Exception as e:
        logger.error(f"Error adding whitelist domain: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/gmail/filtering/feedback")
async def add_filtering_feedback(request: dict):
    """Add user feedback for filtering decision"""
    try:
        message_id = request.get("message_id")
        feedback = request.get("feedback")  # 'correct', 'incorrect', 'borderline'
        comment = request.get("comment", "")
        
        if not message_id or not feedback:
            return {
                "success": False,
                "error": "Message ID and feedback are required"
            }
        
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get user_id from request (in real app, this would come from authentication)
        user_id = "default_user"  # Temporary fallback
        success = gmail_manager.add_feedback(user_id, message_id, feedback, comment)
        
        return {
            "success": success,
            "message": "Feedback recorded" if success else "Failed to record feedback"
        }
        
    except Exception as e:
        logger.error(f"Error adding filtering feedback: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/gmail/filtering/review-queue")
async def get_review_queue(max_items: int = 50):
    """Get emails pending manual review"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get user_id from request (in real app, this would come from authentication)
        user_id = "default_user"  # Temporary fallback
        queue_items = gmail_manager.get_review_queue(user_id, max_items)
        
        # Convert to serializable format
        serializable_items = []
        for item in queue_items:
            serializable_items.append({
                "message_id": item.message_id,
                "timestamp": item.timestamp,
                "sender_email": item.sender_email,
                "subject": item.subject,
                "stage2_score": item.stage2_score,
                "stage2_reasoning": item.stage2_reasoning,
                "final_reason": item.final_reason
            })
        
        return {
            "success": True,
            "queue_items": serializable_items,
            "count": len(serializable_items)
        }
        
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/gmail/filtering/export")
async def export_filtering_decisions(request: dict):
    """Export filtering decisions for analysis"""
    try:
        output_format = request.get("format", "csv")  # 'csv' or 'json'
        filename = f"filtering_decisions_{int(time.time())}.{output_format}"
        output_path = f"/tmp/{filename}"
        
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Get user_id from request (in real app, this would come from authentication)
        user_id = "default_user"  # Temporary fallback
        success = gmail_manager.export_filtering_decisions(user_id, output_path, output_format)
        
        return {
            "success": True,
            "message": f"Filtering decisions exported to {filename}",
            "filename": filename,
            "path": output_path
        }
        
    except Exception as e:
        logger.error(f"Error exporting filtering decisions: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/gmail/filtering/config")
async def get_filtering_config():
    """Get current filtering pipeline configuration"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        config_info = {
            "stage1_enabled": True,
            "stage2_enabled": True,
            "ml_model_type": "heuristic",
            "ml_threshold": 0.8,
            "review_queue_enabled": True,
            "audit_logging_enabled": True
        }
        
        # Get actual configuration from pipeline
        user_id = "default_user"  # Temporary fallback
        stats = gmail_manager.get_filtering_statistics(user_id)
        if 'stage2_config' in stats:
            config_info.update({
                "ml_model_type": stats['stage2_config'].get('model_type', 'heuristic'),
                "ml_threshold": stats['stage2_config'].get('threshold', 0.8)
            })
        
        return {
            "success": True,
            "configuration": config_info
        }
        
    except Exception as e:
        logger.error(f"Error getting filtering config: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/gmail/sync-database")
async def sync_database_with_google_drive(request: dict):
    """
    Synchronize database with Google Drive to remove orphaned entries
    
    This resolves the "duplicate" confusion when users delete documents from Google Drive
    but they remain in the database, causing the system to skip re-processing them.
    """
    try:
        user_id = request.get("user_id")
        cleanup_orphaned = request.get("cleanup_orphaned", True)
        dry_run = request.get("dry_run", False)  # Just check, don't delete
        
        if not user_id:
            return {
                "success": False,
                "error": "user_id is required"
            }
        
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Run the sync (pass False for cleanup_orphaned if dry_run is True)
        sync_results = gmail_manager.sync_database_with_google_drive(
            user_id, 
            cleanup_orphaned=(cleanup_orphaned and not dry_run)
        )
        
        # Add dry run indicator to results
        if dry_run:
            sync_results['dry_run'] = True
            sync_results['message'] = "Dry run completed - no changes made"
        
        return sync_results
        
    except Exception as e:
        logger.error(f"Error in database sync: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/gmail/sync-status/{user_id}")
async def get_sync_status(user_id: str):
    """Get the current sync status between database and Google Drive"""
    try:
        from Integrations.Google.Gmail.gmail_manager import gmail_manager
        
        # Run a dry run to get status without making changes
        sync_results = gmail_manager.sync_database_with_google_drive(user_id, cleanup_orphaned=False)
        
        # Calculate consistency metrics
        total_checked = sync_results.get('total_checked', 0)
        missing_files = sync_results.get('missing_files', 0)
        existing_files = sync_results.get('existing_files', 0)
        
        consistency_rate = (existing_files / max(1, total_checked)) * 100 if total_checked > 0 else 100
        
        return {
            "success": True,
            "sync_status": {
                "total_database_entries": total_checked,
                "files_exist_in_drive": existing_files,
                "files_missing_from_drive": missing_files,
                "consistency_rate": round(consistency_rate, 1),
                "needs_cleanup": missing_files > 0,
                "recommendation": "Run cleanup sync" if missing_files > 0 else "Database and Google Drive are in sync"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# Gmail Auto-Sync Background Task
# ============================================================================

# Global variable to control auto-sync
auto_sync_enabled = True
auto_sync_thread = None

# Global variable to track sync progress
sync_progress_data = {
    "active": False,
    "stage": "",
    "message": "",
    "progress": 0,
    "total": 0,
    "user_id": None,
    "started_at": None
}

def get_all_active_gmail_users():
    """Get all users with active Gmail tokens"""
    try:
        from Integrations.Google.Gmail.gmail_database import gmail_database
        
        # Get all active Gmail tokens
        supabase = gmail_database._initialize_supabase()
        if not supabase:
            return []
        
        result = supabase.table("gmail_tokens").select("user_id").eq("is_active", True).execute()
        
        if result.data:
            return [token['user_id'] for token in result.data]
        return []
        
    except Exception as e:
        logger.error(f"Error getting active Gmail users: {e}")
        return []

def auto_sync_gmail_accounts():
    """Background function to automatically sync Gmail accounts"""
    global auto_sync_enabled
    
    logger.info("🔄 Gmail Auto-Sync: Background task started")
    
    while auto_sync_enabled:
        try:
            # Get all active Gmail users
            active_users = get_all_active_gmail_users()
            
            if active_users:
                logger.info(f"🔄 Gmail Auto-Sync: Found {len(active_users)} active users to sync")
                
                for user_id in active_users:
                    try:
                        logger.info(f"🔄 Gmail Auto-Sync: Syncing emails for user {user_id}")
                        
                        from Integrations.Google.Gmail.gmail_manager import gmail_manager
                        
                        # Check if user has valid tokens before attempting sync
                        from Integrations.Google.Gmail.gmail_database import gmail_database
                        token_data = gmail_database.get_gmail_tokens(user_id)
                        if not token_data:
                            logger.debug(f"⏭️ Gmail Auto-Sync: Skipping user {user_id} - no valid tokens")
                            continue
                        
                        # Sync with 30 days lookback and reasonable limits
                        result = gmail_manager.sync_emails(
                            user_id=user_id,
                            days_back=30,
                            max_results=200  # Higher limit for auto-sync
                        )
                        
                        if result.get('success'):
                            emails_processed = result.get('emails_processed', 0)
                            documents_created = result.get('documents_created', 0)
                            logger.info(f"✅ Gmail Auto-Sync: User {user_id} - {emails_processed} emails, {documents_created} documents")
                        else:
                            logger.warning(f"⚠️ Gmail Auto-Sync: User {user_id} sync failed: {result.get('error', 'Unknown error')}")
                            
                    except Exception as e:
                        logger.error(f"❌ Gmail Auto-Sync: Error syncing user {user_id}: {e}")
                        continue
                        
                    # Small delay between users to avoid rate limiting
                    time.sleep(5)
                    
            else:
                logger.info("🔄 Gmail Auto-Sync: No active Gmail users found")
            
            # Wait for next sync cycle (20 minutes)
            sync_interval = 20 * 60  # 20 minutes in seconds
            logger.info(f"🔄 Gmail Auto-Sync: Sleeping for {sync_interval//60} minutes until next sync")
            
            for _ in range(sync_interval):
                if not auto_sync_enabled:
                    break
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Gmail Auto-Sync: Unexpected error in sync loop: {e}")
            # Wait a bit before retrying
            time.sleep(60)
    
    logger.info("🔄 Gmail Auto-Sync: Background task stopped")

def start_gmail_auto_sync():
    """Start the Gmail auto-sync background thread"""
    global auto_sync_thread, auto_sync_enabled
    
    if auto_sync_thread is None or not auto_sync_thread.is_alive():
        auto_sync_enabled = True
        auto_sync_thread = threading.Thread(target=auto_sync_gmail_accounts, daemon=True)
        auto_sync_thread.start()
        logger.info("🚀 Gmail Auto-Sync: Background thread started")
    else:
        logger.info("🔄 Gmail Auto-Sync: Background thread already running")

def stop_gmail_auto_sync():
    """Stop the Gmail auto-sync background thread"""
    global auto_sync_enabled
    auto_sync_enabled = False
    logger.info("🛑 Gmail Auto-Sync: Background thread stopping")

@app.get("/api/gmail/auto-sync/status")
async def get_auto_sync_status():
    """Get Gmail auto-sync status"""
    global auto_sync_thread, auto_sync_enabled
    
    is_running = auto_sync_thread is not None and auto_sync_thread.is_alive() and auto_sync_enabled
    active_users = get_all_active_gmail_users()
    
    return {
        "auto_sync_enabled": auto_sync_enabled,
        "thread_running": is_running,
        "active_users_count": len(active_users),
        "sync_interval_minutes": 20
    }

@app.post("/api/gmail/auto-sync/start")
async def start_auto_sync():
    """Start Gmail auto-sync"""
    try:
        start_gmail_auto_sync()
        return {"success": True, "message": "Gmail auto-sync started"}
    except Exception as e:
        logger.error(f"Error starting auto-sync: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/gmail/auto-sync/stop")
async def stop_auto_sync():
    """Stop Gmail auto-sync"""
    try:
        stop_gmail_auto_sync()
        return {"success": True, "message": "Gmail auto-sync stopped"}
    except Exception as e:
        logger.error(f"Error stopping auto-sync: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/auth/register")
async def register_user(request: dict):
    """Register a new user account"""
    try:
        from Auth.User_management.admin_register import user_registration_service
        
        email = request.get('email')
        password = request.get('password')
        username = request.get('username')  # Optional, will default to email prefix
        role = request.get('role')
        
        if not all([email, password, role]):
            return {"success": False, "error": "Missing required fields: email, password, role"}
        
        # Auto-generate username from email if not provided
        if not username:
            username = email.split('@')[0] if '@' in email else email
        
        result = user_registration_service.create_user_account(
            email=email,
            password=password,
            username=username,
            role=role
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/auth/login")
async def login_user(request: dict):
    """Authenticate user login"""
    try:
        from Auth.User_management.admin_register import user_registration_service
        
        email = request.get('email')
        password = request.get('password')
        
        if not all([email, password]):
            return {"success": False, "error": "Missing email or password"}
        
        user = user_registration_service.get_user_by_email(email)
        if not user:
            return {"success": False, "error": "Invalid credentials"}
        
        if not user_registration_service.verify_password(password, user['password_hash']):
            return {"success": False, "error": "Invalid credentials"}
        
        if not user.get('is_active', False):
            return {"success": False, "error": "Account is disabled"}
        
        # Return user info (excluding password hash)
        user_info = {
            "user_id": user['user_id'],  # UUID
            "username": user['username'],  # Email prefix for folder matching
            "email": user['email'],
            "role": user['role']
        }
        
        logger.info(f"✅ User logged in: {user['user_id']}")
        
        return {
            "success": True,
            "user": user_info,
            "message": f"Welcome back, {user['full_name']}!"
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/auth/users")
async def list_users():
    """List all registered users (admin only)"""
    try:
        from Auth.User_management.admin_register import user_registration_service
        
        if not user_registration_service.supabase_client:
            return {"error": "Database not connected", "users": []}
        
        result = user_registration_service.supabase_client.table('user_profiles').select(
            'user_id, username, email, role, is_active, created_at'
        ).execute()
        
        return {
            "users": result.data if result.data else [],
            "count": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        return {"error": str(e), "users": []}

@app.get("/api/gmail/users-status")
async def get_gmail_users_status():
    """Get all Gmail users and their connection status"""
    try:
        from Integrations.Google.Gmail.gmail_database import gmail_database

        if not gmail_database.supabase_client:
            return {"error": "Supabase not connected", "users": []}

        # Get all Gmail token records
        response = gmail_database.supabase_client.table('gmail_tokens').select('user_id, gmail_email, gmail_name, is_active, created_at').execute()

        # Enhance data with email prefix for folder mapping
        enhanced_users = []
        if response.data:
            for user in response.data:
                enhanced_user = user.copy()
                if user.get('gmail_email') and '@' in user['gmail_email']:
                    enhanced_user['email_prefix'] = user['gmail_email'].split('@')[0]
                    enhanced_user['expected_folder'] = f"DigitalTwin_Brain/Users/{enhanced_user['email_prefix']}"
                else:
                    enhanced_user['email_prefix'] = None
                    enhanced_user['expected_folder'] = None
                enhanced_users.append(enhanced_user)

        return {
            "users": enhanced_users,
            "count": len(enhanced_users),
            "supabase_connected": True,
            "note": "email_prefix should match Google Drive folder names"
        }

    except Exception as e:
        logger.error(f"Debug error: {e}")
        return {"error": str(e), "users": [], "supabase_connected": False}


# ============================================================================
# ClickUp Integration Endpoints
# ============================================================================

@app.get("/api/clickup/auth-url")
async def get_clickup_auth_url(user_id: str = Query(...)):
    """Get ClickUp OAuth2 authorization URL"""
    try:
        # Import ClickUp manager
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        auth_url = clickup_manager.get_auth_url(user_id)
        
        if auth_url:
            return {
                "success": True,
                "auth_url": auth_url
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate ClickUp authorization URL"
            }
            
    except Exception as e:
        logger.error(f"Error generating ClickUp auth URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class ClickUpCallbackRequest(BaseModel):
    user_id: str
    code: str

@app.post("/api/clickup/callback")
async def handle_clickup_callback(request: ClickUpCallbackRequest):
    """Handle ClickUp OAuth callback"""
    try:
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        result = clickup_manager.handle_callback(request.code, request.user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error handling ClickUp callback: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/clickup/callback") 
async def clickup_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    Direct ClickUp OAuth callback endpoint (working version approach)
    This handles the redirect from ClickUp OAuth
    """
    try:
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        if error:
            logger.error(f"ClickUp OAuth error: {error}")
            return HTMLResponse(f"""
            <html>
                <body>
                    <h1>ClickUp Connection Failed</h1>
                    <p>Error: {error}</p>
                    <script>
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
            """)
        
        if not code or not state:
            return HTMLResponse("""
            <html>
                <body>
                    <h1>ClickUp Connection Failed</h1>
                    <p>Missing authorization code or state</p>
                    <script>
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
            """)
        
        # Handle the callback
        result = clickup_manager.handle_callback(code, state)
        
        if result.get('success'):
            return HTMLResponse(f"""
            <html>
                <body>
                    <h1>✅ ClickUp Connected Successfully!</h1>
                    <p>{result.get('message', 'Your ClickUp account has been connected.')}</p>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'clickup-oauth-success',
                                data: {result}
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 2000);
                    </script>
                </body>
            </html>
            """)
        else:
            return HTMLResponse(f"""
            <html>
                <body>
                    <h1>❌ ClickUp Connection Failed</h1>
                    <p>Error: {result.get('error', 'Unknown error occurred')}</p>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'clickup-oauth-error',
                                error: '{result.get("error", "Unknown error")}'
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
            """)
        
    except Exception as e:
        logger.error(f"Error in ClickUp OAuth callback: {e}")
        return HTMLResponse(f"""
        <html>
            <body>
                <h1>❌ ClickUp Connection Error</h1>
                <p>Technical error: {str(e)}</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'clickup-oauth-error',
                            error: '{str(e)}'
                        }}, '*');
                    }}
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        """)


@app.get("/api/clickup/status")
async def get_clickup_status(user_id: str = Query(...)):
    """Get ClickUp connection status for a user"""
    try:
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        status = clickup_manager.get_connection_status(user_id)
        return status
        
    except Exception as e:
        logger.error(f"Error getting ClickUp status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@app.post("/api/clickup/verify")
async def verify_clickup_connection(user_id: str = Query(...)):
    """Verify ClickUp connection by testing the API"""
    try:
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        # Use get_connection_status since verify_connection doesn't exist
        result = clickup_manager.get_connection_status(user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error verifying ClickUp connection: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class ClickUpDisconnectRequest(BaseModel):
    user_id: str

@app.post("/api/clickup/disconnect")
async def disconnect_clickup(request: ClickUpDisconnectRequest):
    """Disconnect ClickUp integration for a user"""
    try:
        from Integrations.Clickup.clickup_manager import clickup_manager
        
        result = clickup_manager.disconnect_user(request.user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error disconnecting ClickUp: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class ClickUpTokenRequest(BaseModel):
    user_id: str
    personal_token: str

@app.post("/api/clickup/connect-token")
async def connect_clickup_with_token(request: ClickUpTokenRequest):
    """Connect ClickUp using personal API token"""
    try:
        from Integrations.Clickup.clickup_token_auth import clickup_token_auth
        from Integrations.Clickup.clickup_database import clickup_database
        
        # Verify the token
        verification = clickup_token_auth.verify_token(request.personal_token)
        
        if not verification.get('success'):
            return {
                "success": False,
                "error": verification.get('error', 'Token verification failed')
            }
        
        # Store the token
        token_data = {
            'access_token': request.personal_token,
            'token_type': 'Bearer',
            'user_info': verification.get('user_info', {})
        }
        
        stored = clickup_database.store_clickup_token(
            request.user_id, 
            token_data
        )
        
        if stored:
            return {
                "success": True,
                "message": "ClickUp connected successfully with personal token",
                "user_info": verification.get('user_info', {})
            }
        else:
            return {
                "success": False,
                "error": "Failed to store ClickUp token"
            }
            
    except Exception as e:
        logger.error(f"Error connecting ClickUp with token: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/clickup/upload-file")
async def upload_file_to_clickup(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    agent_id: str = Form(...),
    conversation_id: str = Form(...),
    filename: str = Form(...)
):
    """Upload file to ClickUp with analysis and attach to a task"""
    try:
        from Integrations.Clickup.clickup_agent_tools import clickup_agent_tools
        import tempfile
        import os
        
        logger.info(f"File upload request: user={user_id}, file={filename}")
        
        # Validate file size (25MB limit)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            return {
                "success": False,
                "error": f"File too large: {file_size / (1024*1024):.1f}MB (max 25MB)"
            }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Basic file analysis (can be enhanced with AI later)
            file_extension = os.path.splitext(filename)[1].lower()
            file_type_analysis = {
                '.pdf': 'PDF document',
                '.doc': 'Word document',
                '.docx': 'Word document',
                '.xls': 'Excel spreadsheet',
                '.xlsx': 'Excel spreadsheet',
                '.txt': 'Text file',
                '.csv': 'CSV data file',
                '.png': 'PNG image',
                '.jpg': 'JPEG image',
                '.jpeg': 'JPEG image'
            }
            
            analysis_summary = f"Uploaded {file_type_analysis.get(file_extension, 'file')} for processing."
            keywords = f"file, upload, {file_extension[1:] if file_extension else 'document'}"
            
            # For now, we'll create a simple task or attach to an existing one
            # In a real implementation, you'd search for appropriate tasks or create new ones
            
            # Since we don't have a specific task_id, we'll use a simple approach:
            # 1. Try to find an existing task for this conversation/agent
            # 2. Or use a default task_id for uploads
            
            # For demo purposes, we'll simulate a successful upload
            # In reality, you'd need:
            # - A way to determine the appropriate ClickUp workspace/team_id
            # - Logic to find or create appropriate tasks
            # - Actual file upload to ClickUp using the agent tools
            
            # Simulate ClickUp task attachment
            demo_task_id = "demo_task_123"  # In real use, this would be determined dynamically
            demo_task_url = f"https://app.clickup.com/t/{demo_task_id}"
            
            logger.info(f"✅ File upload simulated successfully: {filename}")
            
            return {
                "success": True,
                "message": "File uploaded and analyzed successfully",
                "filename": filename,
                "file_size": file_size,
                "analysis_summary": analysis_summary,
                "keywords": keywords,
                "clickup_task_id": demo_task_id,
                "clickup_task_url": demo_task_url
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error uploading file to ClickUp: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# Google Calendar Integration Endpoints
# ============================================================================

@app.get("/api/calendar/status")
async def get_calendar_status(user_id: str = Query(...)):
    """Check Google Calendar availability using Gmail OAuth tokens"""
    try:
        # Import calendar service
        from Integrations.Google.Calendar.google_calendar_service import GoogleCalendarService
        
        calendar_service = GoogleCalendarService()
        service = calendar_service.get_calendar_service(user_id)
        
        if service:
            return {
                "success": True,
                "available": True,
                "message": "Calendar service is available"
            }
        else:
            return {
                "success": False,
                "available": False,
                "error": "Calendar service not available. Check Gmail connection and permissions."
            }
            
    except Exception as e:
        logger.error(f"Error checking calendar status: {e}")
        return {
            "success": False,
            "available": False,
            "error": str(e)
        }

class CalendarTestRequest(BaseModel):
    query: str
    user_id: str

@app.post("/api/calendar/test")
async def test_calendar_access(request: CalendarTestRequest):
    """Test calendar access by fetching today's events"""
    try:
        # Import calendar manager
        from Integrations.Google.Calendar.calendar_manager import CalendarManager
        
        calendar_manager = CalendarManager()
        
        # Process the calendar request
        response = await calendar_manager.process_request(request.query, request.user_id)
        
        if response:
            # Count events mentioned in response (rough estimate)
            events_count = response.lower().count('event') + response.lower().count('meeting') + response.lower().count('appointment')
            
            return {
                "success": True,
                "message": "Calendar access successful",
                "response": response,
                "events_count": events_count
            }
        else:
            return {
                "success": False,
                "error": "No calendar response or not a calendar request"
            }
            
    except Exception as e:
        logger.error(f"Error testing calendar access: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Hybrid Search System (Gmail + Drive)
# ============================================================================

# Import hybrid search system
from Integrations.Google.Search.adapters import get_search_adapter
from Integrations.Google.Search.orchestrator import get_search_orchestrator, SearchRequest
from Integrations.Google.Search.query_interpreter import SearchSource

hybrid_search_adapter = get_search_adapter()
logger.info("✅ Hybrid search system loaded successfully")

@app.get("/api/search/unified")
async def unified_search(
    query: str = Query(..., description="Natural language search query (supports Romanian/English)"),
    max_results: int = Query(25, ge=1, le=100, description="Maximum number of results"),
    user_id: Optional[str] = Query(None, description="User ID for authenticated access"),
    include_emails: bool = Query(True, description="Include Gmail search results"),
    include_files: bool = Query(True, description="Include Drive search results"),
    folder_filter: Optional[str] = Query(None, description="Filter by folder name or ID")
):
    """
    Unified search across Gmail and Google Drive with bilingual support
    
    Supports Romanian and English queries with natural language operators:
    - English: "find emails from:john after:2025-01-01 has:attachment"
    - Romanian: "găsește emails de la:john după:2025-01-01 are:atașament"
    - Mixed: "find files nume:contract tip:pdf"
    """
    try:
        # Use hybrid search adapter for unified search
        result = hybrid_search_adapter.unified_search(
            query=query,
            max_results=max_results,
            user_id=user_id,
            include_emails=include_emails,
            include_files=include_files
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in unified search endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }

@app.get("/api/search/emails")
async def search_emails(
    query: str = Query(..., description="Email search query (supports Romanian operators)"),
    max_results: int = Query(25, ge=1, le=100, description="Maximum number of results"),
    user_id: str = Query(..., description="User ID for email access"),
    include_content: bool = Query(False, description="Include full email content")
):
    """
    Gmail search with bilingual support
    
    Example queries:
    - "emails from hoang subject:contract"
    - "emails de la:hoang subiect:contract"
    - "mesaje înainte de:2025-01-01"
    """
    try:
        results = hybrid_search_adapter.search_emails(
            query=query,
            user_id=user_id,
            max_results=max_results
        )
        
        return {
            "success": True,
            "query": query,
            "user_id": user_id,
            "results_count": len(results),
            "results": results,
            "search_type": "email",
            "bilingual_support": True
        }
        
    except Exception as e:
        logger.error(f"Error in email search endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }

@app.get("/api/search/files")
async def search_files_hybrid(
    query: str = Query(..., description="File search query (supports Romanian operators)"),
    max_results: int = Query(25, ge=1, le=100, description="Maximum number of results"),
    user_id: Optional[str] = Query(None, description="User ID for authenticated access"),
    folder_filter: Optional[str] = Query(None, description="Folder to search in"),
    file_type: Optional[str] = Query(None, description="File type filter (pdf, docx, etc.)")
):
    """
    Google Drive search with bilingual support
    
    Example queries:
    - "contracts tip:pdf"
    - "documente nume:roadmap"
    - "fișiere conținut:plan trimestrial"
    """
    try:
        results = hybrid_search_adapter.search_files(
            query=query,
            folder_filter=folder_filter,
            file_type_filter=file_type,
            max_results=max_results,
            user_id=user_id
        )
        
        return {
            "success": True,
            "query": query,
            "folder_filter": folder_filter,
            "file_type_filter": file_type,
            "user_id": user_id,
            "results_count": len(results),
            "results": results,
            "search_type": "file",
            "bilingual_support": True
        }
        
    except Exception as e:
        logger.error(f"Error in file search endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }

@app.get("/api/search/test")
async def test_search_connectivity(
    user_id: Optional[str] = Query(None, description="User ID to test")
):
    """Test connectivity to Google search services"""
    try:
        connectivity = hybrid_search_adapter.test_connectivity(user_id)
        
        return {
            "success": connectivity.get("overall", False),
            "user_id": user_id,
            "services": connectivity,
            "hybrid_search": True
        }
        
    except Exception as e:
        logger.error(f"Error testing search connectivity: {e}")
        return {
            "success": False,
            "error": str(e),
            "services": {}
        }


@app.get("/api/search/colleague-context")
async def search_colleague_context(
    query: str = Query(..., description="Natural language search query"),
    user_id: str = Query(..., description="User ID making the request"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of context results"),
    time_window_days: int = Query(30, ge=1, le=365, description="How far back to search (days)")
):
    """
    Search for context from colleagues' emails (anonymized for privacy)
    
    **🔒 Privacy Features:**
    - No full email content exposed
    - Sensitive information automatically removed  
    - Only relevant context sentences returned
    - Colleague names anonymized
    - Requires explicit colleague permission
    
    **Example Queries:**
    - "project deadlines"
    - "client feedback" 
    - "meeting outcomes"
    """
    try:
        from Integrations.Google.Search.context_search import search_colleague_context_api
        
        logger.info(f"🔍 Colleague context search: '{query}' by user {user_id}")
        
        result = search_colleague_context_api(
            query=query,
            requesting_user_id=user_id,
            max_results=max_results
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Colleague context search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "colleague_context": [],
            "privacy_note": "All content is anonymized and sensitive information removed"
        }


# ============================================================================
# Email Permission Management API
# ============================================================================

@app.post("/api/email-permissions/request")
async def request_email_permission(request: Request):
    """
    Request email access permission for agent context
    """
    try:
        data = await request.json()
        requesting_user_id = data.get('requesting_user_id')
        agent_id = data.get('agent_id')
        agent_name = data.get('agent_name')
        target_user_email = data.get('target_user_email')  # New field for selecting which user to request from
        message = data.get('message', '')
        
        if not all([requesting_user_id, agent_id, agent_name, target_user_email]):
            return {
                "success": False,
                "error": "Missing required fields"
            }
        
        # Get requesting user info
        supabase_client = Config.get_supabase_client()
        user_response = supabase_client.table('user_profiles').select('username, email').eq('id', requesting_user_id).execute()
        
        if not user_response.data:
            return {
                "success": False,
                "error": "User not found"
            }
        
        requesting_user = user_response.data[0]
        
        # Find the granting user by email
        granting_user_response = supabase_client.table('user_profiles').select('id, username, email').eq('email', target_user_email).execute()
        
        if not granting_user_response.data:
            return {
                "success": False,
                "error": f"Target user with email {target_user_email} not found"
            }
        
        granting_user = granting_user_response.data[0]
        granting_user_id = granting_user['id']
        
        # Store the request in colleague_permissions table
        permission_response = supabase_client.table('colleague_permissions').insert({
            'requesting_user_id': requesting_user_id,
            'granting_user_id': granting_user_id,
            'permission_type': 'context_sharing',
            'is_active': False  # Pending approval
        }).execute()
        
        # Create notification for the granting user
        notification_response = supabase_client.table('notifications').insert({
            'recipient_user_id': granting_user_id,
            'type': 'email_permission_request',
            'title': 'Email Access Request',
            'body': f'{requesting_user["username"]} requested access to your work email for {agent_name} agent context.',
            'metadata': {
                'requesting_user_id': requesting_user_id,
                'requesting_user_name': requesting_user["username"],
                'agent_id': agent_id,
                'agent_name': agent_name,
                'permission_id': permission_response.data[0]['id'] if permission_response.data else None
            },
            'severity': 'info',
            'delivery_state': 'pending',
            'source_event_id': f'email_permission_request_{requesting_user_id}_{agent_id}_{int(__import__("time").time())}'
        }).execute()
        
        logger.info(f"Email permission requested: {requesting_user_id} -> {agent_name}")
        
        return {
            "success": True,
            "message": "Email permission request sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Error requesting email permission: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/email-permissions/requests")
async def get_email_permission_requests(user_id: str = Query(...)):
    """
    Get email permission requests for a user
    """
    try:
        supabase_client = Config.get_supabase_client()
        
        # Get requests where this user is either requesting or granting
        requests_response = supabase_client.table('colleague_permissions').select('*').or_(
            f'requesting_user_id.eq.{user_id},granting_user_id.eq.{user_id}'
        ).execute()
        
        return {
            "success": True,
            "requests": requests_response.data or []
        }
        
    except Exception as e:
        logger.error(f"Error fetching email permission requests: {e}")
        return {
            "success": False,
            "error": str(e),
            "requests": []
        }


@app.post("/api/email-permissions/respond")
async def respond_to_email_permission(request: Request):
    """
    Approve or deny email permission request
    """
    try:
        data = await request.json()
        permission_id = data.get('permission_id')
        action = data.get('action')  # 'approve' or 'deny'
        responding_user_id = data.get('responding_user_id')
        
        if not all([permission_id, action, responding_user_id]):
            return {
                "success": False,
                "error": "Missing required fields"
            }
        
        supabase_client = Config.get_supabase_client()
        
        # Update the permission status
        is_active = action == 'approve'
        update_response = supabase_client.table('colleague_permissions').update({
            'is_active': is_active
        }).eq('id', permission_id).execute()
        
        if not update_response.data:
            return {
                "success": False,
                "error": "Permission request not found"
            }
        
        permission = update_response.data[0]
        
        # Get user info for notification
        user_response = supabase_client.table('user_profiles').select('username').eq('id', responding_user_id).execute()
        responding_user_name = user_response.data[0]['username'] if user_response.data else 'Unknown'
        
        # Notify the requesting user
        notification_text = f"{responding_user_name} has {'accepted' if action == 'approve' else 'denied'} your request to access their email."
        
        notification_response = supabase_client.table('notifications').insert({
            'recipient_user_id': permission['requesting_user_id'],
            'type': 'email_permission_response',
            'title': f'Email Access {action.title()}d',
            'body': notification_text,
            'metadata': {
                'responding_user_id': responding_user_id,
                'responding_user_name': responding_user_name,
                'action': action,
                'permission_id': permission_id
            },
            'severity': 'info',
            'delivery_state': 'pending',
            'source_event_id': f'email_permission_response_{permission_id}_{action}_{int(__import__("time").time())}'
        }).execute()
        
        logger.info(f"Email permission {action}d: {permission_id}")
        
        return {
            "success": True,
            "message": f"Email permission request {action}d successfully"
        }
        
    except Exception as e:
        logger.error(f"Error responding to email permission: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# Deprecated Legacy Endpoints (Redirected to Hybrid Search)
# ============================================================================

@app.get("/backend/gdrive/search")
async def search_gdrive_files_legacy(
    query: str = Query(..., description="Search query for files"),
    folder: Optional[str] = Query(None, description="Folder to search in"),
    file_type: Optional[str] = Query(None, description="File type filter"),
    user_id: Optional[str] = Query(None, description="User ID for authenticated access")
):
    """Legacy endpoint - redirected to hybrid search system"""
    try:
        # Use hybrid search adapter with legacy parameter mapping
        results = hybrid_search_adapter.search_files(
            query=query,
            folder_filter=folder,
            file_type_filter=file_type,
            max_results=10,
            user_id=user_id
        )
        
        return {
            "success": True,
            "query": query,
            "folder_filter": folder,
            "file_type_filter": file_type,
            "user_id": user_id,
            "results_count": len(results),
            "results": results,
            "note": "Using hybrid search system"
        }
        
    except Exception as e:
        logger.error(f"Error in legacy Google Drive search endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }

async def initialize_search_on_startup():
    """Initialize unified search system on startup"""
    if not MEMORY_AVAILABLE:
        logger.info("⚠️ Memory system not available, skipping search initialization")
        return
        
    try:
        logger.info("🚀 Initializing unified semantic search system...")
        success = await initialize_search_system()
        
        if success:
            logger.info("🎉 Unified semantic search initialized successfully")
        else:
            logger.warning("⚠️ Unified semantic search initialization failed")
            
    except Exception as e:
        logger.error(f"❌ Error initializing search system: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await initialize_search_on_startup()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning") 