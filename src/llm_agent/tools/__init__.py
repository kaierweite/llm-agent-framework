from .file_tools import (
    list_files,
    rename_file,
    delete_file,
    delete_directory,
    create_file,
    read_file,
    search_file_content,
    FILE_TOOL_DEFINITIONS,
    FILE_TOOL_FUNCTIONS,
)
from .network_tools import (
    curl_network_request,
    get_weather,
    query_anythingllm,
    list_anythingllm_documents,
    NETWORK_TOOL_DEFINITIONS,
    NETWORK_TOOL_FUNCTIONS,
)
from .skill_tools import (
    list_available_skills,
    load_skill_content,
    SKILL_TOOL_DEFINITIONS,
    SKILL_TOOL_FUNCTIONS,
)

TOOL_DEFINITIONS = {}
TOOL_DEFINITIONS.update(FILE_TOOL_DEFINITIONS)
TOOL_DEFINITIONS.update(NETWORK_TOOL_DEFINITIONS)
TOOL_DEFINITIONS.update(SKILL_TOOL_DEFINITIONS)

TOOL_FUNCTIONS = {}
TOOL_FUNCTIONS.update(FILE_TOOL_FUNCTIONS)
TOOL_FUNCTIONS.update(NETWORK_TOOL_FUNCTIONS)
TOOL_FUNCTIONS.update(SKILL_TOOL_FUNCTIONS)
