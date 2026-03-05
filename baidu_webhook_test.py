import requests
import json

# Configuration
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
                "content": "[Python Test] 这是来自 Python 脚本的测试消息"
            }
        ]
    }
}

# Send the request
print('Sending message to Baidu webhook...')
print(f'Webhook URL: {WEBHOOK_URL}')
print(f'Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}')
print('-' * 50)

try:
    response = requests.post(
        WEBHOOK_URL,
        headers={'Content-Type': 'application/json'},
        json=payload,
        timeout=10
    )
    
    print(f'Status Code: {response.status_code}')
    print(f'Response Headers: {dict(response.headers)}')
    print('-' * 50)
    print('Response Body:')
    
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(response.text)
    
    if response.status_code == 200:
        print('\n✓ Message sent successfully!')
    else:
        print(f'\n✗ Request failed with status code: {response.status_code}')
        
except requests.exceptions.RequestException as e:
    print(f'Error: {e}')
