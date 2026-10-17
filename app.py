"""StudyBuddy AI: generate practice questions from study notes with local Ollama."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

import streamlit as st
from dotenv import load_dotenv


# Load local configuration before reading environment variables. Values in the
# shell still take precedence over values in .env.
load_dotenv()

MODEL_NAME = os.getenv("STUDYBUDDY_MODEL", "llama3.2:1b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/api"


class OllamaError(RuntimeError):
    """A user-facing Ollama setup or inference error."""


def run_command(command: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run a command and return its output without hiding failures."""
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise OllamaError(f"Command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise OllamaError(f"Command timed out: {' '.join(command)}") from exc


def ollama_is_installed() -> bool:
    return shutil.which("ollama") is not None


def install_ollama() -> None:
    """Try the official installer on supported Unix-like systems."""
    if platform.system() == "Windows":
        raise OllamaError(
            "Ollama is not installed. On Windows, install it from "
            "https://ollama.com/download/windows, then restart this app."
        )

    result = run_command(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], timeout=300)
    if result.returncode != 0 or not ollama_is_installed():
        details = (result.stderr or result.stdout).strip()
        raise OllamaError(
            "Automatic Ollama installation failed. Install it from "
            "https://ollama.com/download and restart the app."
            + (f"\n\nInstaller details: {details}" if details else "")
        )


def api_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a small JSON request to the local Ollama server."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{OLLAMA_API_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OllamaError(
            "Could not connect to Ollama at "
            f"{OLLAMA_BASE_URL}. Make sure Ollama is installed and running."
        ) from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc


def start_ollama_service() -> None:
    """Start Ollama in the background if its local API is not responding."""
    try:
        api_request("/tags")
        return
    except OllamaError:
        pass

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise OllamaError(
            "Ollama is installed but could not be started. Run `ollama serve` "
            "in another terminal and try again."
        ) from exc

    for _ in range(20):
        time.sleep(0.5)
        try:
            api_request("/tags")
            return
        except OllamaError:
            continue
    raise OllamaError(
        "Ollama did not become ready. Try `ollama serve` in another terminal, "
        "then click Generate again."
    )


def ensure_model() -> None:
    """Install Ollama if needed, start it, and download the requested model."""
    if not ollama_is_installed():
        install_ollama()

    start_ollama_service()
    tags = api_request("/tags").get("models", [])
    if any(model.get("name") == MODEL_NAME for model in tags):
        return

    result = run_command(["ollama", "pull", MODEL_NAME], timeout=900)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise OllamaError(
            f"Could not download {MODEL_NAME}. Check your internet connection and "
            "available disk space, then try again."
            + (f"\n\nOllama details: {details}" if details else "")
        )


def generate_questions(notes: str) -> str:
    """Generate exactly five study questions and answers from the supplied notes."""
    prompt = f"""You are a helpful study tutor.
Using only the study notes below, create exactly 5 practice questions.
For each question, provide a concise answer supported by the notes.
Number them 1 through 5 and use this format:
1. Question
   Answer: ...
Do not add an introduction or information that is not in the notes.

Study notes:
{notes}
"""
    response = api_request(
        "/generate",
        method="POST",
        payload={"model": MODEL_NAME, "prompt": prompt, "stream": False},
    )
    answer = response.get("response", "").strip()
    if not answer:
        raise OllamaError("Ollama returned an empty response. Please try again.")
    return answer


SAMPLE_NOTES = """Photosynthesis is the process plants use to convert light energy into chemical energy.
Chlorophyll in chloroplasts absorbs light, mainly in the blue and red parts of the spectrum.
During the light-dependent reactions, water is split and oxygen is released.
The Calvin cycle uses carbon dioxide, ATP, and NADPH to produce glucose.
Photosynthesis mostly takes place in the leaves of plants."""


def main() -> None:
    st.set_page_config(page_title="StudyBuddy AI", page_icon="📚", layout="centered")
    st.title("📚 StudyBuddy AI")
    st.write("Paste your study notes and get five practice questions with answers.")
    st.caption("Everything runs locally on your computer with Ollama and llama3.2:1b.")

    with st.sidebar:
        st.header("Local setup")
        st.write(f"Model: `{MODEL_NAME}`")
        st.write(f"Ollama: `{OLLAMA_BASE_URL}`")
        st.info("The first run may take a few minutes while Ollama and the model are set up.")

    notes = st.text_area(
        "Study notes",
        value=SAMPLE_NOTES,
        height=260,
        placeholder="Paste notes here...",
        help="Your notes are sent only to Ollama running on this computer.",
    )

    if st.button("Generate 5 practice questions", type="primary", use_container_width=True):
        if not notes.strip():
            st.warning("Please paste or type some study notes first.")
            return

        try:
            with st.status("Checking Ollama and preparing the local model...", expanded=True) as status:
                ensure_model()
                status.update(label="Generating questions...", state="running")
                questions = generate_questions(notes.strip())
                status.update(label="Questions ready!", state="complete", expanded=False)
            st.subheader("Practice questions")
            st.markdown(questions)
        except OllamaError as exc:
            st.error(str(exc))
            st.info(
                "If setup failed, install Ollama from https://ollama.com/download, "
                "run `ollama serve`, and try again."
            )
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")


if __name__ == "__main__":
    main()
