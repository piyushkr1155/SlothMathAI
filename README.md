# 🦥 SlothMate AI

> **"Work less. Let your local AI handle the boring stuff."**

SlothMate AI is a local-first, privacy-respecting personal productivity assistant created for the **“Slow and Steady” open-source AI challenge**. 

Instead of drowning in meeting minutes, scattered text notes, product specs, and lengthy PDFs, users simply drop documents into their local inbox. SlothMate AI digests them on-device using local open-weight language models, extracts explicit tasks with deadlines, flags decisions and uncertainties, and consolidates everything into a single, cohesive **Daily Morning Briefing**.

---

## 🧭 Key Highlights

- **100% Local Inference**: Powered by [Ollama](https://ollama.ai/) running open-weight models (`Qwen2.5 3B`, `Llama 3.2`, etc.) on your laptop. No cloud API keys, no subscription fees, no data leaks.
- **Privacy & Offline First**: Zero telemetry. Documents, tasks, and embeddings stay strictly in your local SQLite database (`slothmate.db`).
- **Prompt Injection Defense**: Untrusted user documents are isolated in `<untrusted_document_content>` tags with strict system instructions prohibiting prompt overrides.
- **No Fabricated Deadlines**: Strict date distinction — explicit dates are captured into structured deadlines, while vague expressions (*"soon"*, *"next week"*, *"ASAP"*) are filed under *Uncertainties* for human confirmation.
- **One-Click "Sloth Mode"**: Process all inbox documents, eliminate duplicate tasks, sort priorities, and generate your morning executive briefing in one click.
- **Calm, Productivity-Focused UI**: Built with Streamlit, styled with warm off-white tones, gentle forest greens, clean typography, and restrained cards.

---

## 🏛️ Architecture & Project Structure

SlothMate AI follows a clean, modular architecture separating interface, AI execution, document processing, business logic, and storage:

```
SlothMateAI/
├── app.py                     # Streamlit application entry point & router
├── config.py                  # Global application configuration & paths
├── requirements.txt           # Python package dependencies
├── README.md                  # Comprehensive documentation
├── .gitignore                 # Excludes venv, sqlite databases, cache, logs
├── ai/
│   ├── __init__.py
│   ├── local_model.py         # Ollama HTTP client, status checks, JSON repair
│   └── prompts.py             # System prompts, injection defense, extraction schemas
├── processors/
│   ├── __init__.py
│   ├── text_reader.py         # .txt and .md parser with encoding detection
│   ├── pdf_reader.py          # PyMuPDF extractor with encryption & page checks
│   └── chunking.py            # Sentence & paragraph boundary chunking
├── services/
│   ├── __init__.py
│   ├── task_extractor.py      # Normalization, deadline validation, deduplication
│   ├── briefing.py            # Morning Briefing consolidation & Markdown export
│   └── inbox_processor.py     # Lazy Inbox ingestion & Sloth Mode coordinator
├── storage/
│   ├── __init__.py
│   └── database.py            # SQLite schema (WAL mode, foreign keys, indexes)
├── ui/
│   ├── __init__.py
│   ├── dashboard.py           # Daily metrics & Run Sloth Mode button
│   ├── inbox.py               # Lazy Inbox file uploader & directory table
│   ├── briefing.py            # Morning Briefing viewer & .md download
│   ├── tasks.py               # Task Dashboard ("My Tasks"), search, filters
│   ├── history.py             # Archive of past briefings & execution logs
│   └── settings.py            # Model configuration, live AI health, data reset
├── tests/
│   ├── test_processors.py     # Text, markdown, and PyMuPDF PDF unit tests
│   ├── test_task_extractor.py # Deadline validation and deduplication tests
│   ├── test_storage.py        # SQLite persistence and metrics tests
│   ├── test_ai_model.py       # JSON repair and Ollama status check tests
│   ├── test_briefing.py       # Briefing consolidation tests
│   └── test_inbox_processor.py# Idempotency and batch processing tests
├── sample_data/               # Realistic sample notes, meetings, and roadmap PDF
└── data/                      # Local data directory (git-ignored)
    ├── inbox/                 # Local document inbox directory
    └── slothmate.db           # SQLite database
```

---

## 🚀 Getting Started on Windows

### 1. Prerequisites
- **Python 3.11+** installed ([Python.org](https://www.python.org/downloads/)).
- **Ollama** installed ([Ollama Download](https://ollama.com/download/windows)).

### 2. Setup Virtual Environment (PowerShell)
```powershell
cd D:\PIYUSH\SlothMateAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`)*

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Pull Local Model
Download the recommended default model via Ollama:
```powershell
ollama pull qwen2.5:3b
```
*(You can also use other installed models like `ollama pull llama3.2` or `qwen3:4b`)*

### 5. Launch SlothMate AI
```powershell
python -m streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 📱 Core User Workflows

### 1. Dashboard & Sloth Mode
- View 4 high-level metrics: **Pending Tasks**, **Completed Tasks**, **Overdue Tasks**, and **Documents Processed**.
- Click the prominent **🦥 Run Sloth Mode** button to scan your inbox, extract tasks, and compile your briefing automatically.

### 2. Lazy Inbox
- Drag and drop `.txt`, `.md`, or `.pdf` files.
- Click **📥 Load Sample Documents** to instantly populate the inbox with test files (`meeting_q4_product_sync.md`, `client_acme_feedback.txt`, `project_sloth_architecture.md`, `executive_roadmap.pdf`).
- Inspect file size, SHA-256 hash, and processing status (`🟢 Processed`, `🟡 Pending`, `🔴 Failed`).

### 3. Morning Briefing
- View the synthesized **Executive Summary**.
- Inspect **Top 3 Priorities**, **Tasks Due Today**, **Upcoming Deadlines**, **Key Decisions**, and **Follow-Up Items**.
- Review **Uncertainties** (ambiguous dates or items requiring user confirmation).
- Click **📥 Export Briefing (.md)** to download the briefing as a portable Markdown file.

### 4. My Tasks
- Filter by status (`Pending`, `In Progress`, `Completed`, `Dismissed`) and priority (`High`, `Medium`, `Low`).
- Search tasks by keywords in title, description, or source document.
- Click **🔍 View Source Evidence** on any task to see the exact quote extracted from the original document.
- Check off completed tasks to update the SQLite database in real-time.

### 5. Settings & AI Health
- Check connection status with local Ollama (`🟢 Connected`, `🟡 Model Missing`, `🔴 Unavailable`).
- Switch between detected local models without restarting.
- Adjust model temperature (default `0.2` for deterministic extraction).
- Manage privacy or reset stored database records in the **Danger Zone**.

---

## 🧪 Automated Testing

SlothMate AI includes a test suite covering document reading, PyMuPDF extraction, JSON repair, deadline disambiguation, SQLite persistence, idempotency, and batch processing:

Run all tests with:
```powershell
python -m pytest tests -v
```

**Test Coverage Summary:**
- `test_processors.py`: Text, markdown, empty file rejection, oversize rejection, PyMuPDF text layer extraction, sentence chunking.
- `test_task_extractor.py`: Date pattern regexes, vague timing handling, priority fallback, duplicate title normalization.
- `test_storage.py`: SQLite document CRUD, task status toggling, briefing retrieval, metrics queries.
- `test_ai_model.py`: JSON markdown code block stripping, trailing comma correction, Ollama endpoint mocking.
- `test_briefing.py`: Multi-document synthesis, top 3 priority scoring, markdown formatting.
- `test_inbox_processor.py`: Idempotent execution (duplicate files skipped via SHA-256 hashes), partial failure isolation.

---

## 🔒 Privacy & Security Safeguards

1. **Local-Only Processing**: No remote LLM APIs or cloud servers are queried.
2. **Untrusted Data Isolation**: Document content is framed in `<untrusted_document_content>` tags, and system prompts explicitly instruct the model never to execute embedded commands.
3. **No Executable HTML**: Document contents are rendered strictly as escaped text or markdown, preventing XSS injection.
4. **Local Database WAL Mode**: SQLite runs in Write-Ahead Logging mode with foreign keys enabled, ensuring zero data corruption during unexpected power cuts.
5. **No Telemetry**: No tracking pixels or external analytics scripts.

---

## ⚖️ Model Licensing

- **Qwen2.5 3B**: Open weights licensed under Apache 2.0.
- **Llama 3.2**: Open weights licensed under Meta Llama 3.2 Community License.

---

## 🔮 Future Roadmap

- Native local audio transcription for voice notes via Whisper.cpp.
- Watchdog background file watcher for instant background processing when files are saved to the inbox folder.
- Local vector search across historical briefings using SQLite-VSS.

---

_SlothMate AI — Built for the “Slow and Steady” open-source AI challenge._
