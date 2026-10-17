# StudyBuddy AI

A beginner-friendly Streamlit app that turns study notes into five practice questions with answers. It uses the open-source `llama3.2:1b` model through [Ollama](https://ollama.com), running locally on your computer. No paid API or external AI service is used.

## Requirements

- Python 3.10 or newer
- macOS, Linux, or Windows
- Internet access for the first-time Ollama installer/model download
- About 1 GB of free disk space for the model

## Install and run

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, use `.venv\Scripts\Activate.ps1` instead.

2. Install the Python dependency:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. (Optional) Create your local configuration:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` if you want to use a different local Ollama model or host. The
   defaults are `llama3.2:1b` and `http://127.0.0.1:11434`. The `.env` file is
   ignored by Git so local configuration stays on your computer.

4. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

   Using `python -m streamlit` ensures Streamlit runs from the virtual environment
   instead of a conflicting system or Anaconda installation. If the environment is
   not active, use `./.venv/bin/python -m streamlit run app.py` on macOS/Linux.

The app automatically:

- Checks whether the `ollama` command is available.
- Attempts the official Ollama install script on macOS/Linux when it is missing.
- Gives a clear download link instead on Windows or if automatic installation fails.
- Starts `ollama serve` when the local Ollama API is not already running.
- Downloads `llama3.2:1b` with `ollama pull llama3.2:1b` if it is not available.

## Configuration

Configuration is read from `.env` using `python-dotenv`. Environment variables
already set in the terminal take precedence over `.env` values.

| Variable | Default | Purpose |
| --- | --- | --- |
| `STUDYBUDDY_MODEL` | `llama3.2:1b` | Ollama model to download and use |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama server address |

If Ollama cannot start automatically, run this in another terminal and click Generate again:

```bash
ollama serve
```

You can also install Ollama manually from <https://ollama.com/download>.

## Demonstrate the app

The editor starts with sample photosynthesis notes already filled in. Click **Generate 5 practice questions** and wait for the local model to respond. Then replace the sample with your own notes, such as a class summary or textbook section, and generate another set.

To verify the model outside the app:

```bash
ollama list
```

You should see `llama3.2:1b`.

## Privacy and troubleshooting

- Notes are sent only to the Ollama server at `http://127.0.0.1:11434` on your computer.
- The app does not save or upload study notes.
- Set `OLLAMA_HOST` if Ollama is configured on another local address, for example `OLLAMA_HOST=http://127.0.0.1:11434`.
- If the model download fails, check internet access and disk space, then run `ollama pull llama3.2:1b` manually.
- If you see a connection error, run `ollama serve` and retry.
