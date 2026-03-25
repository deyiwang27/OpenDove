from __future__ import annotations
import subprocess
from pathlib import Path
from langchain_core.tools import BaseTool


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "Read the contents of a file. Input: absolute file path."

    def _run(self, path: str) -> str:
        try:
            return Path(path).read_text()
        except Exception as e:
            return f"Error reading {path}: {e}"


class GlobTool(BaseTool):
    name: str = "glob"
    description: str = "Find files matching a glob pattern. Input JSON: {\"pattern\": \"**/*.py\", \"cwd\": \"/path/to/dir\"}"

    def _run(self, input: str) -> str:
        import json
        try:
            data = json.loads(input)
            cwd = Path(data.get("cwd", "."))
            matches = list(cwd.glob(data["pattern"]))
            return "\n".join(str(m) for m in matches) or "No matches found."
        except Exception as e:
            return f"Error: {e}"


class GrepTool(BaseTool):
    name: str = "grep"
    description: str = "Search file contents using grep. Input JSON: {\"pattern\": \"regex\", \"cwd\": \"/path\"}"

    def _run(self, input: str) -> str:
        import json
        try:
            data = json.loads(input)
            result = subprocess.run(
                ["grep", "-r", "-n", "--include=*.py", data["pattern"], "."],
                cwd=data.get("cwd", "."), capture_output=True, text=True
            )
            return result.stdout or "No matches."
        except Exception as e:
            return f"Error: {e}"


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "Write content to a file (creates parent dirs). Input JSON: {\"path\": \"/abs/path\", \"content\": \"...\"}"

    def _run(self, input: str) -> str:
        import json
        try:
            data = json.loads(input)
            p = Path(data["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data["content"])
            return f"Written: {p}"
        except Exception as e:
            return f"Error: {e}"


class BashTool(BaseTool):
    name: str = "bash"
    description: str = "Run a shell command. Input JSON: {\"command\": \"pytest tests/\", \"cwd\": \"/path/to/worktree\"}"

    def _run(self, input: str) -> str:
        import json
        try:
            data = json.loads(input)
            result = subprocess.run(
                data["command"], shell=True, cwd=data.get("cwd", "."),
                capture_output=True, text=True, timeout=120
            )
            output = result.stdout + result.stderr
            return output[:4000] or "(no output)"
        except Exception as e:
            return f"Error: {e}"
