from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Callable

# Optional: load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from openai import OpenAI

# ---------- OpenAI client & model ----------

client = OpenAI()
MODEL = "gpt-4.1-mini"  # you can change this to another chat model


# ---------- Workspace & "current directory" ----------

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "agent_workspace"
WORKSPACE.mkdir(exist_ok=True)

# This is like the terminal's "current working directory", but always inside WORKSPACE.
# All file paths and commands are interpreted relative to this.
CURRENT_DIR: Path = Path(".")  # relative to WORKSPACE root


def get_current_abs_dir() -> Path:
    """
    Absolute path to the current working directory inside the workspace.
    """
    return (WORKSPACE / CURRENT_DIR).resolve()


def safe_path(relative_path: str) -> Path:
    """
    Resolve a path inside the workspace and prevent escaping it.
    Paths are interpreted relative to CURRENT_DIR, unless they start with a leading '/'
    in which case they're treated as relative to workspace root.
    """
    global CURRENT_DIR

    if relative_path is None:
        relative_path = "."

    # Normalize separators and whitespace
    relative_path = relative_path.replace("\\", "/").strip()

    if relative_path == "":
        relative_path = "."

    # Absolute (workspace-root based) if starting with '/'
    if relative_path.startswith("/"):
        relative_path = relative_path.lstrip("/")
        base = WORKSPACE
    else:
        base = get_current_abs_dir()

    target = (base / relative_path).resolve()

    if not str(target).startswith(str(WORKSPACE)):
        raise ValueError(f"Refusing to access path outside workspace: {target}")

    return target


# ---------- Tool implementations ----------


def tool_list_directory(path: str = ".") -> str:
    p = safe_path(path)

    if not p.exists():
        return f"Directory does not exist: {p.relative_to(WORKSPACE)}"

    if not p.is_dir():
        return f"Path is not a directory: {p.relative_to(WORKSPACE)}"

    entries = []
    for item in sorted(p.iterdir()):
        marker = "/ " if item.is_dir() else "  "
        entries.append(f"{marker}{item.name}")

    listing = "\n".join(entries) or "(empty directory)"
    return f"Listing for {p.relative_to(WORKSPACE)}:\n{listing}"


def tool_create_directory(path: str) -> str:
    p = safe_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Created directory: {p.relative_to(WORKSPACE)}"


def tool_write_file(path: str, content: str, append: bool = False) -> str:
    p = safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        f.write(content)

    return (
        f"{'Appended to' if append else 'Wrote file'}: {p.relative_to(WORKSPACE)} "
        f"(length={len(content)} characters)"
    )


def tool_read_file(path: str) -> str:
    p = safe_path(path)

    if not p.exists() or not p.is_file():
        return f"File does not exist: {p.relative_to(WORKSPACE)}"

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"File is not valid UTF-8 text: {p.relative_to(WORKSPACE)}"

    # Limit very large outputs
    max_len = 4000
    if len(text) > max_len:
        return (
            f"File content (truncated to {max_len} characters):\n"
            + text[:max_len]
            + "\n...[truncated]..."
        )

    return f"File content of {p.relative_to(WORKSPACE)}:\n{text}"


def tool_run_command(command: str) -> str:
    """
    Run a shell command inside the CURRENT_DIR within the workspace.
    This is powerful. Use carefully.
    """
    cwd = get_current_abs_dir()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after 60 seconds in {cwd.relative_to(WORKSPACE)}."

    out = result.stdout or ""
    err = result.stderr or ""
    combined = ""

    if out:
        combined += f"[STDOUT]\n{out}"
    if err:
        combined += f"\n[STDERR]\n{err}"

    if not combined.strip():
        combined = "(no output)"

    # Truncate very long outputs
    max_len = 6000
    if len(combined) > max_len:
        combined = combined[:max_len] + "\n...[truncated]..."

    rel_cwd = cwd.relative_to(WORKSPACE)
    return (
        f"Command (cwd={rel_cwd}): {command}\n"
        f"Exit code: {result.returncode}\n\n{combined}"
    )


TOOL_IMPLEMENTATIONS: Dict[str, Callable[..., str]] = {
    "list_directory": tool_list_directory,
    "create_directory": tool_create_directory,
    "write_file": tool_write_file,
    "read_file": tool_read_file,
    "run_command": tool_run_command,
}


# ---------- OpenAI tool schema ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders inside a workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path inside the workspace. Defaults to '.'.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a folder (and parents if needed) inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path to create, e.g. 'demo' or 'src/utils'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite/append a text file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path, e.g. 'demo/main.py'.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write into the file.",
                    },
                    "append": {
                        "type": "boolean",
                        "description": "If true, append to the file instead of overwriting.",
                        "default": False,
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace (UTF-8).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command inside the current working directory of the workspace. "
                "Use this to run Python scripts, git, or other tools. "
                "Be explicit and safe with commands."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The full command to run, e.g. 'python main.py'.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]


SYSTEM_PROMPT = """
You are 'Local GPT Dev Agent', running on the user's own PC inside a workspace folder.

You can:
- Inspect and edit files and folders in the workspace.
- Create new projects, folders, and files.
- Refactor code across multiple files.
- Run shell commands (python, node, git, npm, etc.) when appropriate.

You have tools to:
- list directories
- read files
- write or overwrite files
- append to files
- run shell commands in the workspace

GENERAL STYLE — VIBE CODING
1. Treat every message as part of a coding session.
   - The user can talk casually: "make me a todo app", "split this file", "vibe-code a backend".
   - Turn that into a concrete plan and execute it with tools.

2. For a new project:
   - Prefer to work inside the "current workspace directory" (the cwd I tell you).
   - Create a top-level folder with a clean name (e.g. "todo-app", "blog-api") under that directory,
     unless the user explicitly gives a different path.
   - Inside, create a minimal but complete structure, e.g. for Python:
       - src/ or app/
       - tests/ (if useful)
       - README.md with clear run instructions
       - requirements.txt or pyproject.toml if needed
   - For JS/TS, use package.json, src/, etc. according to the stack.

3. When editing or refactoring:
   - Before editing a non-trivial file, read it first using the file-read tool.
   - If the user says "split this into multiple files":
       - Decide on a structure (e.g. main.py, services.py, routes/, components/).
       - Create the new files.
       - Move code into them and fix imports.
       - Briefly explain the new structure to the user.

4. Running code and commands:
   - Use the shell tool to run commands (python, node, npm, pip, pytest, git, etc.).
   - After running a command, show the important part of the output.
   - If a command fails, inspect the error, adjust files, and try again.

5. Preparing for Git (only when the user asks):
   - Ensure there is a README.md.
   - Add a sensible .gitignore for the stack (Python venv, __pycache__, node_modules, etc.).
   - Optionally add a LICENSE if appropriate.
   - Use shell commands:
       - 'git init'
       - 'git add .'
       - 'git commit -m "<message>"'
   - Explain what you did in simple terms.

6. Safety:
   - Never run destructive commands like deleting the whole workspace or formatting disks.
   - Stay inside the workspace directory.
   - If something feels risky or irreversible, ask the user before proceeding.

Always respond with:
- A short explanation of what you’re doing, and
- A summary of what changed in the filesystem or what the command output was.
"""


# ---------- cd handling / active project memory ----------


def change_directory(new_path: str) -> str:
    """
    Handle 'cd'-like behavior inside the workspace.
    Supports:
      - cd blog-api
      - cd blog-api/app
      - cd ..
      - cd .
      - cd (go to workspace root)
      - cd C:\\Users\\user\\gpt-local-agent\\agent_workspace  (mapped to workspace root)
    """
    global CURRENT_DIR

    new_path = (new_path or "").strip()

    # `cd` with no args -> workspace root
    if new_path == "":
        CURRENT_DIR = Path(".")
        return "Current directory: / (workspace root)"

    # Strip quotes if user writes cd "blog-api"
    if len(new_path) >= 2 and new_path[0] == new_path[-1] and new_path[0] in {"'", '"'}:
        new_path = new_path[1:-1].strip()

    # If absolute path, try to map it into workspace
    candidate: Path
    if os.path.isabs(new_path):
        candidate = Path(new_path).resolve()
    else:
        candidate = (get_current_abs_dir() / new_path).resolve()

    # If user pointed exactly to WORKSPACE (like cd C:\...\agent_workspace) treat as root
    if candidate == WORKSPACE:
        CURRENT_DIR = Path(".")
        return "Current directory: / (workspace root)"

    # Enforce staying inside workspace
    if not str(candidate).startswith(str(WORKSPACE)):
        return f"Refusing to cd outside workspace root: {candidate}"

    if not candidate.exists():
        # Show nice relative path if possible
        try:
            rel = candidate.relative_to(WORKSPACE)
            return f"Directory does not exist: {rel}"
        except ValueError:
            return f"Directory does not exist: {candidate}"

    if not candidate.is_dir():
        try:
            rel = candidate.relative_to(WORKSPACE)
            return f"Not a directory: {rel}"
        except ValueError:
            return f"Not a directory: {candidate}"

    # Update CURRENT_DIR
    CURRENT_DIR = candidate.relative_to(WORKSPACE)
    if str(CURRENT_DIR) == ".":
        return "Current directory: / (workspace root)"

    return f"Current directory: /{CURRENT_DIR.as_posix()}"


def format_current_dir_for_model() -> str:
    """
    Provide a human-readable cwd string for the model.
    """
    if str(CURRENT_DIR) == ".":
        return "/ (workspace root)"
    return f"/{CURRENT_DIR.as_posix()}"


# ---------- Core chat + tool loop ----------


def run_agent_turn(user_input: str) -> str:
    """
    Handle one user command:
    - Ask the model what to do
    - Execute any tools it requests
    - Return the final assistant message content
    """
    cwd_str = format_current_dir_for_model()

    # Fresh context for each turn, but we tell the model where it "is" (cwd)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Current workspace directory (like your shell cwd) is: "
                f"{cwd_str}. Interpret unqualified/relative paths and "
                "create new files/projects under this directory unless "
                "the user gives an explicit path from the workspace root."
            ),
        },
        {"role": "user", "content": user_input},
    ]

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # If the model wants to use tools
        if msg.tool_calls:
            # Add the assistant message (with tool calls) to the history
            assistant_msg = {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": [],
            }

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                args_str = tool_call.function.arguments

                try:
                    args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError as e:
                    tool_result = f"Error: could not parse arguments for tool '{tool_name}': {e}"
                else:
                    tool_func = TOOL_IMPLEMENTATIONS.get(tool_name)
                    if not tool_func:
                        tool_result = f"Error: unknown tool '{tool_name}'."
                    else:
                        try:
                            tool_result = tool_func(**args)
                        except Exception as e:
                            tool_result = f"Error while running tool '{tool_name}': {e}"

                # Record this tool call on the assistant message
                assistant_msg["tool_calls"].append(
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_name,
                            "arguments": args_str,
                        },
                    }
                )

                # Add the tool result message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    }
                )

            # Insert the assistant message before the tool messages
            messages.insert(-len(msg.tool_calls), assistant_msg)
            continue

        # No tool calls: this is the final answer for this turn
        final_content = msg.content or ""
        return final_content


# ---------- CLI main loop ----------


def main() -> None:
    print("[LOCAL GPT AGENT] running inside workspace:")
    print(f"  {WORKSPACE}")
    print("Type 'exit' to quit.")
    print("You can also use 'cd <path>' to change the active project/directory.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        # Handle local 'cd' without sending to the model
        if user_input.lower().startswith("cd"):
            # allow "cd" or "cd path"
            parts = user_input.split(maxsplit=1)
            path_arg = parts[1] if len(parts) > 1 else ""
            result = change_directory(path_arg)
            print("\nAgent:\n" + result + "\n")
            continue

        print("Agent: thinking...")
        try:
            reply = run_agent_turn(user_input)
        except Exception as e:
            print(f"Agent error: {e}")
            continue

        print("\nAgent:\n" + reply + "\n")


if __name__ == "__main__":
    main()
