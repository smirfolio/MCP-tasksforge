import os
import logging
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP

load_dotenv()

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('[Setup] Initializing server...')

# --- Standard Filenames and Directories ---
WORKFLOW_DIR_NAME = "workflow"
HISTORY_FILENAME = ".mcp_history.md"
CONTEXT_FILENAME = ".mcp_project_context.md"
SYSTEM_PROMPT_FILENAME = "prompt_implement_user_stories.md"

# --- I/O & HELPER FUNCTIONS ---

def read_file_content(file_path: Path) -> str | None:
    """Safely reads content from a file. Returns content or None if not found."""
    if not file_path.is_file():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read file at {file_path}: {e}")
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
        return True
    except Exception as e:
        logging.error(f"Failed to write to file at {file_path}: {e}")
        return False

def is_safe_project_path(dir_path_str: str) -> bool:
    """Performs security checks on the project directory path."""
    if not dir_path_str or ".." in dir_path_str: return False
    try:
        project_path = Path(dir_path_str).resolve()
        if not project_path.is_dir() or not (project_path / ".git").is_dir(): return False
    except Exception: return False
    return True

# --- SERVER LIFESPAN MANAGER ---
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """
    This function runs ONCE when the server starts up.
    It handles the automatic initialization of the workflow directory and prompt.
    """
    logging.info("[Lifespan] Server starting up. Running workflow initialization...")
    project_directory = os.getenv("PROJECT_DIRECTORY")

    if not project_directory or not is_safe_project_path(project_directory):
        logging.error("[Lifespan] Startup check failed: PROJECT_DIRECTORY is invalid or not set.")
    else:
        # Define the destination path for the prompt in the user's project
        prompt_dest_path = Path(project_directory).resolve() / WORKFLOW_DIR_NAME / SYSTEM_PROMPT_FILENAME
        
        # Check if the prompt already exists in the user's project to avoid overwriting it
        if prompt_dest_path.exists():
            logging.info(f"[Lifespan] Workflow prompt already exists at {prompt_dest_path}. Skipping setup.")
        else:
            # Define the source path of the master prompt (relative to this server.py file)
            master_prompt_path = Path(__file__).parent / SYSTEM_PROMPT_FILENAME
            master_prompt_content = read_file_content(master_prompt_path)
            
            if master_prompt_content:
                # Write the master prompt to the user's project workflow directory
                if write_file_content(prompt_dest_path, master_prompt_content):
                    logging.info(f"[Lifespan] Successfully created default prompt at {prompt_dest_path}.")
                else:
                    logging.error(f"[Lifespan] Failed to write prompt file to {prompt_dest_path}.")
            else:
                 logging.error(f"[Lifespan] CRITICAL: Master prompt file '{master_prompt_path}' could not be read.")
    
    # The 'yield' signals that startup is complete and the server can now accept tool calls.
    yield
    
    # Code after the yield would run on server shutdown.
    logging.info("[Lifespan] Server shutting down.")

# --- MCP INSTANCE WITH LIFESPAN ---
mcp = FastMCP("AI Project Forge Context Server", lifespan=server_lifespan)

# --- MCP Tools ---

@mcp.tool()
async def get_project_context(project_id: int) -> str:
    """
    Fetches project details from the remote API. Returns only the raw project context.
    The agent is responsible for saving it locally using 'save_project_context'.
    """
    logging.info(f"[Tool:get_project_context] Called for Project ID: {project_id}")
    
    secret_key = os.getenv("SECRET_KEY")
    PROJECT_API_URL = os.getenv("PROJECT_API_URL", "https://tasksforge.ai/api/mcpproject")

    if not secret_key or not PROJECT_API_URL:
        return "Error: Server is missing required environment variables (SECRET_KEY, PROJECT_API_URL)."
    
    api_endpoint = f"{PROJECT_API_URL}/{project_id}"
    headers = {"Content-Type": "application/json", "sessionKey": secret_key}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_endpoint, headers=headers)
            response.raise_for_status()
            project_data = response.json()
        logging.info(f"[API] Successfully fetched data for project '{project_data.get('name')}'")
    except httpx.RequestError as e:
        return f"Error: Could not retrieve project data from API: {e}"

    return f"""
# PROJECT CONTEXT

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
## Detailed Task List
```json
{json.dumps(project_data.get('tasks_list', []), indent=2)}
```
"""

@mcp.tool()
def save_project_context(project_context: str) -> str:
    """Saves the project context to a standard file in the project's workflow directory."""
    logging.info("[Tool:save_project_context] Called.")
    project_directory = os.getenv("PROJECT_DIRECTORY")

    if not project_directory or not is_safe_project_path(project_directory):
        return "Error: Cannot save context. The project_directory is invalid or not set."

    context_file_path = Path(project_directory).resolve() / WORKFLOW_DIR_NAME / CONTEXT_FILENAME
    
    if write_file_content(context_file_path, project_context):
        return f"Success: Project context saved locally to {context_file_path.relative_to(project_directory)}."
    else:
        return "Error: Failed to save the project context."

@mcp.tool()
def log_task_completion(completion_report: str) -> str:
    """Appends a timestamped report to the history file in the project's workflow directory."""
    logging.info("[Tool:log_task_completion] Called.")
    project_directory = os.getenv("PROJECT_DIRECTORY")
    
    if not project_directory or not is_safe_project_path(project_directory):
        return "Error: Cannot log progress. The project_directory is invalid or not set."
    
    if not completion_report or not completion_report.strip():
        return "Error: Cannot log empty completion report."

    history_file_path = Path(project_directory).resolve() / WORKFLOW_DIR_NAME / HISTORY_FILENAME
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    log_entry = f"\n\n---\n\n**Logged on:** {timestamp}\n\n{completion_report}"

    if write_file_content(history_file_path, log_entry, append=True):
        return f"Success: Progress logged to {history_file_path.relative_to(project_directory)}."
    else:
        return "Error: Failed to save progress."