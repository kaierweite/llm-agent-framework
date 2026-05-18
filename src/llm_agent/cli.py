import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

import json
import signal

from llm_agent import PROJECT_ROOT
from llm_agent.core.agent import ChatClientWithSkills
from llm_agent.tools import list_available_skills


def signal_handler(sig, frame):
    print("\n\nGoodbye!")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    env_path = os.path.join(PROJECT_ROOT, '.env')
    chat = ChatClientWithSkills(env_path)

    if not chat.base_url or not chat.api_key or not chat.model:
        print("Error: Missing required environment variables in .env file")
        print("Please copy env.example to .env and fill in the values")
        return

    print("=" * 50)
    print("  AI Chat Client with Skills")
    print(f"  Model: {chat.model}")
    print("=" * 50)
    print("功能特性:")
    print("  - 技能调用功能（load_skill_content）")
    print("  - 超过20轮对话时自动压缩")
    print("  - 上下文超过30000字符时自动压缩")
    print("  - JSONL 格式日志（含会话ID、时间戳）")
    print("  - 支持 /search 命令搜索聊天历史")
    print("  - AnythingLLM 知识库查询")
    print("  - 流式输出，逐字显示")
    print("=" * 50)
    status = chat.get_status()
    print(f"日志文件目录: {status['log_dir']}")
    print("=" * 50)
    print("Available tools:")
    for tool_name in chat.tool_functions.keys():
        print(f"  - {tool_name}")
    print("=" * 50)

    skills_json = list_available_skills()
    try:
        skills_data = json.loads(skills_json)
        skills_list = skills_data.get('skills', [])
        if skills_list:
            print("\n可用技能:")
            for skill in skills_list:
                print(f"  - {skill.get('name')}: {skill.get('description', '')[:50]}...")
    except json.JSONDecodeError:
        pass

    print("=" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() == 'clear':
                chat.clear_history()
                chat.clear_skill()
                print("Conversation history cleared.")
                continue

            if user_input.lower() == 'quit' or user_input.lower() == 'exit':
                print("Goodbye!")
                break

            if user_input.lower() == 'status':
                status = chat.get_status()
                rounds = len(status['conversation_history']) // 2
                length = status['context_length']
                print(f"\n当前对话状态:")
                print(f"  对话轮次: {rounds} 轮")
                print(f"  上下文长度: {length} 字符")
                print(f"  是否达到压缩条件: {'是' if status['should_summarize'] else '否'}")
                print(f"  日志目录: {status['log_dir']}")
                print(f"  当前激活技能: {'是' if status['has_skill'] else '否'}")
                continue

            if user_input.lower() == 'skill':
                chat.clear_skill()
                print("技能已清除。")
                continue

            use_search = chat.should_use_search(user_input)

            if use_search:
                query = user_input
                if query.startswith('/search'):
                    query = query[7:].strip()

                print("\n[检测到搜索请求，正在搜索聊天历史...]")
                log_content = chat.search_history(query)
                print(f"\n{log_content}\n")

                user_input_with_context = f"""请根据以下聊天历史记录回答用户的问题。

用户的问题是：{query}

聊天历史记录：
{log_content}

请根据以上信息回答用户的问题。如果聊天历史中没有相关信息，请如实告知用户。"""

                response = chat.stream_chat(user_input_with_context)
                tool_calls, clean_response = chat.parse_tool_call(response)

                if tool_calls:
                    chat.handle_tool_calls_and_respond(user_input, tool_calls, clean_response)
                else:
                    clean_response = chat.llm.strip_tool_call_tags(clean_response)
                    print(f"\n{clean_response}")
                    chat.add_to_history(user_input, clean_response)
            else:
                response = chat.stream_chat(user_input)
                tool_calls, clean_response = chat.parse_tool_call(response)

                if tool_calls:
                    chat.handle_tool_calls_and_respond(user_input, tool_calls, clean_response)
                else:
                    clean_response = chat.llm.strip_tool_call_tags(clean_response)
                    print(f"\n{clean_response}")
                    chat.add_to_history(user_input, clean_response)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == '__main__':
    main()
