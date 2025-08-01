import os
import logging
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

load_dotenv()

# --- Setup ---
LOGS_DIR = Path("project_logs")
LOGS_DIR.mkdir(exist_ok=True) # Ensure the logs directory exists

# --- Logging and Server Setup (no change) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('[Setup] Initializing server...')
mcp = FastMCP("AI Project Forge Context Server")
logging.info(f'[Setup] FastMCP server "{mcp.name}" created.')

# --- Standard Filenames ---
WORKFLOW_DIR_NAME = "workflow"
HISTORY_FILENAME = ".mcp_history.md"
CONTEXT_FILENAME = ".mcp_project_context.md"


def read_file_content(file_path: Path) -> str | None:
    """Safely reads content from a file. Returns content or None if not found."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read file at {file_path}: {e}")
        return None

def write_file_content(file_path: Path, content: str, append: bool = False) -> bool:
    """Safely writes content to a file. Returns True on success, False on failure."""
    mode = "a" if append else "w"
    try:
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Failed to write to file at {file_path}: {e}")
        return False
    
# --- Security Helper (no change) ---
def is_safe_project_path(dir_path_str: str) -> bool:
    # ... (implementation is the same)
    if not dir_path_str or ".." in dir_path_str: return False
    try:
        project_path = Path(dir_path_str).resolve()
        if not project_path.is_dir() or not (project_path / ".git").is_dir(): return False
    except Exception: return False
    return True


# --- Helper function for system prompt (no change) ---
def load_system_prompt():
    # ... (implementation is the same)
    try:
        with open("prompt_implement_user_stories.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        logging.error("[Critical] The 'prompt_implement_user_stories.md' file was not found.")
        return "ERROR: System prompt file not found. Please contact the administrator."

# --- MCP Tools ---
@mcp.tool()
async def get_project_context(project_id: int) -> str:
    """
    Fetches project details from the API and combines it with the system prompt and
    any existing implementation history to create a full context string.
    """
    logging.info(f"[Tool:get_project_context] Called for Project ID: {project_id}")
    
    # Get config from environment
    project_directory = os.getenv("PROJECT_DIRECTORY")
    secret_key = os.getenv("SECRET_KEY")
    PROJECT_API_URL = os.getenv("PROJECT_API_URL")

    # Validate config and path
    if not all([project_directory, secret_key, PROJECT_API_URL]):
        return "Error: Server is missing required environment variables (PROJECT_DIRECTORY, SECRET_KEY, PROJECT_API_URL)."
    if not is_safe_project_path(project_directory):
        return "Error: The project_directory is not a valid git repository."

    # Fetch data from the remote API
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

    # --- Construct just the project-specific context ---
    project_context_str = f"""
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
    
    # This tool now ONLY returns the fetched context.
    # The client/agent is responsible for combining it with other local files.
    return project_context_str

#--- 2. NEW TOOL TO SAVE THE CONTEXT ---
@mcp.tool()
def save_project_context(project_context: str) -> str:
    """
    Saves the provided project context string to a standard file in the project directory.
    """
    logging.info("[Tool:save_project_context] Called to save project context locally.")
    project_directory = os.getenv("PROJECT_DIRECTORY")
    if not project_directory or not is_safe_project_path(project_directory):
        return "Error: Cannot save context. The project_directory is invalid or not set."

    context_file_path = Path(project_directory).resolve() / WORKFLOW_DIR_NAME / CONTEXT_FILENAME

    if write_file_content(context_file_path, project_context):
        logging.info(f"Successfully saved project context to {context_file_path}")
        return f"Success: Project context saved locally to {CONTEXT_FILENAME}."
    else:
        return "Error: A server-side error occurred while trying to save the project context."
    
@mcp.tool()
def log_task_completion(completion_report: str) -> str: # No longer needs project_id
    """
    Appends a timestamped task completion report to the project's history file.
    """
    logging.info("[Tool:log_task_completion] Logging progress.")
    project_directory = os.getenv("PROJECT_DIRECTORY")
    if not project_directory or not is_safe_project_path(project_directory):
        return "Error: Cannot log progress. The project_directory is invalid or not set."

    if not completion_report or not completion_report.strip():
        return "Error: Cannot log empty completion report."

    history_file_path = Path(project_directory).resolve() / WORKFLOW_DIR_NAME / HISTORY_FILENAME

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    log_entry = f"\n\n---\n\n**Logged on:** {timestamp}\n\n{completion_report}"

    if write_file_content(history_file_path, log_entry, append=True):
        logging.info(f"Successfully appended report to {history_file_path}")
        return f"Success: Progress has been logged to {HISTORY_FILENAME}."
    else:
        return "Error: A server-side error occurred while trying to save progress."