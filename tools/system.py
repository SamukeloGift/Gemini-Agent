
import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def get_system_info() -> Dict[str, Any]:
    """
    Get current system information
    """
    try:
        import psutil

        # Get basic system info Use global platform, to avoid repeating yourself and checking everywhere...
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "current_user": os.getenv("USERNAME") if IS_WINDOWS else os.getenv("USER"),
            "current_directory": str(Path.cwd()),
            "home_directory": str(Path.home()),
            "timestamp": datetime.now().isoformat()
        }

        # Get system resources if psutil available...
        try:
            # Use C:\ for Windows and / for MacOS and linux
            disk_path = "C:\\" if IS_WINDOWS else "/"

            system_info.update({
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {
                    "total": psutil.disk_usage(disk_path).total,
                    "used": psutil.disk_usage(disk_path).used,
                    "free": psutil.disk_usage(disk_path).free,
                    "percent": (psutil.disk_usage(disk_path).used / psutil.disk_usage(disk_path).total) * 100
                }
            })
        except ImportError:
            system_info["note"] = "Install psutil for detailed system metrics"

        return system_info

    except Exception as e:
        return {"error": f"Failed to get system info: {str(e)}"}


def run_python_script(script_path: str, timeout: int = 30) -> Dict[str, Any]:
    """
    run a Python script and capture output/errors 
    """
    try:
        path = Path(script_path).expanduser()
        if not path.exists():
            return {"error": f"Script not found: {script_path}"}

        start_time = time.time()

        # Use platform-specific Python command(linux And Mac use python3...)
        python_cmd = "python" if IS_WINDOWS else "python3"

        result = subprocess.run(
            [python_cmd, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=path.parent
        )

        execution_time = time.time() - start_time

        output_data = {
            "script_path": str(path),
            "platform": platform.system(),
            "python_command": python_cmd,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(execution_time, 2),
            "success": result.returncode == 0,
            "timestamp": datetime.now().isoformat()
        }

        return output_data

    except subprocess.TimeoutExpired:
        return {"error": f"Script execution timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": f"Failed to execute script: {str(e)}"}


def analyze_python_code(file_path: str) -> Dict[str, Any]:
    """
    Analyze Python code for potential issues using basic checks
    """
    try:
        from .file_system import read_file_content
        # First Read The file
        file_content = read_file_content(file_path)
        if "error" in file_content:
            return file_content

        content = file_content["content"]
        lines = content.split('\n')

        issues = []
        suggestions = []
        imports = []
        functions = []
        classes = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                imports.append(stripped)

            if stripped.startswith('def '):
                functions.append(stripped)

            if stripped.startswith('class '):
                classes.append(stripped)

            # issue detection
            if 'print(' in line and not line.strip().startswith('#'):
                suggestions.append(f"Line {i}: Consider using logging instead of print statements")

            if line.strip() == 'pass' and i > 1:
                issues.append(f"Line {i}: Empty pass statement - might need implementation")

            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                issues.append(f"Line {i}: TODO/FIXME comment found")

        # try basic syntax check
        syntax_valid = True
        syntax_error = None
        try:
            compile(content, file_path, 'exec')
        except SyntaxError as e:
            syntax_valid = False
            syntax_error = f"Line {e.lineno}: {e.msg}"
            issues.append(f"Syntax Error: {syntax_error}")

        analysis = {
            "file_path": file_path,
            "total_lines": len(lines),
            "imports_count": len(imports),
            "functions_count": len(functions),
            "classes_count": len(classes),
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "issues": issues,
            "suggestions": suggestions,
            "imports": imports,
            "functions": functions[:10],  # limit this for display
            "classes": classes,
            "analysis_timestamp": datetime.now().isoformat()
        }

        return analysis

    except Exception as e:
        return {"error": f"Failed to analyze code: {str(e)}"}


def send_system_notification(message: str, title: str = "System Agent") -> Dict[str, Any]:
    """
    Send system notification cross-platform
    """
    try:
        if IS_MACOS:
            # Use macOS osascript to show notification
            script = f'display notification "{message}" with title "{title}"'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
        elif IS_WINDOWS:
            # Use PowerShell for Windows notifications
            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = "{title}"
            $notification.BalloonTipText = "{message}"
            $notification.Visible = $true
            $notification.ShowBalloonTip(3000)
            Start-Sleep -Seconds 3
            $notification.Dispose()
            '''
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                text=True
            )
        elif IS_LINUX:
            # use notify-send for linux
            result = subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                text=True
            )
        else:
            return {"error": f"Notifications not supported on {platform.system()}"}

        notification_result = {
            "message": message,
            "title": title,
            "platform": platform.system(),
            "success": result.returncode == 0,
            "error": result.stderr if result.returncode != 0 else None,
            "timestamp": datetime.now().isoformat()
        }

        return notification_result

    except Exception as e:
        return {"error": f"Failed to send notification: {str(e)}"}


def execute_cli_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute CLI command with proper shell handling
    """
    try:
        start_time = time.time()
        if IS_WINDOWS:
            # For win-os, use powershell
            command_list = ["powershell", "-Command", command]
        else:
            # for unix split the command into a list
            command_list = command.split()
            
        result = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd(),
            shell=False 
        )

        execution_time = time.time() - start_time

        output_data = {
            "command": command,
            "platform": platform.system(),
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "execution_time": round(execution_time, 2),
            "success": result.returncode == 0,
            "working_directory": str(Path.cwd()),
            "timestamp": datetime.now().isoformat()
        }

        return output_data

    except subprocess.TimeoutExpired:
        return {"error": f"Command execution timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": f"Failed to execute command: {str(e)}"}
