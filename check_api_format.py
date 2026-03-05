import requests
import json

# 使用用户提供的配置
ACCESS_TOKEN = 'db31142ad3bc795d7c9666965cfa30969'
WEBHOOK_URL = f'http://apiin.im.baidu.com/api/msg/groupmsgsend?access_token={ACCESS_TOKEN}'
GROUP_ID = 11917896

# Message payload
payload = {
    "message": {
        "header": {
            "toid": [GROUP_ID]
        },
        "body": [
            {
                "type": "TEXT",
                "content": "[格式测试] 检查API响应格式"
            }
        ]
    }
}

print('发送测试消息...')
print(f'URL: {WEBHOOK_URL}')
print(f'Group ID: {GROUP_ID}')

try:
    response = requests.post(
        WEBHOOK_URL,
        headers={'Content-Type': 'application/json'},
        json=payload,
        timeout=10
    )
    
    print(f'\n状态码: {response.status_code}')
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f'响应JSON: {json.dumps(result, indent=2, ensure_ascii=False)}')
            print('\n字段分析:')
            print(f'  - errcode 字段存在: {"errcode" in result}')
            print(f'  - errcode 值: {result.get("errcode")}')
            print(f'  - errno 字段存在: {"errno" in result}')
            print(f'  - errno 值: {result.get("errno")}')
            print(f'  - errmsg 字段存在: {"errmsg" in result}')
            print(f'  - errmsg 值: {result.get("errmsg")}')
            
            # 检查可能的字段名变体
            print(f'\n所有字段名: {list(result.keys())}')
        except json.JSONDecodeError:
            print(f'响应不是JSON: {response.text}')
    else:
        print(f'响应文本: {response.text}')
        
except Exception as e:
    print(f'错误: {e}')