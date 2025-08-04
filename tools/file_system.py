import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import platform
import glob
import re

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def search_text(pattern: str, file_pattern: str, base_path: str = ".") -> Dict[str, Any]:
    """
    Search for a text pattern in files matching a glob pattern.
    """
    try:
        path = Path(base_path).expanduser().resolve()
        files = [p for p in path.glob(file_pattern) if p.is_file()]
        results = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if re.search(pattern, line):
                            results.append({
                                "file_path": str(file),
                                "line_number": line_num,
                                "line_content": line.strip()
                            })
            except Exception as e:
                # ignore files that can't be opened
                print(f"Could not read file {file}: {e}")
                continue
        return {"results": results}
    except Exception as e:
        return {"error": f"Failed to search for text: {str(e)}"}

def find_files(pattern: str, base_path: str = ".") -> Dict[str, Any]:
    """
    Find files matching a glob pattern recursively.
    """
    try:
        path = Path(base_path).expanduser().resolve()
        files = [str(p) for p in path.glob(pattern)]
        return {"files": files}
    except Exception as e:
        return {"error": f"Failed to find files: {str(e)}"}

def check_trash_bin(days_threshold: int = 10) -> Dict[str, Any]:
    """
    Check Trash/Recycle Bin for files older than specified days
    """
    try:
        # Check Path
        if IS_MACOS:
            trash_path = Path.home() / ".Trash"
        elif IS_WINDOWS:
            # Windows Recycle Bin locations
            trash_paths = [
                Path("C:\\$Recycle.Bin"),
                Path.home() / "Desktop" / "$RECYCLE.BIN"
            ]
            trash_path = None
            for path in trash_paths:
                if path.exists():
                    trash_path = path
                    break
            if not trash_path:
                return {"error": "Recycle Bin not found"}
        elif IS_LINUX:
            trash_path = Path.home() / ".local/share/Trash/files"
        else:
            return {"error": f"Unsupported operating system: {platform.system()}"}

        if not trash_path.exists():
            return {"error": f"Trash directory not found: {trash_path}"}

        old_files = []
        total_files = 0
        total_size = 0
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        for item in trash_path.iterdir():
            try:
                stat_info = item.stat()
                file_date = datetime.fromtimestamp(stat_info.st_mtime)
                file_size = stat_info.st_size
                total_files += 1
                total_size += file_size

                if file_date < cutoff_date:
                    old_files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": file_size,
                        "modified": file_date.isoformat(),
                        "days_old": (datetime.now() - file_date).days
                    })
            except (OSError, PermissionError):
                continue

        result = {
            "trash_path": str(trash_path),
            "platform": platform.system(),
            "total_files": total_files,
            "total_size": total_size,
            "old_files_count": len(old_files),
            "old_files": old_files[:20],  # for cleaner display
            "size_to_free": sum(f["size"] for f in old_files),
            "days_threshold": days_threshold,
            "scan_timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        return {"error": f"Failed to check trash: {str(e)}"}


def clean_old_trash_files(days_threshold: int = 10, confirm: bool = True) -> Dict[str, Any]:
    """
    Delete files from trash older than specified days
    """
    try:
        # First check what we're about to delete
        trash_check = check_trash_bin(days_threshold)
        if "error" in trash_check:
            return trash_check

        old_files = trash_check["old_files"]
        if not old_files:
            return {"message": "No old files found to delete", "deleted_count": 0}

        deleted_files = []
        failed_deletions = []
        total_freed = 0

        for file_info in old_files:
            try:
                file_path = Path(file_info["path"])
                if file_path.exists():
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()

                    deleted_files.append(file_info["name"])
                    total_freed += file_info["size"]

            except (OSError, PermissionError) as e:
                failed_deletions.append({"file": file_info["name"], "error": str(e)})

        result = {
            "deleted_count": len(deleted_files),
            "failed_count": len(failed_deletions),
            "deleted_files": deleted_files,
            "failed_deletions": failed_deletions,
            "space_freed_bytes": total_freed,
            "space_freed_mb": round(total_freed / (1024 * 1024), 2),
            "timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        return {"error": f"Failed to clean trash: {str(e)}"}


def read_file_content(file_path: str, max_lines: int = 500) -> Dict[str, Any]:
    """
    Read and analyze file content
    """
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"error": f"Path is not a file: {file_path}"}

        # Check file size (limit to 1MB for safety), 
        file_size = path.stat().st_size
        if file_size > (1024 * 1024):
            return {"error": f"File too large: {file_size} bytes (max 1MB)"}

        # check file type
        suffix = path.suffix.lower()
        file_type = "text"
        if suffix in ['.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
            file_type = "code"
        elif suffix in ['.md', '.txt', '.log']:
            file_type = "text"
        elif suffix in ['.jpg', '.png', '.pdf', '.zip']:
            return {"error": f"Binary file type not supported: {suffix}"}

        # check content
        try:
            with open(path, 'r', encoding='utf-8') as f: # Use encoding='utf-8', Windows kinda has issues with default encoding
                lines = f.readlines()
                content = ''.join(lines[:max_lines])

            result = {
                "file_path": str(path),
                "file_type": file_type,
                "file_extension": suffix,
                "total_lines": len(lines),
                "content_lines_read": min(len(lines), max_lines),
                "content": content,
                "file_size": file_size,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                "is_truncated": len(lines) > max_lines
            }

            return result

        except UnicodeDecodeError:
            return {"error": f"Cannot decode file as UTF-8: {file_path}"}

    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


def write_file_content(file_path: str, content: str, backup: bool = True) -> Dict[str, Any]:
    """
    Write content to file with optional backup
    """
    try:
        path = Path(file_path).expanduser()
        backup_path = None

        # Create backup 
        if path.exists() and backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_suffix(f".backup_{timestamp}{path.suffix}")
            shutil.copy2(path, backup_path)

        # Write content
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = {
            "file_path": str(path),
            "backup_created": backup_path is not None,
            "backup_path": str(backup_path) if backup_path else None,
            "content_length": len(content),
            "lines_written": content.count('\n') + 1,
            "timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}


def list_directory_contents(dir_path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """
    List directory contents with file information
    """
    try:
        path = Path(dir_path).expanduser().resolve()
        if not path.exists():
            return {"error": f"Directory not found: {dir_path}"}

        if not path.is_dir():
            return {"error": f"Path is not a directory: {dir_path}"}

        files = []
        directories = []
        total_size = 0

        for item in path.iterdir():
            if not show_hidden and item.name.startswith('.'):
                continue

            try:
                stat_info = item.stat()
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "is_directory": item.is_dir(),
                    "size": stat_info.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "permissions": oct(stat_info.st_mode)[-3:]
                }

                if item.is_dir():
                    directories.append(item_info)
                else:
                    files.append(item_info)
                    total_size += item_info["size"]

            except (OSError, PermissionError):
                continue

        result = {
            "directory_path": str(path),
            "total_files": len(files),
            "total_directories": len(directories),
            "total_size": total_size,
            "files": sorted(files, key=lambda x: x["name"]),
            "directories": sorted(directories, key=lambda x: x["name"]),
            "show_hidden": show_hidden,
            "scan_timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        return {"error": f"Failed to list directory: {str(e)}"}