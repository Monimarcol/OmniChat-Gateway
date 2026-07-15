"""Static V1 model capability matrix. Each entry's `ollama_tag` is what actually gets
passed to `ollama pull` / `litellm.completion(model="ollama/<tag>")` -- this catalog
doubles as both the recommendation input and the source of truth for what's pullable.

Ported from the Kade-AI hardware detection POC and adapted to Ollama's actual model
tags (the POC's catalog referenced GGUF quant files directly; here we only need the
tag Ollama itself resolves).
"""
from dataclasses import dataclass


@dataclass
class ModelSpec:
    id: str
    ollama_tag: str
    display_name: str
    min_ram_gb: float
    param_count: str
    tags: list[str]
    strengths: str
    limitations: str


CATALOG: list[ModelSpec] = [
    ModelSpec(
        id="llama3.2-1b",
        ollama_tag="llama3.2:1b",
        display_name="Llama 3.2 1B",
        min_ram_gb=2.5,
        param_count="1B",
        tags=["chat"],
        strengths="Very fast, minimal footprint, good for quick back-and-forth chat.",
        limitations="Weak at multi-step reasoning, coding, and long documents.",
    ),
    ModelSpec(
        id="llama3.2-3b",
        ollama_tag="llama3.2:3b",
        display_name="Llama 3.2 3B",
        min_ram_gb=4.0,
        param_count="3B",
        tags=["chat", "brainstorming"],
        strengths="Good balance of speed and quality for everyday chat and idea generation.",
        limitations="Struggles with technical accuracy on research or code-heavy tasks.",
    ),
    ModelSpec(
        id="phi3.5",
        ollama_tag="phi3.5",
        display_name="Phi-3.5 Mini",
        min_ram_gb=4.5,
        param_count="3.8B",
        tags=["research", "coding", "brainstorming"],
        strengths="Strong reasoning for its size; solid at structured analysis and light coding.",
        limitations="Smaller context window than larger models; can be terse.",
    ),
    ModelSpec(
        id="qwen2.5-7b",
        ollama_tag="qwen2.5:7b",
        display_name="Qwen2.5 7B",
        min_ram_gb=8.0,
        param_count="7B",
        tags=["research", "content_creation", "chat"],
        strengths="Strong general knowledge and multilingual writing quality.",
        limitations="Noticeably slower on CPU-only, low-RAM machines.",
    ),
    ModelSpec(
        id="qwen2.5-coder-7b",
        ollama_tag="qwen2.5-coder:7b",
        display_name="Qwen2.5 Coder 7B",
        min_ram_gb=8.0,
        param_count="7B",
        tags=["coding"],
        strengths="Purpose-built for code generation, review, and debugging.",
        limitations="Weaker than general models at open-ended writing or brainstorming.",
    ),
    ModelSpec(
        id="mistral-7b",
        ollama_tag="mistral:7b",
        display_name="Mistral 7B",
        min_ram_gb=8.0,
        param_count="7B",
        tags=["content_creation", "chat", "brainstorming"],
        strengths="Fluent, natural writing style; reliable general-purpose assistant.",
        limitations="Less precise than domain models on research or coding tasks.",
    ),
    ModelSpec(
        id="gemma2-9b",
        ollama_tag="gemma2:9b",
        display_name="Gemma 2 9B",
        min_ram_gb=10.0,
        param_count="9B",
        tags=["research", "content_creation"],
        strengths="Strong instruction-following; good at longer, structured documents.",
        limitations="Needs more RAM headroom; slower first-token latency on modest hardware.",
    ),
    ModelSpec(
        id="llama3",
        ollama_tag="llama3",
        display_name="Llama 3 8B",
        min_ram_gb=8.0,
        param_count="8B",
        tags=["chat", "content_creation", "brainstorming"],
        strengths="The default model this project ships with -- broadly capable generalist.",
        limitations="Outperformed by newer same-size models on coding and research tasks.",
    ),
]

DEFAULT_MODEL = next(m for m in CATALOG if m.id == "llama3")
