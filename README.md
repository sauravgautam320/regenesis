# Regen — Knowledge-to-TechTree Generator

Small script that fetches short Wikipedia extracts related to survival skills by default (can be any data scrapper by modifying the array) and uses a local model server (optimised on gemma) to convert them into structured "tech tree" nodes. Survival focused skills cruncher.

## Requirements
- Python 3.10+
- `requests` (install: `pip install requests`)

## Quick start
1. Ensure your local model server is running and exposes the inference endpoint at `http://localhost:11434/api/generate`.
2. (Optional) Set model selection via environment variables:
   - `MODEL_NAME` — default: `gemma3:4b` (used by the script)
   - `MODEL_FALLBACKS` — comma-separated fallback model names (optional)

Example (PowerShell):
```
$env:MODEL_NAME = 'gemma3:4b'
python core.py
```

## Files
- `core.py` — main script
- `genesis_nodes.json` — generated DB of nodes (ignored by default)
- `ai_debug/` — raw AI responses saved for inspection (ignored by default)
- `wikipedia_vault.json` — cached Wikipedia extracts (ignored by default)

## Notes
- The script writes parsed nodes to `genesis_nodes.json` and saves raw AI responses to `ai_debug/` for debugging.
- If the model returns markdown-wrapped JSON or JSON arrays, the script attempts to extract and validate the first valid node.

If you want, I can add a small `requirements.txt` or a CI/test step next.
