"""
update_long_term_memory 规则层 —— 高置信度正则提取。

规则存储在 JSON 配置文件中，支持热加载（MD5 哈希检测变更）。

配置文件路径：{PROJECT_ROOT}/memory_rules.json
"""

from __future__ import annotations

import json
import os
import re
import hashlib
import threading
from typing import List, Dict, Any, Optional

from llm_agent import PROJECT_ROOT
from llm_agent.core.redis_history import RedisChatHistory

# ── 默认规则 ──────────────────────────────────────────────────────────
DEFAULT_RULES: Dict[str, List[Dict[str, Any]]] = {
    "preference_rules": [
        {
            "pattern": r"以后都用(.+)",
            "action": "set_pref",
            "key_group": 1,
            "pref_key": "default_style",
        },
        {
            "pattern": r"以后用(.+)",
            "action": "set_pref",
            "key_group": 1,
            "pref_key": "default_style",
        },
        {
            "pattern": r"不要(.+?)了",
            "action": "remove_pref",
            "key_group": 1,
        },
        {
            "pattern": r"不再(.+)",
            "action": "remove_pref",
            "key_group": 1,
        },
        {
            "pattern": r"记住我的(.+?)是(.+)",
            "action": "set_fact",
            "key_group": 1,
            "value_group": 2,
        },
        {
            "pattern": r"记住(.+)",
            "action": "set_fact",
            "key_group": 1,
            "value_group": 1,
        },
    ],
    "task_rules": [
        {
            "pattern": r"帮我(.+)",
            "action": "add_task",
            "task_group": 1,
        },
        {
            "pattern": r"请(.+)",
            "action": "add_task",
            "task_group": 1,
        },
        {
            "pattern": r"取消(.+?)任务",
            "action": "remove_task",
            "task_group": 1,
        },
        {
            "pattern": r"不用(.+?)了",
            "action": "remove_task",
            "task_group": 1,
        },
    ],
}

RULES_FILE = os.path.join(PROJECT_ROOT, "memory_rules.json")


class MemoryRuleEngine:
    """
    基于规则的长期记忆提取引擎。

    用法：
        engine = MemoryRuleEngine()
        engine.process(user_message, history)
    """

    def __init__(self, rules_path: str = RULES_FILE):
        self.rules_path = rules_path
        self._rules_hash: Optional[str] = None
        self._rules: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()
        self._load_rules()

    def _load_rules(self):
        """加载规则文件，若不存在则使用默认规则并创建文件。"""
        if os.path.exists(self.rules_path):
            with open(self.rules_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._rules_hash = hashlib.md5(content.encode()).hexdigest()
            self._rules = json.loads(content)
        else:
            self._rules = DEFAULT_RULES.copy()
            self._save_rules()

    def _save_rules(self):
        """保存当前规则到文件。"""
        content = json.dumps(self._rules, ensure_ascii=False, indent=2)
        self._rules_hash = hashlib.md5(content.encode()).hexdigest()
        with open(self.rules_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _check_reload(self):
        """检查规则文件是否变更，变更则重新加载。"""
        if not os.path.exists(self.rules_path):
            return
        with open(self.rules_path, "r", encoding="utf-8") as f:
            content = f.read()
        new_hash = hashlib.md5(content.encode()).hexdigest()
        if new_hash != self._rules_hash:
            with self._lock:
                self._rules = json.loads(content)
                self._rules_hash = new_hash

    def process(self, user_message: str, history: RedisChatHistory) -> bool:
        """
        处理用户消息，提取偏好/事实/任务并更新 Redis。

        返回：是否有任何更新发生。
        """
        self._check_reload()
        updated = False

        # 处理偏好规则
        for rule in self._rules.get("preference_rules", []):
            match = re.search(rule["pattern"], user_message)
            if not match:
                continue

            action = rule["action"]

            if action == "set_pref":
                key = rule.get("pref_key", "general")
                # 如果有 key_group，用匹配组作为 key
                if "key_group" in rule:
                    key = match.group(rule["key_group"]).strip()
                value = match.group(rule.get("value_group", 1)).strip() if "value_group" in rule else "true"
                history.set_pref(key, value)
                updated = True

            elif action == "remove_pref":
                key = match.group(rule["key_group"]).strip()
                history.remove_pref(key)
                updated = True

            elif action == "set_fact":
                key = match.group(rule["key_group"]).strip()
                if "value_group" in rule:
                    value = match.group(rule["value_group"]).strip()
                else:
                    value = "true"
                history.set_fact(key, value)
                updated = True

            elif action == "remove_fact":
                key = match.group(rule["key_group"]).strip()
                history.remove_fact(key)
                updated = True

        # 处理任务规则
        for rule in self._rules.get("task_rules", []):
            match = re.search(rule["pattern"], user_message)
            if not match:
                continue

            action = rule["action"]

            if action == "add_task":
                task = match.group(rule["task_group"]).strip()
                history.add_pending(task)
                updated = True

            elif action == "remove_task":
                task = match.group(rule["task_group"]).strip()
                # 尝试模糊匹配已有任务
                pending = history.get_pending()
                for existing in pending:
                    if task in existing or existing in task:
                        history.remove_pending(existing)
                updated = True

        return updated
