import os

from llm_agent import PROJECT_ROOT

_HOME = os.path.expanduser("~")

# 白名单：只允许访问项目目录和常用的用户文档目录，
# 排除 .ssh / .env / 浏览器 profile 等敏感路径。
ALLOWED_ROOTS = [
    PROJECT_ROOT,
    os.path.normpath(os.getcwd()),
    os.path.normpath(os.path.join(_HOME, "Documents")),
    os.path.normpath(os.path.join(_HOME, "Desktop")),
    os.path.normpath(os.path.join(_HOME, "Downloads")),
    os.path.normpath(os.path.join(_HOME, "Pictures")),
    os.path.normpath(os.path.join(_HOME, "Videos")),
    os.path.normpath(os.path.join(_HOME, "Music")),
]

FILE_TOOL_DEFINITIONS = {
    "list_files": {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出某个目录下的所有文件及其属性信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "要列出文件的目录路径"}
                },
                "required": ["directory"]
            }
        }
    },
    "rename_file": {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "修改某个目录下某个文件的名字",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "文件所在的目录路径"},
                    "old_name": {"type": "string", "description": "原文件名"},
                    "new_name": {"type": "string", "description": "新文件名"}
                },
                "required": ["directory", "old_name", "new_name"]
            }
        }
    },
    "delete_file": {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除某个目录下的某个文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "文件所在的目录路径"},
                    "filename": {"type": "string", "description": "要删除的文件名"}
                },
                "required": ["directory", "filename"]
            }
        }
    },
    "delete_directory": {
        "type": "function",
        "function": {
            "name": "delete_directory",
            "description": "删除某个目录下的某个子目录（包括其所有内容）",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "父目录路径"},
                    "dirname": {"type": "string", "description": "要删除的子目录名"}
                },
                "required": ["directory", "dirname"]
            }
        }
    },
    "create_file": {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "在某个目录下新建一个文件并写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "要创建文件的目录路径"},
                    "filename": {"type": "string", "description": "新文件的名称"},
                    "content": {"type": "string", "description": "要写入文件的内容，默认为空"}
                },
                "required": ["directory", "filename"]
            }
        }
    },
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取某个目录下的某个文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "文件所在的目录路径"},
                    "filename": {"type": "string", "description": "要读取的文件名"}
                },
                "required": ["directory", "filename"]
            }
        }
    },
    "search_file_content": {
        "type": "function",
        "function": {
            "name": "search_file_content",
            "description": "在目录中搜索文件内容，查找包含关键字的行，支持逐行搜索和关键字高亮",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "要搜索的目录路径"},
                    "keyword": {"type": "string", "description": "要搜索的关键字"},
                    "filename": {"type": "string", "description": "可选，指定要搜索的文件名，不指定则搜索目录下所有文件"}
                },
                "required": ["directory", "keyword"]
            }
        }
    },
}

def _is_under_allowed_root(target: str) -> bool:
    for root in ALLOWED_ROOTS:
        try:
            common = os.path.commonpath([target, root])
            if os.path.normcase(common) == os.path.normcase(root):
                return True
        except ValueError:
            continue
    return False


def _validate_path(directory: str, filename: str = None) -> str:
    if not directory:
        return "Error: Directory path cannot be empty."

    try:
        abs_directory = os.path.abspath(directory)
        abs_directory = os.path.normpath(abs_directory)

        if not _is_under_allowed_root(abs_directory):
            return f"Error: Access denied. Path is outside allowed directories."

        if filename is not None:
            full_path = os.path.normpath(os.path.join(abs_directory, filename))
            if not full_path.startswith(abs_directory + os.sep) and full_path != abs_directory:
                return "Error: Invalid path detected."
            if not _is_under_allowed_root(full_path):
                return f"Error: Access denied. Path is outside allowed directories."

        return ""
    except Exception as e:
        return f"Error: Path validation failed - {str(e)}"


def list_files(directory: str) -> str:
    try:
        validation_error = _validate_path(directory)
        if validation_error:
            return validation_error
        
        if not os.path.isdir(directory):
            return f"Error: '{directory}' is not a valid directory."
        
        entries = os.listdir(directory)
        
        result = "\n".join(entries)
        return result
    except Exception as e:
        return f"Error listing files: {str(e)}"


def rename_file(directory: str, old_name: str, new_name: str) -> str:
    try:
        validation_error = _validate_path(directory, old_name)
        if validation_error:
            return validation_error
        validation_error = _validate_path(directory, new_name)
        if validation_error:
            return validation_error
        
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        
        if not os.path.exists(old_path):
            return f"Error: File '{old_name}' does not exist in '{directory}'."
        
        if os.path.exists(new_path):
            return f"Error: File '{new_name}' already exists in '{directory}'."
        
        os.rename(old_path, new_path)
        return f"Successfully renamed '{old_name}' to '{new_name}' in '{directory}'."
    except Exception as e:
        return f"Error renaming file: {str(e)}"


def delete_file(directory: str, filename: str) -> str:
    try:
        validation_error = _validate_path(directory, filename)
        if validation_error:
            return validation_error
        
        file_path = os.path.join(directory, filename)
        
        if not os.path.exists(file_path):
            return f"Error: File '{filename}' does not exist in '{directory}'."
        
        if os.path.isdir(file_path):
            return f"Error: '{filename}' is a directory, not a file."
        
        os.remove(file_path)
        return f"Successfully deleted '{filename}' from '{directory}'."
    except Exception as e:
        return f"Error deleting file: {str(e)}"


def delete_directory(directory: str, dirname: str) -> str:
    try:
        validation_error = _validate_path(directory, dirname)
        if validation_error:
            return validation_error
        
        dir_path = os.path.join(directory, dirname)
        
        if not os.path.exists(dir_path):
            return f"Error: Directory '{dirname}' does not exist in '{directory}'."
        
        if not os.path.isdir(dir_path):
            return f"Error: '{dirname}' is not a directory."
        
        import shutil
        shutil.rmtree(dir_path)
        return f"Successfully deleted directory '{dirname}' from '{directory}'."
    except Exception as e:
        return f"Error deleting directory: {str(e)}"


def create_file(directory: str, filename: str, content: str = "") -> str:
    try:
        validation_error = _validate_path(directory, filename)
        if validation_error:
            return validation_error
        
        file_path = os.path.join(directory, filename)
        
        if os.path.exists(file_path):
            return f"Error: File '{filename}' already exists in '{directory}'."
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully created file '{filename}' in '{directory}' with content."
    except Exception as e:
        return f"Error creating file: {str(e)}"


def read_file(directory: str, filename: str) -> str:
    try:
        validation_error = _validate_path(directory, filename)
        if validation_error:
            return validation_error
        
        file_path = os.path.join(directory, filename)
        
        if not os.path.exists(file_path):
            return f"Error: File '{filename}' does not exist in '{directory}'."
        
        if os.path.isdir(file_path):
            return f"Error: '{filename}' is a directory, not a file."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        total_lines = len(lines)
        header = f"=== {filename} ({total_lines} lines) ==="
        return f"{header}\n{content}\n{'=' * len(header)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def search_file_content(directory: str, keyword: str, filename: str = None) -> str:
    try:
        validation_error = _validate_path(directory)
        if validation_error:
            return validation_error
        if filename:
            validation_error = _validate_path(directory, filename)
            if validation_error:
                return validation_error
        
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' does not exist."
        
        if not os.path.isdir(directory):
            return f"Error: '{directory}' is not a directory."
        
        matches = []
        max_results = 50
        
        if filename:
            file_path = os.path.join(directory, filename)
            if not os.path.exists(file_path):
                return f"Error: File '{filename}' does not exist in '{directory}'."
            if os.path.isdir(file_path):
                return f"Error: '{filename}' is a directory."
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if keyword.lower() in line.lower():
                        matches.append(f"{filename}:{line_num}:{line.rstrip()}")
                        if len(matches) >= max_results:
                            break
        else:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, directory)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if keyword.lower() in line.lower():
                                    matches.append(f"{rel_path}:{line_num}:{line.rstrip()}")
                                    if len(matches) >= max_results:
                                        break
                    except:
                        continue
                    
                    if len(matches) >= max_results:
                        break
                
                if len(matches) >= max_results:
                    break
        
        if not matches:
            return f"No matches found for '{keyword}' in '{directory}'."
        
        result = f"Found {len(matches)} matches for '{keyword}':\n"
        result += "=" * 60 + "\n"
        result += "\n".join(matches)
        
        if filename is None:
            result += f"\n[Showing {len(matches)} of many matches]"
        
        return result
    except Exception as e:
        return f"Error searching: {str(e)}"


FILE_TOOL_FUNCTIONS = {
    "list_files": list_files,
    "rename_file": rename_file,
    "delete_file": delete_file,
    "delete_directory": delete_directory,
    "create_file": create_file,
    "read_file": read_file,
    "search_file_content": search_file_content,
}
