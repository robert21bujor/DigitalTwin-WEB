"""
Logging utilities for the marketing system with department-specific logs
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Dict, Any, Optional


def setup_main_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Setup main system logging with cleaner console output"""
    
    if config is None:
        config = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "Logs/MarketingSystem.log",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5
        }
    
    # Ensure Logs directory exists
    os.makedirs("Logs", exist_ok=True)
    
    # Set root logger to WARNING to suppress noisy third-party INFO messages
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    
    # Clear any existing handlers from root logger
    root_logger.handlers.clear()
    
    # Console handler - only show WARNING and above for cleaner output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - capture everything at INFO level for debugging
    file_handler = logging.handlers.RotatingFileHandler(
        config["file"],
        maxBytes=config["max_bytes"],
        backupCount=config["backup_count"]
    )
    file_handler.setLevel(getattr(logging, config["level"]))
    file_formatter = logging.Formatter(config["format"])
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Create main marketing system logger with INFO level
    logger = logging.getLogger("marketing_system")
    logger.setLevel(getattr(logging, config["level"]))
    
    # Set our application loggers to INFO level with console output
    app_loggers = [
        "marketing_system",
        "company_system", 
        "agent",
        "manager", 
        "orchestrator",
        "task_manager",
        "auth",
        "chat"
    ]
    
    for logger_name in app_loggers:
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(logging.INFO)
        
        # Add dedicated console handler for our app loggers
        if not any(isinstance(h, logging.StreamHandler) for h in app_logger.handlers):
            app_console_handler = logging.StreamHandler()
            app_console_handler.setLevel(logging.INFO)
            app_console_formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
            app_console_handler.setFormatter(app_console_formatter)
            app_logger.addHandler(app_console_handler)
            app_logger.propagate = False  # Don't propagate to root logger
    
    # Explicitly suppress noisy third-party loggers
    noisy_loggers = [
        "httpx",
        "sentence_transformers", 
        "sentence_transformers.SentenceTransformer",
        "Memory.vector_store",
        "Memory.enhanced_memory",
        "semantic_kernel",
        "semantic_kernel.connectors.ai.open_ai.services.open_ai_handler",
        "urllib3",
        "requests"
    ]
    
    for logger_name in noisy_loggers:
        noisy_logger = logging.getLogger(logger_name)
        noisy_logger.setLevel(logging.WARNING)  # Only show warnings and errors
    
    # Set up Core loggers to use shorter names
    setup_core_loggers(config["level"])
    
    return logger


def setup_core_loggers(log_level: str = "INFO"):
    """Setup shorter logger names for Core modules to improve readability"""
    
    core_modules = [
        ("Core.Departments.company_system", "company_system"),
        ("Core.Agents.agent", "agent"),
        ("Core.Agents.manager", "manager"),
        ("Core.Tasks.orchestrator", "orchestrator"),
        ("Core.Tasks.task_manager", "task_manager"),
        ("Auth.Core.account_system", "auth"),
        ("Core.Interfaces.chat_interfaces", "chat")
    ]
    
    for full_name, short_name in core_modules:
        # Create logger with short name
        logger = logging.getLogger(short_name)
        logger.setLevel(getattr(logging, log_level))
        
        # Also create an alias for the full module name
        full_logger = logging.getLogger(full_name)
        full_logger.setLevel(getattr(logging, log_level))


def setup_department_logger(department_name: str) -> logging.Logger:
    """Setup department-specific logger"""
    
    # Ensure Logs directory exists
    os.makedirs("Logs", exist_ok=True)
    
    logger_name = f"{department_name.lower()}_department"
    log_file = f"Logs/{department_name}Logs.log"
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_department_logger(department_name: str) -> logging.Logger:
    """Get or create department logger"""
    logger_name = f"{department_name.lower()}_department"
    
    # Check if logger already exists
    if logger_name in logging.Logger.manager.loggerDict:
        return logging.getLogger(logger_name)
    else:
        return setup_department_logger(department_name)


def log_task_activity(department: str, task_id: str, activity: str, actor: str, details: str = ""):
    """Log task activity to department-specific log"""
    dept_logger = get_department_logger(department)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"TASK_ACTIVITY | {timestamp} | "
        f"Task: {task_id} | "
        f"Activity: {activity} | "
        f"Actor: {actor}"
    )
    
    if details:
        log_message += f" | Details: {details}"
    
    dept_logger.info(log_message)


def log_agent_work(department: str, agent_name: str, task_id: str, work_summary: str):
    """Log agent work completion to department log"""
    dept_logger = get_department_logger(department)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"AGENT_WORK | {timestamp} | "
        f"Agent: {agent_name} | "
        f"Task: {task_id} | "
        f"Work: {work_summary[:100]}..."  # First 100 chars
    )
    
    dept_logger.info(log_message)


def log_manager_review(department: str, manager_name: str, task_id: str, decision: str, reason: str = ""):
    """Log manager review to department log"""
    dept_logger = get_department_logger(department)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"MANAGER_REVIEW | {timestamp} | "
        f"Manager: {manager_name} | "
        f"Task: {task_id} | "
        f"Decision: {decision}"
    )
    
    if reason:
        log_message += f" | Reason: {reason}"
    
    dept_logger.info(log_message)


def log_human_verification(department: str, task_id: str, decision: str, reviewer: str = "Human"):
    """Log actual human verification decision to department log"""
    dept_logger = get_department_logger(department)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"HUMAN_VERIFICATION | {timestamp} | "
        f"Task: {task_id} | "
        f"Decision: {decision} | "
        f"Reviewer: {reviewer}"
    )
    
    dept_logger.info(log_message)





def log_task_creation(task_id: str, title: str, department: str, agent: str, manager: str, priority: str):
    """Log task creation with structured format"""
    logger = logging.getLogger("marketing_system")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"TASK_CREATED | {timestamp} | "
        f"ID: {task_id} | "
        f"Title: {title} | "
        f"Department: {department} | "
        f"Agent: {agent} | "
        f"Manager: {manager} | "
        f"Priority: {priority}"
    )
    
    logger.info(log_message)


def log_verification_step(task_id: str, step: str, actor: str, status: str, message: str = ""):
    """Log verification flow step"""
    logger = logging.getLogger("marketing_system")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"VERIFICATION | {timestamp} | "
        f"Task: {task_id} | "
        f"Step: {step} | "
        f"Actor: {actor} | "
        f"Status: {status}"
    )
    
    if message:
        log_message += f" | Message: {message}"
    
    logger.info(log_message) 