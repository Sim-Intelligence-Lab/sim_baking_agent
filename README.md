# Sim Baking Agent

A Flask baking game starring Trang. Pick a vanilla cake or a pizza in the Step Controls panel; the agent follows that recipe from memory, while the environment tracks ingredients, tools, and each baking step.

## Quick start

Requires Python 3.10+ and [Ollama](https://ollama.com/download).

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen3:4b-instruct
python baking_app.py
```

Make sure the Ollama service is running before launching the app. Open <http://127.0.0.1:5000> to play.

## Ollama configuration

The app uses Ollama as its only model backend. The default model is `qwen3:4b-instruct`; configure a different local model or Ollama server with:

```bash
export OLLAMA_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen3:4b-instruct
python baking_app.py
```

`OLLAMA_BASE_URL` and `LLM_MODEL` are optional. The app does not require an OpenAI API key.

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── baking_app.py                  # Flask routes and app setup
├── baking_agent.py                # Agent behavior and recipe retrieval
├── scripts/
│   └── draw_pizza_art.py          # Redraws the pizza pixel art (needs Pillow)
├── baking/
│   ├── environment.py             # Shared kitchen rules and the cake recipe
│   ├── pizza_environment.py       # Pizza recipe rules
│   ├── recipes.py                 # Recipe name -> kitchen lookup
│   ├── trang/
│   │   ├── agent.json             # Agent name and persona
│   │   └── memory/memory_stream.txt  # Mixed memories, including both recipes
│   ├── templates/index.html       # Game page
│   └── static/
│       ├── game.js                # Browser game logic
│       └── assets/                # Kitchen map, sprites, and ingredient art
└── simulation_engine/
    ├── gpt_structure.py           # OpenAI-compatible model requests
    └── settings.py                # Backend and model configuration
```

## Pizza art

The pizza item sprites and end screens are drawn by code. To tweak one, edit its grid in `scripts/draw_pizza_art.py` and run:

```bash
pip install pillow
python scripts/draw_pizza_art.py
```

## Repository

[Sim-Intelligence-Lab/sim_baking_agent](https://github.com/Sim-Intelligence-Lab/sim_baking_agent)
