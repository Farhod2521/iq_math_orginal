import requests

headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json"
}

json_data = {
    "model": "openai/gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "What is the meaning of life?"
        }
    ]
}

response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=json_data)

print(response.json())
