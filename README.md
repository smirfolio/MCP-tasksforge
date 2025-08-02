# TasksForge.ai - MCP Context Server

This project provides a Model Context Protocol (MCP) server designed to act as a bridge between an AI coding agent (like Cline, Claude Desktop, or a custom tool) and the Project Management AI Assistant tasksforge.ai.

It allows your AI agent to fetch detailed project context, including requirements, user stories, and dependencies, and then assists in implementing the project user story by user story, persisting the progress along the way.

## Features

-   **Dynamic Context Injection**: Fetches comprehensive project details from a remote API and provides it to the AI agent.
-   **State Persistence**: Tracks the implementation progress of user stories in a local `.mcp_history.md` file.
-   **Local Caching**: Saves the fetched project context to `.mcp_project_context.md` on the first run to speed up subsequent sessions.
-   **Organized Workflow**: All agent-related files (history, context, prompts) are stored neatly within a `workflow` directory inside your project.
-   **Secure**: Validates that it only operates within a valid Git repository, preventing accidental writes to other parts of your system, temporary token usage..

## How It Works

The workflow is designed to be efficient and stateful:

1.  **User Setup**: The developer configures their AI coding agent to use this MCP server, providing their Tasksforge secret key in `https://www.tasksforge.ai/internalApp/settings`.
2.  **First Run**: The agent, running in a project directory, detects that the local context is missing. It calls the MCP server to fetch project details from the Tasksforge API. The server then instructs the agent to save this context locally.
3.  **Implementation**: Guided by the prompt in `workflow/prompt_implement_user_stories.md`, the agent helps the developer implement user stories incrementally.
4.  **Logging Progress**: When a user story is complete, the agent calls the MCP server to save a timestamped completion report to `workflow/.mcp_history.md`.
5.  **Subsequent Runs**: On the next run, the agent loads the context and history directly from the local `workflow` directory, avoiding unnecessary API calls and immediately knowing the project's current state.

## Setup and Installation

Follow these steps to get the MCP server ready to be used by your AI agent.

### 1. Prerequisites

-   Python 3.10+
-   `pip` or `uv` for package management
-   An AI coding agent that supports MCP server configuration (e.g., Cline).

### 2. Clone the Server Repository

Clone this repository to a stable location on your machine. This is where the server code will live.

```bash
git clone <url_to_your_mcp_server_repo> MCP-tasksforge
cd MCP-tasksforge
```

### 3. Install Dependencies

Install the required Python packages.

In Celine you can ask in the AI chat to install the MCP-tasksforge directly from the repository project
 ´´´
 Hey Celine could you install this MCP server : @https://github.com/smirfolio/MCP-tasksforge
 ´´´
or manually: 

```bash
pip install -r requirements.txt
# or with uv
uv pip install -r requirements.txt
```
TIPS: in dev enverenement set the env variables, than, you can start your MCP server with the command : 
```bash
uv run mcp dev server.py
```

### 4. Configure Server Environment

The server needs the URL of your project management API. Create a `.env` file in the `MCP-tasksforge` directory.

Create a file named `.env`:

```dotenv
# .env for the MCP Server
# This is the your project working directory.
PROJECT_DIRECTORY="<absolute apth to your project working directory>"
```

## Configuration for Your AI Agent

Your AI coding agent needs to know how to run this server. You will configure this in your agent's settings, typically in a JSON configuration file. Here is a template based on the provided format.
You can ask also your Celine agent to implement the MCP server : 
```BASH
 Hey Cline, add this MCP server from @https://github.com/smirfolio/MCP-tasksforge
```
**`mcp.json` (Example Configuration in your AI Agent):**

```json
{
    "mcpServers": {
        "ai-project-forge": {
            "name": "AI Project Forge",
            "command": "uv",
            "args": [
                "run",
                "mcp",
                "run",
                "<PROJECT_DIRECTORY>/MCP-tasksforge/server.py"
            ],
            "env": {
                "SECRET_KEY": "<Your TAsksforge Secret JWT>",
                "PROJECT_DIRECTORY": "{project_dir}"
            }
        }
    }
}
```

**How to fill out the template:**

-   `"name"`: A user-friendly name for the server, like "AI Project Forge".
-   `"command"` and `"args"`: The command to run the server. The example uses `uv` and `mcp run`.
-   `<PROJECT_DIRECTORY>`: Replace this with the **absolute path** to the directory where you cloned `MCP-tasksforge`.
-   `"env"`: This is the most important part.
    -   `"SECRET_KEY"`: Replace `<Your TAsksforge Secret JWT>` with the **full JWT** you obtain from your Tasksforge application's user settings.
    -   `"PROJECT_DIRECTORY"`: The value `{project_dir}` is a special placeholder that your AI agent (like Cline) should dynamically replace with the **absolute path of the project folder you are currently working in**. This tells the server where to create the `workflow` directory.

You able now to ask your AI Agent to restart the MCP server

## Usage Workflow

Once configured, using the server via your AI agent is simple.

### 1. Initializing a Project

1.  Open a terminal in the root of your project folder (e.g., `~/my-cool-app`).
2.  Make sure it's a Git repository (`git init` if it's not).
3.  Start a conversation with your AI agent and ask it to work on the project, providing the project ID. For example:
    > "Let's start working on project 478."

The agent will automatically:
-   Call the MCP server to fetch the context from the API and will save this context to `workflow/.mcp_project_context.md`.
-   Present you with the project title and analysis, then wait for your command.

### 2. Implementing User Stories

-   Instruct the agent to start a specific user story: `"Start implementing user story #1"`.
-   The agent will follow the rules in the prompt, working incrementally and waiting for your confirmation at each step.

### 3. Completing a Session

-   When a user story is finished, the agent will generate a "Task Completed" summary.
-   It will then automatically call the MCP server to append this summary, along with a timestamp, to `workflow/.mcp_history.md`.
-   The agent will then stop and wait for your next instruction.

### 4. Starting a New Session

-   Simply start a new conversation with the agent in the same project directory.
- Add the `workflow/` folder to the AI coding assistant context
-   The agent will now find and read the local `workflow/.mcp_project_context.md` and `workflow/.mcp_history.md` files, giving it instant knowledge of the project's state without needing to call the API again.

**Tips** After completing a user story, start a completely new chat session for the next one. Provide the AI with the relevant project files `workflow/` and ask it to summarize the work just completed and what remains.
This significantly reduces token consumption, as the context in a single chat increases dramatically with each interaction.

## Server Tools Reference

The MCP server exposes the following tools for the AI agent to use:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_project_context` | `project_id: int` | Fetches the full project context from the remote API. |
| `log_task_completion` | `completion_report: str` | Appends a timestamped summary to `workflow/.mcp_history.md`. |

Special thanks to [@CodingtheFuture](https://www.youtube.com/@CodingtheFuture-jg1he) for not only contributing amazing content but for inspiring and uplifting our entire community. 
