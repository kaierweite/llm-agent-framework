import os
import json
import uuid
from datetime import datetime


class ChatLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self._session_id = uuid.uuid4().hex[:8]

    @property
    def session_id(self) -> str:
        return self._session_id

    def _get_log_file_path(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"chat_{today}.jsonl")

    def write_to_log(self, user_input: str, assistant_response: str,
                     tool_calls=None, model=None, usage=None, latency_ms=None):
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            log_file = self._get_log_file_path()

            now = datetime.now().astimezone().isoformat()
            sid = self._session_id

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": now, "sid": sid,
                    "role": "user", "content": user_input
                }, ensure_ascii=False) + "\n")

                entry = {
                    "ts": now, "sid": sid,
                    "role": "assistant", "content": assistant_response
                }
                if tool_calls:
                    entry["tool_calls"] = tool_calls
                if model:
                    entry["model"] = model
                if usage:
                    entry["usage"] = usage
                if latency_ms:
                    entry["latency_ms"] = latency_ms

                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"\nWarning: 写入日志失败: {str(e)}")

    def search_in_log_file(self, query: str) -> str:
        try:
            if not os.path.exists(self.log_dir):
                return f"聊天记录目录不存在: {self.log_dir}"

            results = []
            log_files = sorted(
                [f for f in os.listdir(self.log_dir) if f.endswith(".jsonl")],
                reverse=True
            )

            query_lower = query.lower()
            for log_file in log_files:
                file_path = os.path.join(self.log_dir, log_file)
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            content = entry.get("content", "")
                            if query_lower in content.lower():
                                results.append((log_file, entry))
                        except json.JSONDecodeError:
                            continue

            if not results:
                return f"未找到与 '{query}' 相关的聊天记录"

            result = f"找到 {len(results)} 条相关记录:\n\n"
            for i, (filename, entry) in enumerate(results[:10], 1):
                ts = entry.get("ts", "")
                role = entry.get("role", "")
                content = entry.get("content", "")
                result += f"[{filename}] {ts} ({role}):\n{content}\n\n"

            return result

        except Exception as e:
            return f"搜索聊天记录时出错: {str(e)}"

    def error(self, message: str):
        """记录错误日志（兼容 logging 接口）"""
        print(f"\n[ERROR] {message}")

    def cleanup_old_logs(self, keep_days=30):
        now = datetime.now()
        for f in os.listdir(self.log_dir):
            if f.startswith("chat_") and f.endswith(".jsonl"):
                try:
                    date_str = f[5:15]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if (now - file_date).days > keep_days:
                        os.remove(os.path.join(self.log_dir, f))
                except Exception:
                    pass
