# Phase 5: GenAI Streamlit Churn Copilot

Natural-language Q&A over the Telco churn MySQL database, powered by LangGraph + OpenAI or Ollama.

## Quick start

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
copy genai\.env.example genai\.env
```

Edit `genai/.env`:

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `openai` or `ollama` |
| `OPENAI_API_KEY` | Required if using OpenAI |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | Default `http://localhost:11434` |
| `OLLAMA_MODEL` | Default `llama3.2:1b` (smaller; use `llama3.2` if you have ~2GB free) |
| `MYSQL_*` | Optional — falls back to `sql/.env` |

### 3. Load MySQL data

```powershell
python sql/load_to_mysql.py
python powerbi/load_scores_to_mysql.py
```

### 4. Run notebooks (development)

| Notebook | Purpose |
|----------|---------|
| `notebooks/05_phase5_genai_setup.ipynb` | Connection tests |
| `notebooks/06_phase5_tools_and_prompts.ipynb` | Tool smoke tests |
| `notebooks/07_phase5_langgraph_agent.ipynb` | Agent eval (8 questions) |
| `notebooks/08_streamlit_churn_copilot.ipynb` | Launch Streamlit |

### 5. Launch Streamlit app

```powershell
streamlit run streamlit/churn_copilot.py
```

Open http://localhost:8501

### Asking questions

- **Main area (top):** large text box + **Ask** button
- **Bottom:** chat input bar (always visible; press Enter to send)
- **Sidebar:** sample question buttons

### Charts

Ask naturally, e.g.:
- "Show a bar chart of churn rate by plan type"
- "Chart the churn trend for the last 6 months"

The agent calls the `generate_chart` tool (Plotly bar/line/pie) after running SQL. Charts appear below the text answer in the chat.

## Sample questions

- Why are customers churning?
- Which segment has highest churn?
- What is the churn trend last 3 months?
- Who are the top 10 customers at risk?
- What is ARPU by plan?
- How does churn differ for senior vs non-senior?
- Which city has highest churn?
- What is the overall churn rate?

## Architecture

```
Streamlit UI  →  LangGraph agent  →  Tools  →  MySQL (telco_churn)
                      ↓
              Context prompt (EDA + SHAP JSON)
```

### Tools

| Tool | Description |
|------|-------------|
| `run_sql_query` | Read-only SELECT (allowlist tables, LIMIT 500) |
| `get_churn_summary` | Precomputed EDA + SHAP insights |
| `get_segment_churn` | Churn rate by plan, city, gender, etc. |
| `get_churn_trend` | Churn counts by `churn_month` |
| `get_top_risk_customers` | Top active customers by ML risk |
| `generate_chart` | Plotly bar/line/pie from SQL |

Core logic: [`genai/copilot.py`](copilot.py)

## LLM providers

**OpenAI (recommended for demos):**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Ollama (offline):**
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```
Run `ollama pull llama3.2` first.

## Windows troubleshooting (Ollama)

### `ollama` is not recognized

Ollama installs to `%LOCALAPPDATA%\Programs\Ollama\`. Refresh PATH in the current terminal:

```powershell
$env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
ollama --version
```

Or use the full path:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
```

Restart Cursor after installing Ollama so new terminals inherit PATH.

### Not enough disk space (C: drive full)

Models default to `C:\Users\<YOU>\.ollama\` (~2GB for `llama3.2`). Options:

- **Smaller model:** `ollama pull llama3.2:1b` and set `OLLAMA_MODEL=llama3.2:1b` in `genai/.env`
- **Move models to D:** set user env `OLLAMA_MODELS=D:\ollama\models`, restart Ollama app
- **Free space on C:** delete temp files, empty Recycle Bin, run Disk Cleanup

### Start Ollama on Windows

1. Open **Ollama** from the Start menu (runs server in background), or
2. `ollama serve` in a separate terminal (leave it open)

## Security

- SQL tool accepts **SELECT only**
- Tables allowlisted: `telco_customers`, `vw_powerbi_customers`, `churn_scores_full`
- All queries auto-append `LIMIT 500` if missing
