import tempfile
import subprocess
import os
import requests
import re

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_ai(prompt):
    payload = {
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 150,
            "temperature": 0.2
        }
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return r.json().get("response", "AI failed")
    except:
        return "AI connection error"


def extract_repo_info(url):
    match = re.match(r"https://github.com/([^/]+)/([^/]+)", url)
    if not match:
        return None

    user, repo = match.groups()
    repo = repo.replace(".git", "")
    return f"https://github.com/{user}/{repo}.git"


def extract_important_code(text):
    lines = text.splitlines()
    important = []

    for line in lines:
        if (
            "import " in line
            or "def " in line
            or "class " in line
        ):
            important.append(line)

    return "\n".join(important)[:2000]


def analyze_repo_logic(github_url):

    repo_url = extract_repo_info(github_url)

    if not repo_url:
        return "Invalid GitHub URL"

    with tempfile.TemporaryDirectory() as tmpdir:

        result = subprocess.run(
            ["git", "-c", "credential.helper=", "clone", "--depth", "1", repo_url],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return result.stderr

        repo_folder = os.listdir(tmpdir)[0]
        repo_path = os.path.join(tmpdir, repo_folder)

        combined = ""

        for root, _, files in os.walk(repo_path):
            for f in files:
                if f.endswith(".py"):
                    try:
                        with open(os.path.join(root, f), "r", errors="ignore") as file:
                            combined += extract_important_code(file.read())
                    except:
                        pass

        combined = combined[:3000]

        if len(combined.strip()) < 100:
            return "Not enough code to analyze"

        prompt = f"""
Analyze this project:

1. What it does
2. Technologies used
3. Main components

Code:
{combined}
"""

        return ask_ai(prompt)