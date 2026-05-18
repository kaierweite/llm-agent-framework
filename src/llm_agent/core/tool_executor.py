"""
工具调用执行器 —— 从 ChatEngine 中拆分出来的独立模块。

职责：
- 解析 LLM 响应中的 <function_calls> 标签
- 单工具执行（带超时、回调、耗时统计）
- 多工具并行执行（ThreadPoolExecutor）
- 工具调用结果收集器
"""

import json
import re
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Callable, Optional

# 工具调用统一超时（秒）
TOOL_TIMEOUT = 30

# 多轮工具调用安全防护
MAX_TOOL_ROUNDS = 5
MAX_TOTAL_TOOL_TIME = 120


def parse_tool_call(response: str) -> tuple:
    """从 LLM 响应中解析 <function_calls> 标签，返回 (tool_calls, clean_response)。"""
    tool_calls = []
    clean_response = response

    function_call_pattern = r'<function_calls>\s*(\[.*?\])\s*</function_calls>'
    match = re.search(function_call_pattern, response, re.DOTALL)

    if match:
        try:
            raw = json.loads(match.group(1))
            if isinstance(raw, list):
                tool_calls = [tc for tc in raw if isinstance(tc, dict) and 'name' in tc]
            clean_response = response[:match.start()].strip()
        except json.JSONDecodeError:
            pass

    return tool_calls, clean_response


def execute_single_tool(
    tool_call: dict,
    tool_functions: dict,
    on_tool_start: Optional[Callable] = None,
    on_tool_result: Optional[Callable] = None,
    tool_calls_collector: Optional[list] = None,
) -> str:
    """执行单个工具调用，返回结果字符串。"""
    tool_name = tool_call.get('name')
    parameters = tool_call.get('parameters', {})
    tool_call_id = f"tc_{int(time.time() * 1000)}_{tool_name}"
    started_at = time.time()

    if tool_name not in tool_functions:
        error_msg = f"[{tool_name}] 工具未找到"
        if on_tool_result:
            on_tool_result(tool_name, error_msg, False, tool_call_id=tool_call_id)
        if tool_calls_collector is not None:
            tool_calls_collector.append({
                "id": tool_call_id, "name": tool_name, "arguments": parameters,
                "result": error_msg, "status": "error",
                "started_at": datetime.fromtimestamp(started_at).isoformat(),
                "completed_at": datetime.fromtimestamp(started_at).isoformat(),
                "duration_ms": 0,
            })
        return error_msg

    if on_tool_start:
        on_tool_start(tool_name, parameters, tool_call_id=tool_call_id)

    tool_func = tool_functions[tool_name]
    try:
        result = tool_func(**parameters) if parameters else tool_func()
        completed_at = time.time()
        if on_tool_result:
            on_tool_result(tool_name, f"[{tool_name}] {result}", True, tool_call_id=tool_call_id)
        if tool_calls_collector is not None:
            tool_calls_collector.append({
                "id": tool_call_id, "name": tool_name, "arguments": parameters,
                "result": str(result)[:500], "status": "success",
                "started_at": datetime.fromtimestamp(started_at).isoformat(),
                "completed_at": datetime.fromtimestamp(completed_at).isoformat(),
                "duration_ms": int((completed_at - started_at) * 1000),
            })
        return f"[{tool_name}] {result}"
    except Exception as e:
        completed_at = time.time()
        error_msg = f"[{tool_name}] 错误: {str(e)}"
        if on_tool_result:
            on_tool_result(tool_name, error_msg, False, tool_call_id=tool_call_id)
        if tool_calls_collector is not None:
            tool_calls_collector.append({
                "id": tool_call_id, "name": tool_name, "arguments": parameters,
                "result": error_msg, "status": "error",
                "started_at": datetime.fromtimestamp(started_at).isoformat(),
                "completed_at": datetime.fromtimestamp(completed_at).isoformat(),
                "duration_ms": int((completed_at - started_at) * 1000),
            })
        return error_msg


def execute_tool_calls(
    tool_calls: list,
    tool_functions: dict,
    on_tool_start: Optional[Callable] = None,
    on_tool_result: Optional[Callable] = None,
    tool_calls_collector: Optional[list] = None,
) -> str:
    """执行一批工具调用（单工具直接执行，多工具并行），返回拼接结果。"""
    if len(tool_calls) == 1:
        return execute_single_tool(tool_calls[0], tool_functions, on_tool_start, on_tool_result, tool_calls_collector)

    with ThreadPoolExecutor(max_workers=min(len(tool_calls), 5)) as pool:
        futures = [
            pool.submit(execute_single_tool, call, tool_functions, on_tool_start, on_tool_result, tool_calls_collector)
            for call in tool_calls
        ]
        results = []
        for i, f in enumerate(futures):
            try:
                results.append(f.result(timeout=TOOL_TIMEOUT))
            except FuturesTimeoutError:
                tool_name = tool_calls[i].get("name", "unknown")
                error_msg = f"[{tool_name}] 错误: 工具执行超时（超过 {TOOL_TIMEOUT} 秒）"
                if on_tool_result:
                    on_tool_result(tool_name, error_msg, False)
                if tool_calls_collector is not None:
                    tool_calls_collector.append({
                        "id": f"tc_timeout_{int(time.time() * 1000)}_{tool_name}",
                        "name": tool_name,
                        "arguments": tool_calls[i].get("parameters", {}),
                        "result": error_msg, "status": "timeout",
                        "started_at": datetime.now().isoformat(),
                        "completed_at": datetime.now().isoformat(),
                        "duration_ms": TOOL_TIMEOUT * 1000,
                    })
                results.append(error_msg)

    return "\n\n".join(results)


async def execute_tool_calls_async(
    tool_calls: list,
    tool_functions: dict,
    on_tool_start: Optional[Callable] = None,
    on_tool_result: Optional[Callable] = None,
    tool_calls_collector: Optional[list] = None,
) -> str:
    """异步版本：在事件循环的线程池中执行工具调用。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: execute_tool_calls(tool_calls, tool_functions, on_tool_start, on_tool_result, tool_calls_collector),
    )
