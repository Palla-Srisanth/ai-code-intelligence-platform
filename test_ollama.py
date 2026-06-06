import requests

url = "http://localhost:11434/api/generate"

payload = {
    "model": "phi3:mini",
    "prompt": "Say hello in one sentence.",
    "stream": False
}

response = requests.post(url, json=payload)

print(response.json())