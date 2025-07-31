import os
import logging
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

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

# --- Helper function for system prompt (no change) ---
def load_system_prompt():
    # ... (implementation is the same)
    try:
        with open("prompt_implement_user_stories.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        logging.error("[Critical] The 'prompt_implement_user_stories.md' file was not found.")
        return "ERROR: System prompt file not found. Please contact the administrator."
    
def get_log_file_path(project_id: int) -> Path:
    """Returns the standardized path for a project's log file."""
    return LOGS_DIR / f"project_{project_id}_log.md"

# --- MCP Tools ---

@mcp.tool()
async def get_project_context(project_id: int) -> str:
    """
    Fetches project context from the API and combines it with any existing implementation logs.
    """
    logging.info(f"[Tool:get_project_context] Called for Project ID: {project_id}")

    secret_key = os.getenv("SECRET_KEY")
    PROJECT_API_URL = os.getenv("PROJECT_API_URL")

    if not secret_key:
        return "Error: Server not configured. SECRET_KEY is missing from .env file."
    if not PROJECT_API_URL:
        return "Error: Server not configured. PROJECT_API_URL is missing from .env file."

    # --- API Fetching ---
    api_endpoint = f"{PROJECT_API_URL}/{project_id}"
    headers = {"Content-Type": "application/json", "sessionKey": secret_key}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_endpoint, headers=headers)
            response.raise_for_status()
            project_data = response.json()
        logging.info(f"[API] Successfully fetched data for project '{project_data.get('name')}'")
    except httpx.RequestError as e:
        return f"Error: Could not retrieve project data. The backend API returned an error: {e}"

    # --- Load existing implementation log ---
    implementation_log = ""
    log_file_path = get_log_file_path(project_id)
    if log_file_path.exists():
        logging.info(f"Found existing log file for project {project_id}. Loading content.")
        with open(log_file_path, "r", encoding="utf-8") as f:
            implementation_log = f.read()
    
    # --- Context Building ---
    system_prompt = load_system_prompt()

    # Conditionally add the log section to the context
    log_section = ""
    if implementation_log:
        log_section = f"""
            # Implementation Log
            This log contains a history of all previously completed user stories for this project. Use this to understand the current state of the codebase.
            ---
            {implementation_log}
            ---
        """

    enriched_context_string = f"""
        {system_prompt}

        {log_section}

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
    
    logging.info("[Context] Enriched context string created. Returning to client.")
    return enriched_context_string

@mcp.tool()
def log_task_completion(project_id: int, completion_report: str) -> str:
    """
    Appends a task completion report to the project's persistent log file.
    """
    logging.info(f"[Tool:log_task_completion] Logging progress for project ID: {project_id}")
    if not completion_report or not completion_report.strip():
        return "Error: Cannot log empty completion report."

    log_file_path = get_log_file_path(project_id)

    try:
        # Open the file in append mode ('a') with UTF-8 encoding
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n") # Add a separator for clarity
            f.write(completion_report)
        
        logging.info(f"Successfully appended report to {log_file_path}")
        return f"Success: Progress for project {project_id} has been logged."
    except Exception as e:
        logging.error(f"Failed to write to log file for project {project_id}. Error: {e}")
        return f"Error: Could not save progress. A server-side error occurred: {e}"