#!/usr/bin/env python3

import os
import logging
import json
import httpx
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

# MCP FastMCP import
from mcp.server.fastmcp import FastMCP

# Optional: Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Setup Logging (Protocol Requirement) ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info('[Setup] Initializing AI Project Forge Context Server...')

# --- Standard Filenames and Directories ---
WORKFLOW_DIR_NAME = "workflow"
HISTORY_FILENAME = ".mcp_history.md"
CONTEXT_FILENAME = ".mcp_project_context.md"
SYSTEM_PROMPT_FILENAME = "prompt_implement_user_stories.md"

# --- Environment Variables (Protocol Requirement) ---
PROJECT_DIRECTORY = os.getenv("PROJECT_DIRECTORY")
SECRET_KEY = os.getenv("SECRET_KEY")
PROJECT_API_URL = os.getenv("PROJECT_API_URL", "https://www.tasksforge.ai/api/mcpproject")

logging.info(f'[Setup] Environment loaded - Project Dir: {PROJECT_DIRECTORY}')
logging.info(f'[Setup] API URL: {PROJECT_API_URL}')

# --- Initialize MCP Server (Protocol Requirement) ---
mcp = FastMCP("AI Project Forge Context Server")

# --- I/O & HELPER FUNCTIONS ---

def read_file_content(file_path: Path) -> str | None:
    """Safely reads content from a file. Returns content or None if not found."""
    try:
        if not file_path.is_file():
            logging.error(f'[File] File not found: {file_path}')
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            logging.info(f'[File] Successfully read {len(content)} characters from {file_path}')
            return content
    except Exception as e:
        logging.error(f"[File] Failed to read file at {file_path}: {e}")
        return None

def write_file_content(file_path: Path, content: str, append: bool = False) -> bool:
    """
    Safely writes content to a file, creating parent directories if needed.
    """
    mode = "a" if append else "w"
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
        logging.info(f'[File] Successfully {"appended to" if append else "wrote"} {file_path}')
        return True
    except Exception as e:
        logging.error(f"[File] Failed to write to file at {file_path}: {e}")
        return False

def is_safe_project_path(dir_path_str: str) -> bool:
    """Performs security checks on the project directory path."""
    if not dir_path_str or ".." in dir_path_str:
        logging.error('[Security] Invalid project path: contains .. or is empty')
        return False
    try:
        project_path = Path(dir_path_str).resolve()
        if not project_path.is_dir():
            logging.error(f'[Security] Project path is not a directory: {project_path}')
            return False
        if not (project_path / ".git").is_dir():
            logging.error(f'[Security] Project path does not contain .git directory: {project_path}')
            return False
        logging.info(f'[Security] Project path validation passed: {project_path}')
        return True
    except Exception as e:
        logging.error(f'[Security] Project path validation failed: {e}')
        return False

def initialize_workflow_directory() -> Dict[str, Any]:
    """Initialize workflow directory and prompt file if needed."""
    logging.info("[Setup] Initializing workflow directory...")
    
    if not PROJECT_DIRECTORY or not is_safe_project_path(PROJECT_DIRECTORY):
        return {
            "success": False,
            "error": "PROJECT_DIRECTORY is invalid or not set",
            "project_directory": PROJECT_DIRECTORY
        }

    # Define the destination path for the prompt in the user's project
    project_path = Path(PROJECT_DIRECTORY).resolve()
    workflow_dir = project_path / WORKFLOW_DIR_NAME
    prompt_dest_path = workflow_dir / SYSTEM_PROMPT_FILENAME
    
    # Create workflow directory
    workflow_dir.mkdir(exist_ok=True)
    
    # Check if the prompt already exists to avoid overwriting
    if prompt_dest_path.exists():
        logging.info(f"[Setup] Workflow prompt already exists at {prompt_dest_path}")
        return {
            "success": True,
            "message": "Workflow directory already initialized",
            "prompt_path": str(prompt_dest_path.relative_to(project_path)),
            "project_directory": PROJECT_DIRECTORY
        }
    else:
        # Define the source path of the master prompt (relative to this server.py file)
        master_prompt_path = Path(__file__).parent / SYSTEM_PROMPT_FILENAME
        master_prompt_content = read_file_content(master_prompt_path)
        
        if master_prompt_content:
            if write_file_content(prompt_dest_path, master_prompt_content):
                logging.info(f"[Setup] Successfully created default prompt at {prompt_dest_path}")
                return {
                    "success": True,
                    "message": "Workflow directory initialized with default prompt",
                    "prompt_path": str(prompt_dest_path.relative_to(project_path)),
                    "project_directory": PROJECT_DIRECTORY
                }
            else:
                logging.error(f"[Setup] Failed to write prompt file to {prompt_dest_path}")
                return {
                    "success": False,
                    "error": "Failed to write prompt file",
                    "project_directory": PROJECT_DIRECTORY
                }
        else:
            logging.error(f"[Setup] Master prompt file could not be read: {master_prompt_path}")
            return {
                "success": False,
                "error": f"Master prompt file not found: {master_prompt_path}",
                "project_directory": PROJECT_DIRECTORY
            }

def save_project_context(project_context: str) -> str:
    """
    Saves the project context to a standard file in the project's workflow directory.
    
    Args:
        project_context: The project context content to save
    
    Returns:
        JSON string with operation status
    """
    logging.info("[Tool:save_project_context] Called.")
    
    if not project_context or not project_context.strip():
        error_msg = "Project context cannot be empty"
        logging.error(f'[Tool:save_project_context] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg
        })
    
    if not PROJECT_DIRECTORY or not is_safe_project_path(PROJECT_DIRECTORY):
        error_msg = "Project directory is invalid or not set"
        logging.error(f'[Tool:save_project_context] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_directory": PROJECT_DIRECTORY
        })

    project_path = Path(PROJECT_DIRECTORY).resolve()
    context_file_path = project_path / WORKFLOW_DIR_NAME / CONTEXT_FILENAME
    
    if write_file_content(context_file_path, project_context):
        success_msg = f"Project context saved to {context_file_path.relative_to(project_path)}"
        logging.info(f'[Tool:save_project_context] {success_msg}')
        return json.dumps({
            "success": True,
            "message": success_msg,
            "file_path": str(context_file_path.relative_to(project_path)),
            "content_length": len(project_context)
        })
    else:
        error_msg = "Failed to save the project context"
        logging.error(f'[Tool:save_project_context] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "file_path": str(context_file_path.relative_to(project_path))
        })

# --- MODULE-LEVEL INITIALIZATION ---
# This runs when the module is imported, which happens with `uv run mcp dev`
def _perform_module_initialization():
    """Initialize workflow directory when module is imported (for MCP dev server)"""
    try:
        logging.info("[Module Init] Performing module-level initialization...")
        init_result = initialize_workflow_directory()
        logging.info(f"[Module Init] Initialization result: {json.dumps(init_result, indent=2)}")
        
        if init_result["success"]:
            logging.info("[Module Init] ✅ Workflow initialization completed successfully")
        else:
            logging.error(f"[Module Init] ❌ Workflow initialization failed: {init_result.get('error', 'Unknown error')}")
    except Exception as e:
        logging.error(f"[Module Init] Exception during module initialization: {e}")
        import traceback
        logging.error(f"[Module Init] Full traceback: {traceback.format_exc()}")

# --- MCP TOOLS (Protocol Compliant) ---

@mcp.tool()
async def get_project_context(project_id: int) -> str:
    """
    Fetches project details from the remote API and saves it locally.
    
    Args:
        project_id: The ID of the project to fetch from the API
    
    Returns:
        JSON string with project context and operation status
    """
    logging.info(f"[Tool:get_project_context] Called for Project ID: {project_id}")
    
    # Validate environment variables
    if not SECRET_KEY:
        error_msg = "SECRET_KEY environment variable is not set"
        logging.error(f'[Tool:get_project_context] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_id": project_id
        })
    
    if not PROJECT_API_URL:
        error_msg = "PROJECT_API_URL environment variable is not set"
        logging.error(f'[Tool:get_project_context] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_id": project_id
        })

    # Fetch project data from API
    api_endpoint = f"{PROJECT_API_URL}/{project_id}"
    headers = {"Content-Type": "application/json", "sessionKey": SECRET_KEY}
    
    try:
        logging.info(f'[API] Making request to: {api_endpoint}')
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_endpoint, headers=headers)
            response.raise_for_status()
            project_data = response.json()
        
        logging.info(f"[API] Successfully fetched data for project '{project_data.get('name', 'Unknown')}'")
        
    except httpx.TimeoutException:
        error_msg = f"API request timed out for project {project_id}"
        logging.error(f'[API] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_id": project_id
        })
    except httpx.HTTPStatusError as e:
        error_msg = f"API returned status {e.response.status_code}: {e.response.text}"
        logging.error(f'[API] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_id": project_id,
            "status_code": e.response.status_code
        })
    except Exception as e:
        error_msg = f"Failed to fetch project data: {str(e)}"
        logging.error(f'[API] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_id": project_id
        })

    # Format project context
    project_context = f"""# PROJECT CONTEXT

## Project Name
{project_data.get('name', 'N/A')}

## High-Level Description
{project_data.get('description', 'N/A')}

## Elaborated Description & Advice
{project_data.get('elaborated_description', 'N/A')}

## Key Features
{project_data.get('key_features', 'N/A')}

## Core Requirements
{project_data.get('elaborated_core_requirements', 'N/A')}

## User Stories
{project_data.get('elaborated_user_stories', 'N/A')}

 ## Schema Design (Markdown + SQL DDL)
{project_data.get('schema_design', 'N/A')}

## Webflow / UI Flow (Markdown + Mermaid + Wireframes)
{project_data.get('webflow_ui', 'N/A')}

## Detailed Task List
```json
{json.dumps(project_data.get('tasks_list', []), indent=2)}
```
"""

    # Save project context locally
    save_result = save_project_context(project_context)
    
    return json.dumps({
        "success": True,
        "project_id": project_id,
        "project_name": project_data.get('name', 'Unknown'),
        "project_context": project_context,
        "save_status": save_result,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    })

@mcp.tool()
def log_task_completion(completion_report: str) -> str:
    """
    Appends a timestamped completion report to the history file.
    
    Args:
        completion_report: The task completion report to log
    
    Returns:
        JSON string with operation status
    """
    logging.info("[Tool:log_task_completion] Called.")
    
    if not completion_report or not completion_report.strip():
        error_msg = "Completion report cannot be empty"
        logging.error(f'[Tool:log_task_completion] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg
        })
    
    if not PROJECT_DIRECTORY or not is_safe_project_path(PROJECT_DIRECTORY):
        error_msg = "Project directory is invalid or not set"
        logging.error(f'[Tool:log_task_completion] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "project_directory": PROJECT_DIRECTORY
        })

    project_path = Path(PROJECT_DIRECTORY).resolve()
    history_file_path = project_path / WORKFLOW_DIR_NAME / HISTORY_FILENAME
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    log_entry = f"\n\n---\n\n**Logged on:** {timestamp}\n\n{completion_report}"

    if write_file_content(history_file_path, log_entry, append=True):
        success_msg = f"Progress logged to {history_file_path.relative_to(project_path)}"
        logging.info(f'[Tool:log_task_completion] {success_msg}')
        return json.dumps({
            "success": True,
            "message": success_msg,
            "file_path": str(history_file_path.relative_to(project_path)),
            "logged_at": timestamp,
            "entry_length": len(log_entry)
        })
    else:
        error_msg = "Failed to save progress"
        logging.error(f'[Tool:log_task_completion] {error_msg}')
        return json.dumps({
            "success": False,
            "error": error_msg,
            "file_path": str(history_file_path.relative_to(project_path))
        })

# --- MODULE INITIALIZATION (Runs when imported by MCP dev server) ---
_perform_module_initialization()

# --- MAIN FUNCTION ---
async def main():
    """Main entry point (Protocol Compliant)"""

    try:
        logging.info("[Setup] AI Project Forge Context Server starting...")
        # Start the MCP server
        logging.info("[Setup] Starting MCP server on stdio...")
        await mcp.run()
        
    except KeyboardInterrupt:
        logging.info("[Setup] Server stopped by user")
    except Exception as error:
        logging.error(f"[Setup] Server error: {error}")
        raise

if __name__ == "__main__":
    asyncio.run(main())