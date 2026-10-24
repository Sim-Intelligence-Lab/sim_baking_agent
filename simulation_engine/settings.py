"""Ollama model configuration used by the baking app."""

import os

MODEL_BACKEND = "ollama"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEBUG = False
LLM_VERS = os.environ.get("LLM_MODEL", "qwen3:4b-instruct")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
