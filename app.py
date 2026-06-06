import streamlit as st
import requests
import tempfile
import os
import subprocess
import re

st.set_page_config(page_title="AI Code Intelligence Platform", layout="wide")

st.title("🧠 AI Code Intelligence Platform")
st.subheader("Accurate • Offline • Repo Analysis")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"
MAX_OUTPUT = 180


# =========================================================
# 🔥 CLEAN REPO URL + SUBFOLDER
# =========================================================
def extract_repo_info(url):
    match = re.match(r"https://github.com/([^/]+)/([^/]+)", url)

    if not match:
        return None, None

    user, repo = match.groups()

    # Remove .git if already present
    repo = repo.replace(".git", "")

    repo_url = f"https://github.com/{user}/{repo}.git"

    subpath = None

    if "/tree/" in url:
        parts = url.split("/tree/")
        if len(parts) > 1:
            path_part = parts[1]
            if "/" in path_part:
                subpath = path_part.split("/", 1)[1]

    return repo_url, subpath


# =========================================================
# 🔥 AI CALL
# =========================================================
def ask_ai(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": MAX_OUTPUT,
            "temperature": 0.2
        }
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if r.status_code == 200:
            return r.json()["response"]
    except:
        pass

    return "⚠️ AI response failed."


# =========================================================
# 🔥 CODE EXTRACTION
# =========================================================
def extract_important_code(text, max_chars=2500):
    lines = text.splitlines()
    important = []

    for line in lines:
        if (
            line.strip().startswith("import ")
            or line.strip().startswith("from ")
            or "def " in line
            or "class " in line
            or "if __name__" in line
        ):
            important.append(line)

    summary = "\n".join(important)

    if len(summary) < max_chars:
        summary = text[:max_chars]

    return summary[:max_chars]


# =========================================================
# 🔥 ANALYSIS
# =========================================================
def analyze_project(text):
    prompt = f"""
You are analyzing a real software project.

STRICT RULES:
- Do NOT guess randomly
- Use only given context
- If unclear, say "Partially inferred"

Provide:

1. What this project does
2. Technologies used
3. Main components
3. Confidence level (High / Medium / Low)

Code:
{text}
"""
    return ask_ai(prompt)


# =========================================================
# 💬 CHAT
# =========================================================
def chat_with_project(context, question):
    prompt = f"""
Answer ONLY using project context.

If not present, say:
"Not present in analyzed project."

Context:
{context}

Question:
{question}
"""
    return ask_ai(prompt)


# =========================================================
# 🌐 MAIN APP
# =========================================================
github_url = st.text_input("Paste GitHub Repository Link")

if github_url:

    if st.button("🚀 Analyze Repo"):

        repo_url, subpath = extract_repo_info(github_url)

        if not repo_url:
            st.error("❌ Invalid GitHub URL")
            st.stop()

        # Clean URL issues
        repo_url = repo_url.replace(".git.git", ".git").strip()

        st.info("Cloning repository...")

        with tempfile.TemporaryDirectory() as tmpdir:

            # 🔥 FIXED CLONE (NO LOGIN POPUP)
            result = subprocess.run(
                [
                    "git",
                    "-c", "credential.helper=",
                    "clone",
                    "--depth", "1",
                    repo_url
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                st.error("❌ Clone failed")
                st.code(result.stderr)
                st.stop()

            repo_folders = os.listdir(tmpdir)

            if not repo_folders:
                st.error("❌ No repo found after cloning")
                st.stop()

            repo_path = os.path.join(tmpdir, repo_folders[0])

            # Handle subfolder
            if subpath:
                repo_path = os.path.join(repo_path, subpath)

                if not os.path.exists(repo_path):
                    st.error("❌ Subfolder not found")
                    st.stop()

            st.success("✅ Repository loaded successfully")

            combined = ""

            ALLOWED = (".py", ".js", ".ts", ".java", ".cpp", ".c")
            IGNORE = ("venv", "node_modules", ".git", "__pycache__", "dist", "build")

            IMPORTANT_FILES = ("app.py", "main.py", "index.js", "server.py")

            files_scanned = 0
            MAX_FILES = 12

            progress = st.progress(0)

            for root, dirs, files in os.walk(repo_path):

                dirs[:] = [d for d in dirs if d not in IGNORE]

                for f in files:

                    if files_scanned >= MAX_FILES:
                        break

                    path = os.path.join(root, f)

                    try:

                        # README boost
                        if f.lower() == "readme.md":
                            with open(path, "r", errors="ignore") as file:
                                readme = file.read()
                                combined += f"\n\nREADME:\n{readme[:1500]}"

                        elif f in IMPORTANT_FILES and f.endswith(ALLOWED):
                            with open(path, "r", errors="ignore") as file:
                                content = file.read()
                                important = extract_important_code(content)

                                combined += f"\n\nFile: {f}\n{important}"
                                files_scanned += 1

                        elif f.endswith(ALLOWED):
                            with open(path, "r", errors="ignore") as file:
                                content = file.read()

                                if len(content.strip()) == 0:
                                    continue

                                important = extract_important_code(content)

                                combined += f"\n\nFile: {f}\n{important}"
                                files_scanned += 1

                        progress.progress(min(files_scanned / MAX_FILES, 1.0))

                    except:
                        pass

                if files_scanned >= MAX_FILES:
                    break

            # Validation
            if files_scanned == 0:
                st.error("❌ No valid code found")
                st.stop()

            if len(combined.strip()) < 200:
                st.error("❌ Not enough context")
                st.stop()

            combined = combined[:4000]

            st.info("🧠 Running AI analysis...")

            result = analyze_project(combined)

            st.session_state["context"] = combined

            st.success("Analysis Complete")

            st.markdown("## 📊 Project Report")
            st.write(result)


# =========================================================
# 💬 QUESTIONS
# =========================================================
if "context" in st.session_state:

    st.markdown("## 💬 Ask About Project")

    preset_questions = [
        "What does this project do?",
        "What technologies are used?",
        "What are the main components?",
        "What improvements can be made?",
        "What is the complexity level?"
    ]

    cols = st.columns(2)

    for i, q in enumerate(preset_questions):
        if cols[i % 2].button(q):
            answer = chat_with_project(st.session_state["context"], q)
            st.write(answer)

    custom_q = st.text_input("Ask your own question")

    if custom_q:
        answer = chat_with_project(st.session_state["context"], custom_q)
        st.write(answer)