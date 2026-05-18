import os
import re
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from threading import Lock

from llm_agent import PROJECT_ROOT

NETWORK_TOOL_DEFINITIONS = {
    "curl_network_request": {
        "type": "function",
        "function": {
            "name": "curl_network_request",
            "description": "通过curl方式访问网页并获取返回内容，支持GET/POST等HTTP方法",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要访问的网页URL地址"},
                    "method": {"type": "string", "description": "HTTP请求方法，如GET、POST等，默认为GET"},
                    "headers": {"type": "object", "description": "HTTP请求头，默认为空字典"},
                    "data": {"type": "string", "description": "POST请求时发送的数据，默认为空"}
                },
                "required": ["url"]
            }
        }
    },
    "get_weather": {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的天气预报",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "要查询天气的城市名称（支持中文城市名，如'成都'、'达州'、'青城山'等）"}
                },
                "required": ["city"]
            }
        }
    },
}

CITY_PINYIN_MAP = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "成都": "Chengdu",
    "重庆": "Chongqing",
    "杭州": "Hangzhou",
    "武汉": "Wuhan",
    "西安": "Xian",
    "南京": "Nanjing",
    "天津": "Tianjin",
    "苏州": "Suzhou",
    "郑州": "Zhengzhou",
    "长沙": "Changsha",
    "沈阳": "Shenyang",
    "青岛": "Qingdao",
    "宁波": "Ningbo",
    "东莞": "Dongguan",
    "无锡": "Wuxi",
    "昆明": "Kunming",
    "大连": "Dalian",
    "厦门": "Xiamen",
    "福州": "Fuzhou",
    "济南": "Jinan",
    "温州": "Wenzhou",
    "常州": "Changzhou",
    "徐州": "Xuzhou",
    "佛山": "Foshan",
    "南通": "Nantong",
    "唐山": "Tangshan",
    "保定": "Baoding",
    "邯郸": "Handan",
    "绍兴": "Shaoxing",
    "潍坊": "Weifang",
    "临沂": "Linyi",
    "淄博": "Zibo",
    "烟台": "Yantai",
    "洛阳": "Luoyang",
    "襄阳": "Xiangyang",
    "宜昌": "Yichang",
    "荆州": "Jingzhou",
    "衡阳": "Hengyang",
    "遵义": "Zunyi",
    "绵阳": "Mianyang",
    "南充": "Nanchong",
    "达州": "Dazhou",
    "乐山": "Leshan",
    "眉山": "Meishan",
    "德阳": "Deyang",
    "广元": "Guangyuan",
    "遂宁": "Suining",
    "内江": "Neijiang",
    "自贡": "Zigong",
    "泸州": "Luzhou",
    "宜宾": "Yibin",
    "攀枝花": "Panzhihua",
    "资阳": "Ziyang",
    "雅安": "Ya'an",
    "广安": "Guang'an",
    "巴中": "Bazhong",
    "阿坝": "Aba",
    "甘孜": "Ganzi",
    "凉山": "Liangshan",
    "青城山": "Qingchengshan",
    "都江堰": "Dujiangyan",
    "九寨沟": "Jiuzhaigou",
    "稻城": "Daocheng",
    "亚丁": "Yading",
    "康定": "Kangding",
    "四姑娘山": "Siguniangshan",
    "峨眉山": "Emeishan",
    "乐山大佛": "Leshan",
}

WEATHER_EN_TO_CN = {
    "Sunny": "晴天",
    "Clear": "晴朗",
    "Partly cloudy": "多云",
    "Cloudy": "阴天",
    "Overcast": "阴",
    "Mist": "薄雾",
    "Fog": "雾",
    "Rain": "雨",
    "Light rain": "小雨",
    "Moderate rain": "中雨",
    "Heavy rain": "大雨",
    "Thunderstorm": "雷雨",
    "Snow": "雪",
    "Light snow": "小雪",
    "Patchy light drizzle": "零星小雨",
    "Patchy rain possible": "可能有雨",
}

CACHE_EXPIRE_SECONDS = 600
_weather_cache = {}
_cache_lock = Lock()


def _get_cache_key(city: str) -> str:
    return city.lower()


def _is_cache_valid(cache_entry: dict) -> bool:
    if not cache_entry:
        return False
    timestamp = cache_entry.get('timestamp', 0)
    return (datetime.now().timestamp() - timestamp) < CACHE_EXPIRE_SECONDS


def get_weather(city: str) -> str:
    cache_key = _get_cache_key(city)
    
    with _cache_lock:
        if cache_key in _weather_cache and _is_cache_valid(_weather_cache[cache_key]):
            cached_result = _weather_cache[cache_key]['result']
            return cached_result + "\n[数据来自缓存]"
    
    pinyin_name = CITY_PINYIN_MAP.get(city, city)
    
    try:
        url = f"https://wttr.in/{urllib.parse.quote(pinyin_name)}?format=j1"
        
        req = urllib.request.Request(url, method='GET')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode('utf-8', errors='replace'))
            
            current_conditions = data.get('current_condition', [])
            current = current_conditions[0] if current_conditions else {}
            weather_desc_list = current.get('weatherDesc', [])
            weather_desc = weather_desc_list[0] if weather_desc_list else {}
            desc_en = weather_desc.get('value', '未知')
            desc_cn = WEATHER_EN_TO_CN.get(desc_en, desc_en)
            
            temp_C = current.get('temp_C', '?')
            feelsLike_C = current.get('FeelsLikeC', '?')
            humidity = current.get('humidity', '?')
            wind_Kmph = current.get('windspeedKmph', '?')
            
            weather_list = data.get('weather', [])
            tomorrow = weather_list[1] if len(weather_list) > 1 else {}
            tomorrow_max = tomorrow.get('maxtempC', '?') if tomorrow else '?'
            tomorrow_min = tomorrow.get('mintempC', '?') if tomorrow else '?'
            tomorrow_hourly = tomorrow.get('hourly', []) if tomorrow else []
            if len(tomorrow_hourly) > 4:
                tomorrow_desc_list = tomorrow_hourly[4].get('weatherDesc', [])
                tomorrow_desc_en = tomorrow_desc_list[0].get('value', desc_en) if tomorrow_desc_list else desc_en
            else:
                tomorrow_desc_en = desc_en
            tomorrow_desc_cn = WEATHER_EN_TO_CN.get(tomorrow_desc_en, tomorrow_desc_en)
            
            lines = [
                f"📍 {city} 天气预报",
                "=" * 30,
                f"🌡️ 当前温度: {temp_C}°C（体感 {feelsLike_C}°C）",
                f"☁️ 天气状况: {desc_cn}",
                f"💧 湿度: {humidity}%",
                f"🌬️ 风速: {wind_Kmph} km/h",
                "-" * 30,
                f"📅 明天天气预报",
                f"   气温: {tomorrow_min}°C ~ {tomorrow_max}°C",
                f"   天气: {tomorrow_desc_cn}",
            ]
            result = "\n".join(lines)
            
            with _cache_lock:
                _weather_cache[cache_key] = {
                    'result': result,
                    'timestamp': datetime.now().timestamp()
                }
            
            return result
            
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}\n城市 {city} 查询失败，请尝试使用拼音或英文名称。"
    except urllib.error.URLError as e:
        return f"网络错误: {str(e.reason)}\n请检查网络连接后重试。"
    except Exception as e:
        return f"查询天气失败: {str(e)}"


def _extract_html_text(html: str) -> str:
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<noscript[^>]*>.*?</noscript>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = re.sub(r'&nbsp;', ' ', cleaned)
    cleaned = re.sub(r'&lt;', '<', cleaned)
    cleaned = re.sub(r'&gt;', '>', cleaned)
    cleaned = re.sub(r'&amp;', '&', cleaned)
    cleaned = re.sub(r'&#?\w+;', '', cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return '\n'.join(lines)


def _is_safe_url(url: str) -> bool:
    try:
        import ipaddress
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ''
        if hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return True


def curl_network_request(url: str, method: str = "GET", headers: dict = None, data: str = None) -> str:
    if not _is_safe_url(url):
        return f"Error: Access to internal/private addresses is not allowed: {url}"
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc:
            netloc = parsed.netloc.encode('idna').decode('ascii')
            path = urllib.parse.quote(urllib.parse.unquote(parsed.path))
            query = urllib.parse.quote(urllib.parse.unquote(parsed.query))
            url = urllib.parse.urlunparse((parsed.scheme, netloc, path, parsed.params, query, parsed.fragment))
        
        req = urllib.request.Request(url, method=method)
        
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        
        if data:
            if isinstance(data, str):
                data = data.encode('utf-8')
            req.data = data
        
        with urllib.request.urlopen(req, timeout=180) as response:
            status_code = response.status
            response_headers = dict(response.headers)
            body = response.read().decode('utf-8', errors='replace')

            content_type = response_headers.get('Content-Type', '').lower()
            is_html = 'text/html' in content_type or '<html' in body[:1000].lower()

            lines = [f"HTTP Status: {status_code}", "Response Headers:"]
            for key, value in response_headers.items():
                lines.append(f"  {key}: {value}")

            if is_html:
                text = _extract_html_text(body)
                lines.append("")
                lines.append("网页正文内容:")
                lines.append("=" * 80)
                if len(text) > 10000:
                    lines.append(text[:10000])
                    lines.append(f"... (truncated, total length: {len(text)} chars)")
                else:
                    lines.append(text)
            else:
                lines.append("")
                lines.append("Response Body:")
                lines.append("=" * 80)
                if len(body) > 5000:
                    lines.append(body[:5000])
                    lines.append(f"... (truncated, total length: {len(body)} bytes)")
                else:
                    lines.append(body)

            return "\n".join(lines)
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}\nError details: {str(e)}"
    except urllib.error.URLError as e:
        return f"URL Error: {str(e.reason)}"
    except Exception as e:
        return f"Error: {str(e)}"


def query_anythingllm(message: str, api_key: str, workspace_slug: str) -> str:
    if not api_key:
        return "错误: 未配置 ANYTHINGLLM_API_KEY 环境变量"
    if not workspace_slug:
        return "错误: 未配置 ANYTHINGLLM_WORKSPACE_SLUG 环境变量"

    json_data = json.dumps({
        "message": message,
        "mode": "query",
        "enable_thinking": False
    }).encode('utf-8')

    url = f'http://localhost:3001/api/v1/workspace/{workspace_slug}/chat'
    try:
        req = urllib.request.Request(url, data=json_data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')

        with urllib.request.urlopen(req, timeout=180) as response:
            if response.status != 200:
                return f"HTTP请求失败: {response.status}"
            response_text = response.read().decode('utf-8', errors='replace')

        try:
            response_json = json.loads(response_text)
            if 'error' in response_json and response_json['error']:
                return f"API错误: {response_json['error']}"
            if 'textResponse' in response_json:
                return response_json['textResponse']
            elif 'response' in response_json:
                return response_json['response']
            else:
                return f"未知响应格式: {response_text}"
        except json.JSONDecodeError:
            return f"解析响应失败: {response_text}"

    except urllib.error.HTTPError as e:
        return f"HTTP请求失败: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"连接失败: {str(e.reason)}"
    except Exception as e:
        return f"查询失败: {str(e)}"


def list_anythingllm_documents(api_key: str, workspace_slug: str) -> str:
    if not api_key:
        return "错误: 未配置 ANYTHINGLLM_API_KEY 环境变量"
    if not workspace_slug:
        return "错误: 未配置 ANYTHINGLLM_WORKSPACE_SLUG 环境变量"

    url = f'http://localhost:3001/api/v1/workspace/{workspace_slug}'
    try:
        req = urllib.request.Request(url, method='GET')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('Accept', 'application/json')

        with urllib.request.urlopen(req, timeout=180) as response:
            if response.status != 200:
                return f"HTTP请求失败: {response.status}"
            response_text = response.read().decode('utf-8', errors='replace')

        try:
            response_json = json.loads(response_text)
            if 'error' in response_json:
                return f"API错误: {response_json['error']}"

            workspace_data = response_json.get('workspace', [])
            if not workspace_data:
                return f"未找到工作区 '{workspace_slug}'"

            documents = workspace_data[0].get('documents', []) if isinstance(workspace_data, list) else workspace_data.get('documents', [])
            if not documents:
                return f"工作区 '{workspace_slug}' 中没有文档。请先在 AnythingLLM 中添加文档到该工作区。"

            result_text = f"工作区 '{workspace_slug}' 中的文档列表：\n\n"
            for i, doc in enumerate(documents, 1):
                metadata = json.loads(doc.get('metadata', '{}')) if doc.get('metadata') else {}
                title = metadata.get('title', doc.get('filename', '未知'))
                result_text += f"{i}. {title}\n"
            return result_text

        except json.JSONDecodeError:
            return f"解析响应失败: {response_text}"

    except urllib.error.HTTPError as e:
        return f"HTTP请求失败: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"连接失败: {str(e.reason)}"
    except Exception as e:
        return f"查询失败: {str(e)}"


NETWORK_TOOL_FUNCTIONS = {
    "curl_network_request": curl_network_request,
    "get_weather": get_weather,
}
