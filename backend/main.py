from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

# ✅ CORS (frontend connection fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    url: str


# 🔥 AI ANALYSIS (STRICT + CLEAN OUTPUT)
def analyze_repo_data(description, language, topics):
    try:
        prompt = f"""
You are a strict software analyzer.

Convert this GitHub repo info into EXACT format:

Project: <one line>
Tech Stack: <comma separated>
Main Feature: <one line>

Repo Info:
Description: {description}
Language: {language}
Topics: {topics}

Rules:
- Do NOT repeat input
- Do NOT add extra text
- Output ONLY 3 lines
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 60,
                    "temperature": 0.1
                }
            },
            timeout=40
        )

        output = response.json().get("response", "").strip()

        # 🔥 fallback if model fails
        if "Project:" not in output:
            return f"""Project: {description}
Tech Stack: {language}
Main Feature: Based on repository topics ({topics})"""

        return output

    except Exception as e:
        return f"❌ Ollama error: {str(e)}"


# 🚀 MAIN API
@app.post("/analyze")
def analyze_repo(data: RepoRequest):
    try:
        repo_url = data.url.strip()

        # ✅ Validate URL
        if "github.com" not in repo_url:
            return {"result": "❌ Invalid GitHub URL"}

        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]

        # 🔥 Extract owner/repo
        parts = repo_url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            return {"result": "❌ Invalid GitHub repo"}

        owner, repo = parts[0], parts[1]

        # 🔥 GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url)

        if response.status_code != 200:
            return {"result": "❌ Repo not found or private"}

        repo_data = response.json()

        description = repo_data.get("description", "No description")
        language = repo_data.get("language", "Unknown")
        topics = ", ".join(repo_data.get("topics", []))

        # 🔥 AI processing
        result = analyze_repo_data(description, language, topics)

        return {"result": result}

    except Exception as e:
        return {"result": f"❌ Error: {str(e)}"}