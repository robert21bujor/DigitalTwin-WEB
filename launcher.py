#!/usr/bin/env python3
"""
AI Multi-Agent Digital Twin System Launcher
==========================================

Launches the Full Web Interface directly:
- BusinessDev & Operations agent dashboard
- Integrated chat with AI agents
- Real-time collaboration features
- Modern web application with FastAPI backend and Next.js frontend
"""

import subprocess
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import resource cleanup to prevent semaphore leaks
try:
    from cleanup_resources import setup_cleanup_handlers, force_single_process_mode
    setup_cleanup_handlers()
    force_single_process_mode()
    logger.info("Resource cleanup handlers installed")
except ImportError:
    logger.warning("Resource cleanup not available")
except Exception as e:
    logger.warning(f"Resource cleanup setup failed: {e}")
import time
import asyncio
import json
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# Memory system imports
try:
    from Memory.memory_sync import GoogleDriveMemorySync
    from Utils.config import Config
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

class SystemLauncher:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.memory_sync_enabled = MEMORY_AVAILABLE and Config.is_memory_enabled() if MEMORY_AVAILABLE else False
    
    def check_dependencies(self):
        """Check if required dependencies are available"""
        try:
            # Check basic Python packages
            import semantic_kernel
            import asyncio
            logger.info("Core dependencies available")
            return True
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            logger.error("Please run: pip install -r requirements.txt")
            return False
    
    async def sync_agent_memories(self):
        """Sync agent memories with Google Drive"""
        if not self.memory_sync_enabled:
            logger.warning("Memory sync disabled or unavailable")
            return True
        
        try:
            logger.info("Syncing agent memories with Google Drive (using multi-user Gmail OAuth)...")
            
            # Get list of all users with Gmail tokens for memory sync
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            try:
                # Get all users who have connected Gmail
                connected_users = self._get_gmail_connected_users()
                
                if not connected_users:
                    logger.warning("No users have connected Gmail for agent memory sync")
                    logger.info("Agents will operate without Google Drive access until users connect Gmail")
                    logger.info("To enable agent Google Drive access:")
                    logger.info("1. Go to http://localhost:3001/dashboard/manager")
                    logger.info("2. Open Settings → Gmail Integration")
                    logger.info("3. Click 'Connect Gmail'")
                return True  # Don't fail startup, just skip sync
            
                logger.info(f"Found {len(connected_users)} user(s) with Gmail connected")
                logger.info(f"Users: {', '.join([user['gmail_email'] for user in connected_users])}")
                
                # Sync agent memories from all connected users
                successful_syncs = 0
                total_syncs = 0
                
                for user in connected_users:
                    try:
                        user_id = user['user_id']
                        gmail_email = user['gmail_email']
                        
                        logger.info(f"Syncing agent memories from {gmail_email}...")
                        
                        # Initialize memory sync with this user's Gmail OAuth
                        from Memory.memory_sync import GoogleDriveMemorySync
                        sync_manager = GoogleDriveMemorySync(user_id=user_id)
            
                        # Perform sync for this user
                        sync_result = await sync_manager.sync_with_google_drive(force_full_sync=False)
                        total_syncs += 1
            
                        if sync_result:
                            successful_syncs += 1
                            logger.info(f"Successfully synced memories from {gmail_email}")
                        else:
                            logger.warning(f"Issues syncing memories from {gmail_email}")
                            
                    except Exception as e:
                        logger.error(f"Failed to sync memories from {user.get('gmail_email', 'unknown')}: {e}")
                        total_syncs += 1
                
                # Report results
                if successful_syncs > 0:
                    logger.info(f"Agent memories synced successfully from {successful_syncs}/{total_syncs} users")
                    logger.info("Business Development and Operations agents now have access to documents")
                    logger.info("Agents can search across all connected users' Google Drives")
                else:
                    logger.warning("Memory sync completed with issues")
                    logger.warning("Please check individual user connections and logs")
                
            except Exception as e:
                logger.error(f"Memory sync failed: {e}")
                logger.info("System will continue without memory sync")
            
            return True
            
        except Exception as e:
            logger.error(f"Memory sync system failed: {e}")
            logger.info("System will continue without agent memory sync")
            return True  # Don't fail startup if memory sync fails
    
    def _get_gmail_connected_users(self):
        """Get all users who have connected Gmail and have valid tokens"""
        try:
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            if not gmail_database.supabase_client:
                return []
            
            # Query for all active Gmail tokens (only select existing columns)
            result = gmail_database.supabase_client.table("gmail_tokens").select(
                "user_id, gmail_email, is_active"
            ).eq("is_active", True).execute()
            
            if not result.data:
                return []
            
            connected_users = []
            for token_record in result.data:
                # Additional validation could be added here
                # (e.g., check if token is not expired, test API access)
                
                # Skip users without gmail_email (they exist but have None values)
                if token_record.get('gmail_email'):
                    connected_users.append({
                        'user_id': token_record['user_id'],
                        'gmail_email': token_record['gmail_email']
                    })
                else:
                    logger.warning(f"Skipping user {token_record.get('user_id')} - no gmail_email set")
            
            return connected_users
            
        except Exception as e:
            logger.error(f"Error getting connected users: {e}")
            return []
    
    def launch_web_interface(self):
        """Launch the full web interface with integrated simple chat"""
        logger.info("Starting Full Web Interface...")
        logger.info("This will start the complete web application with:")
        logger.info("- Integrated direct agent communication")
        logger.info("- AI agents with Azure OpenAI")
        logger.info("- FastAPI backend")
        logger.info("- Next.js frontend dashboard")
        logger.info("- Visual task management")
        logger.info("- BusinessDev & Operations focused dashboard")
        logger.info("Access points:")
        logger.info("Frontend: http://localhost:3001")
        logger.info("API: http://localhost:8000")
        logger.info("API Docs: http://localhost:8000/docs")
        
        # Sync agent memories before starting
        try:
            asyncio.run(self.sync_agent_memories())
        except Exception as e:
            logger.warning(f"Memory sync skipped: {e}")
        
        processes = []
        original_dir = os.getcwd()
        
        try:
            # Start backend API
            logger.info("Starting Backend API...")
            backend_path = self.project_root / "AgentUI" / "Backend"
            
            # Set environment variables to prevent macOS segmentation faults
            backend_env = os.environ.copy()
            backend_env.update({
                'MULTIPROCESSING_START_METHOD': 'spawn',
                'OMP_NUM_THREADS': '1',
                'MKL_NUM_THREADS': '1',
                'TOKENIZERS_PARALLELISM': 'false',
                'PYTHONMALLOC': 'malloc'
            })
            
            # Start backend with visible output for debugging
            backend_process = subprocess.Popen([
                sys.executable, "api.py"
            ], cwd=str(backend_path), env=backend_env)  # Pass fixed environment
            processes.append(("Backend API", backend_process))
            
            # Wait for backend to start and check if it's running
            logger.info("Waiting for backend to initialize...")
            for i in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                if backend_process.poll() is not None:
                    logger.error(f"Backend API failed to start (exit code: {backend_process.returncode})")
                    return
                    
                # Test if backend is responding
                try:
                    if requests:
                        response = requests.get("http://localhost:8000/api/health", timeout=1)
                        if response.status_code == 200:
                            logger.info("Backend API is responding!")
                            break
                except:
                    pass
                    
                if i == 9:
                    logger.warning("Backend API taking longer than expected to start...")
            
            # Start frontend
            logger.info("Starting Frontend...")
            # Use the correct npm command based on operating system
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            frontend_process = subprocess.Popen([
                npm_cmd, "run", "dev"
            ], cwd=str(self.project_root / "AgentUI"))  # Don't capture output initially  
            processes.append(("Frontend", frontend_process))
            
            # Wait a bit for frontend to start
            logger.info("Waiting for frontend to start...")
            time.sleep(5)
            
            logger.info("Full Web Interface started successfully!")
            logger.info("=" * 50)
            logger.info("📱 Open your browser and go to: http://localhost:3001")
            logger.info("💬 Integrated chat: Talk to any agent directly!")
            logger.info("📊 Dashboard: Visual task and performance management!")
            # This information is already logged above - no need to repeat here
            
            # Monitor processes and show their output
            while True:
                time.sleep(1)
                
                # Check if any process died
                for name, process in processes:
                    if process.poll() is not None:
                        logger.error(f"{name} stopped unexpectedly (exit code: {process.returncode})")
                        logger.info("Check the output above for error details")
                        return
                        
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
            for name, process in processes:
                logger.info(f"Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    logger.info(f"{name} stopped")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {name}...")
                    process.kill()
                    process.wait()
                    logger.info(f"{name} killed")
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")
            
            # Force cleanup multiprocessing resources
            try:
                from cleanup_resources import cleanup_all_resources
                cleanup_all_resources()
                logger.info("Resources cleaned up")
            except:
                pass
            logger.info("All services stopped successfully")
            
        except Exception as e:
            logger.error(f"Error launching web interface: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up any started processes
            logger.info("🧹 Cleaning up processes...")
            for name, process in processes:
                try:
                    logger.info(f"Terminating {name}...")
                    process.terminate()
                    process.wait(timeout=3)
                    logger.info(f"{name} terminated")
                except subprocess.TimeoutExpired:
                    try:
                        logger.warning(f"Force killing {name}...")
                        process.kill()
                        process.wait()
                        logger.info(f"{name} killed")
                    except Exception as e:
                        logger.warning(f"Could not kill {name}: {e}")
                except Exception as e:
                    logger.error(f"Error terminating {name}: {e}")
                        
        finally:
            # Comprehensive resource cleanup
            try:
                from cleanup_resources import cleanup_all_resources
                cleanup_all_resources()
            except:
                pass
            # Restore original directory
            os.chdir(original_dir)
    
    def run(self):
        """Main launcher - now directly launches web interface (option 3)"""
        if not self.check_dependencies():
            return
        
        logger.info("🚀 AI Multi-Agent Digital Twin System")
        logger.info("=" * 60)
        logger.info("🌐 Starting Full Web Interface directly...")
        
        try:
            self.launch_web_interface()
        except KeyboardInterrupt:
            logger.info("👋 Goodbye!")
        except Exception as e:
            logger.error(f"Error: {e}")

def main():
    """Entry point"""
    launcher = SystemLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 