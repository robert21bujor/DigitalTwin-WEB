"""
ClickUp Agent Tools
Provides semantic kernel functions for ClickUp integration
"""

import json
import logging
import os
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from semantic_kernel.functions import kernel_function

from .clickup_database import clickup_database

logger = logging.getLogger(__name__)


class ClickUpAgentTools:
    """ClickUp integration tools for AI agents"""
    
    def __init__(self):
        """Initialize ClickUp agent tools"""
        self.database = clickup_database
        self.base_url = "https://api.clickup.com/api/v2"
        logger.info("ClickUp Agent Tools initialized")
    
    def _get_headers(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get API headers with authentication for a user"""
        token_data = self.database.get_token(user_id)
        
        if not token_data or not token_data.get('access_token'):
            logger.error(f"No valid ClickUp token for user {user_id}")
            return None
            
        return {
            'Authorization': f"Bearer {token_data['access_token']}",
            'Content-Type': 'application/json'
        }
            
    def _make_api_request(self, endpoint: str, user_id: str, method: str = 'GET', 
                         data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request to ClickUp"""
        headers = self._get_headers(user_id)
        
        if not headers:
            return None
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning(f"ClickUp API authentication failed for user {user_id}")
                return None
            else:
                logger.error(f"ClickUp API request failed: {response.status_code} - {response.text}")
                return None
            
        except requests.RequestException as e:
            logger.error(f"Network error in ClickUp API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in ClickUp API request: {e}")
            return None
    
    @kernel_function(
        description="Get user's ClickUp teams and workspaces",
        name="get_clickup_teams"
    )
    def get_teams(self, user_id: str) -> str:
        """Get all ClickUp teams for the user"""
        
        try:
            result = self._make_api_request("team", user_id)
            
            if result and 'teams' in result:
                teams_info = []
                for team in result['teams']:
                    teams_info.append({
                        'id': team.get('id'),
                        'name': team.get('name'),
                        'color': team.get('color'),
                        'avatar': team.get('avatar'),
                        'members': len(team.get('members', []))
                    })
                
                return json.dumps({
                    "success": True,
                    "teams": teams_info,
                    "count": len(teams_info)
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to retrieve ClickUp teams",
                    "teams": []
                })
            
        except Exception as e:
            logger.error(f"Error getting ClickUp teams: {e}")
            return json.dumps({
                "success": False,
                "error": f"Error retrieving teams: {str(e)}",
                "teams": []
                        })
    
    @kernel_function(
        description="Get ClickUp connection status for a user",
        name="get_clickup_status"
    )
    def get_connection_status(self, user_id: str) -> str:
        """Get ClickUp connection status"""
        
        try:
            is_connected = self.database.is_user_connected(user_id)
            
            if is_connected:
                # Test API access
                result = self._make_api_request("user", user_id)
                
                if result and 'user' in result:
                    user_info = result['user']
                    return json.dumps({
                        "connected": True,
                        "status": "active",
                        "user": {
                            "id": user_info.get('id'),
                            "username": user_info.get('username'),
                            "email": user_info.get('email'),
                            "initials": user_info.get('initials')
                        },
                        "message": "ClickUp connection is active"
                    }, indent=2)
                else:
                    return json.dumps({
                        "connected": False,
                        "status": "authentication_failed",
                        "message": "ClickUp token appears invalid"
                    })
            else:
                return json.dumps({
                    "connected": False,
                    "status": "not_connected",
                    "message": "User has not connected ClickUp account"
                })
            
        except Exception as e:
            logger.error(f"Error checking ClickUp status: {e}")
            return json.dumps({
                "connected": False,
                "status": "error",
                "message": f"Error checking status: {str(e)}"
            })

    @kernel_function(
        description="Get all tasks assigned to or created by the user",
        name="get_my_tasks"
    )
    def get_my_tasks(self, user_id: str) -> str:
        """Get tasks for the current user"""
        
        try:
            # First get teams to find spaces/lists
            teams_result = self._make_api_request("team", user_id)
            if not teams_result or 'teams' not in teams_result:
                return json.dumps({
                    "success": False, 
                    "error": "Could not retrieve teams",
                    "tasks": []
                })

            all_tasks = []
            
            for team in teams_result['teams']:
                team_id = team.get('id')
                if team_id:
                    # Get spaces for this team
                    spaces_result = self._make_api_request(f"team/{team_id}/space", user_id)
                    if spaces_result and 'spaces' in spaces_result:
                        
                        for space in spaces_result['spaces']:
                            space_id = space.get('id')
                            if space_id:
                                # Get lists in this space
                                lists_result = self._make_api_request(f"space/{space_id}/list", user_id)
                                if lists_result and 'lists' in lists_result:
                                    
                                    for list_item in lists_result['lists']:
                                        list_id = list_item.get('id')
                                        if list_id:
                                            # Get tasks in this list
                                            # Get tasks with subtasks included  
                                            tasks_result = self._make_api_request(f"list/{list_id}/task?include_closed=true&subtasks=true", user_id)
                                            
                                            if tasks_result and 'tasks' in tasks_result:
                                                for task in tasks_result['tasks']:
                                                    # Skip if this is actually a subtask (has parent field)
                                                    if task.get('parent'):
                                                        continue
                                                        
                                                    # Check for subtasks in the task data
                                                    subtasks_count = 0
                                                    subtasks_info = []
                                                    
                                                    if 'subtasks' in task and task['subtasks']:
                                                        subtasks_count = len(task['subtasks'])
                                                        for subtask in task['subtasks']:
                                                            subtasks_info.append({
                                                                'id': subtask.get('id'),
                                                                'name': subtask.get('name'),
                                                                'status': subtask.get('status', {}).get('status', 'unknown'),
                                                                'url': subtask.get('url')
                                                            })
                                                    
                                                    # Also check if any tasks in the full list are subtasks of this task
                                                    if subtasks_count == 0:
                                                        current_task_id = task.get('id')
                                                        for potential_subtask in tasks_result['tasks']:
                                                            if potential_subtask.get('parent') == current_task_id:
                                                                subtasks_count += 1
                                                                subtasks_info.append({
                                                                    'id': potential_subtask.get('id'),
                                                                    'name': potential_subtask.get('name'),
                                                                    'status': potential_subtask.get('status', {}).get('status', 'unknown'),
                                                                    'url': potential_subtask.get('url')
                                                                })
                                                    
                                                    task_info = {
                                                        'id': task.get('id'),
                                                        'name': task.get('name'),
                                                        'description': task.get('description', ''),
                                                        'status': task.get('status', {}).get('status', 'unknown'),
                                                        'priority': task.get('priority'),
                                                        'assignees': [assignee.get('username') for assignee in task.get('assignees', [])],
                                                        'due_date': task.get('due_date'),
                                                        'url': task.get('url'),
                                                        'team': team.get('name'),
                                                        'space': space.get('name'),
                                                        'list': list_item.get('name'),
                                                        'subtasks_count': subtasks_count,
                                                        'subtasks': subtasks_info
                                                    }
                                                    all_tasks.append(task_info)

            return json.dumps({
                "success": True,
                "tasks": all_tasks,
                "count": len(all_tasks)
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting ClickUp tasks: {e}")
            return json.dumps({
                "success": False,
                "error": f"Error retrieving tasks: {str(e)}",
                "tasks": []
            })

    @kernel_function(
        description="Get detailed information about a specific task including subtasks and comments",
        name="get_task_details"
    )
    def get_task_details(self, user_id: str, task_id: str) -> str:
        """Get detailed information about a specific ClickUp task"""
        
        try:
            # Get basic task info
            task_result = self._make_api_request(f"task/{task_id}", user_id)
            
            if not task_result:
                return json.dumps({
                    "success": False,
                    "error": "Task not found or access denied"
                })
            
            # Get subtasks
            subtasks = []
            if 'subtasks' in task_result and task_result['subtasks']:
                for subtask in task_result['subtasks']:
                    subtasks.append({
                        'id': subtask.get('id'),
                        'name': subtask.get('name'),
                        'status': subtask.get('status', {}).get('status', 'unknown'),
                        'assignees': [assignee.get('username') for assignee in subtask.get('assignees', [])],
                        'url': subtask.get('url')
                    })
            
            # Get comments
            comments_result = self._make_api_request(f"task/{task_id}/comment", user_id)
            comments = []
            if comments_result and 'comments' in comments_result:
                for comment in comments_result['comments'][:5]:  # Last 5 comments
                    comments.append({
                        'id': comment.get('id'),
                        'comment': comment.get('comment_text', '')[:200],  # First 200 chars
                        'user': comment.get('user', {}).get('username', 'Unknown'),
                        'date': comment.get('date')
                    })
            
            # Get custom fields
            custom_fields = []
            if 'custom_fields' in task_result:
                for field in task_result['custom_fields']:
                    custom_fields.append({
                        'name': field.get('name'),
                        'value': field.get('value')
                    })
            
            task_details = {
                'success': True,
                'task': {
                    'id': task_result.get('id'),
                    'name': task_result.get('name'),
                    'description': task_result.get('description', ''),
                    'status': task_result.get('status', {}).get('status', 'unknown'),
                    'priority': task_result.get('priority'),
                    'assignees': [assignee.get('username') for assignee in task_result.get('assignees', [])],
                    'creator': task_result.get('creator', {}).get('username', 'Unknown'),
                    'created': task_result.get('date_created'),
                    'updated': task_result.get('date_updated'),
                    'due_date': task_result.get('due_date'),
                    'start_date': task_result.get('start_date'),
                    'time_estimate': task_result.get('time_estimate'),
                    'time_spent': task_result.get('time_spent'),
                    'url': task_result.get('url'),
                    'subtasks': subtasks,
                    'comments': comments,
                    'custom_fields': custom_fields,
                    'tags': [tag.get('name') for tag in task_result.get('tags', [])],
                    'watchers': [watcher.get('username') for watcher in task_result.get('watchers', [])]
                }
            }
            
            return json.dumps(task_details, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting task details: {e}")
            return json.dumps({
                "success": False,
                "error": f"Error retrieving task details: {str(e)}"
            })

    @kernel_function(
        description="Search for tasks in a specific project or space",
        name="search_tasks_in_project"
    )
    def search_tasks_in_project(self, user_id: str, project_name: str) -> str:
        """Search for tasks in a specific project/space"""
        
        try:
            # Get all tasks first
            all_tasks_result = self.get_my_tasks(user_id)
            all_tasks_data = json.loads(all_tasks_result)
            
            if not all_tasks_data.get("success"):
                return all_tasks_result
            
            # Filter by project/space/list name
            matching_tasks = []
            search_term = project_name.lower()
            
            for task in all_tasks_data["tasks"]:
                team_name = (task.get("team", "") or "").lower()
                space_name = (task.get("space", "") or "").lower() 
                list_name = (task.get("list", "") or "").lower()
                
                if (search_term in team_name or 
                    search_term in space_name or 
                    search_term in list_name):
                    matching_tasks.append(task)
            
            return json.dumps({
                "success": True,
                "project_name": project_name,
                "tasks": matching_tasks,
                "count": len(matching_tasks)
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error searching tasks in project: {e}")
            return json.dumps({
                "success": False,
                "error": f"Error searching tasks: {str(e)}"
            })


# Create singleton instance
clickup_agent_tools = ClickUpAgentTools()