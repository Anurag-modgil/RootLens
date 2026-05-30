import logging
import re
import subprocess
from typing import Dict, Any

logger = logging.getLogger("rootlens.executor")

class SafeCommandExecutor:
    def __init__(self):
        self.allowlist_patterns = [
            r"^docker restart [a-zA-Z0-9_-]+$",
            r"^kubectl rollout restart deployment/[a-zA-Z0-9_-]+$",
            r"^redis-cli flushall$",
            r"^echo '[a-zA-Z0-9_\s!\.\-]+'$"
        ]

    def is_command_allowed(self, command: str) -> bool:
        """
        Validate that the command matches one of the patterns in the strict allowlist.
        """
        trimmed = command.strip()
        for pattern in self.allowlist_patterns:
            if re.match(pattern, trimmed):
                return True
        return False

    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Securely execute an allowlisted command using subprocess with shell=False.
        Prevents shell injections.
        """
        trimmed = command.strip()
        
        # 1. Enforce allowlist check
        if not self.is_command_allowed(trimmed):
            error_msg = f"Security Block: Command '{trimmed}' is not allowlisted."
            logger.error(error_msg)
            return {
                "status": "blocked",
                "error": error_msg,
                "output": ""
            }

        # 2. Parse command safely into tokens to avoid passing raw shell string
        # split by whitespace (safe split since allowlisted commands have simple inputs)
        tokens = trimmed.split()

        logger.info(f"Executing secure command: {tokens}")
        try:
            # shell=False prevents command injection vulnerabilities
            run_result = subprocess.run(
                tokens,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if run_result.returncode == 0:
                return {
                    "status": "success",
                    "output": run_result.stdout.strip(),
                    "error": ""
                }
            else:
                return {
                    "status": "failed",
                    "output": run_result.stdout.strip(),
                    "error": run_result.stderr.strip()
                }

        except subprocess.TimeoutExpired as te:
            error_msg = f"Command execution timed out: {str(te)}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "output": "",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Subprocess error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "output": "",
                "error": error_msg
            }
