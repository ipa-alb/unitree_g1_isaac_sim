# Humanoid LLM Orchestrator — Task & Setup

## System Specs

| Component | Spec |
|-----------|------|
| CPU | Intel Core Ultra 9 285K (24 cores) |
| RAM | 62.25 GB total / ~35.8 GB available |
| GPU | NVIDIA GeForce RTX 5090 (31.84 GB VRAM) |
| OS | Ubuntu 22.04.5 LTS |
| Disk (root) | 78G total, 19G free |
| Disk (home) | 119G total, 19G free |

## Chosen Model: DeepSeek-R1-Distill-Qwen-7B

| Property | Value |
|----------|-------|
| Model | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` |
| Type | R1 chain-of-thought distillation (dense 7B) |
| VRAM Usage | ~16.5 GB (52% of 31.84 GB) |
| Speed | ~25.4 tok/s |
| Context | 131k tokens |
| GGUF Size | ~8 GB |
| Quantization | Q4_K_M |
| Runtime | llama.cpp |
| llmfit Score | 87 (highest compatible) |

### Why This Model

1. **VRAM headroom** — Uses only ~52% of your 5090. Leaves ~15 GB free for Isaac Sim to run simultaneously.
2. **R1 chain-of-thought** — Distilled from DeepSeek-R1's reasoning capability. Thinks step-by-step before acting — ideal for multi-step robot planning (observe scene → reason about objects → pick action).
3. **Fast inference** — ~25 tok/s means the orchestrator loop stays responsive. 3x faster than the 30B MoE alternative.
4. **131k context** — Plenty for accumulating observations, camera descriptions, and multi-step plans across a long session.
5. **Small disk footprint** — GGUF is only ~8 GB, fits easily on /home with 19 GB free.
6. **Top compatibility score** — Scored 87/100 on llmfit, highest of all compatible models for this hardware.

## Setup Guide: Running Qwen3-Coder-30B-A3B Locally

### Option A: Ollama (Easiest)

```bash
# 1. Install ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the model
ollama pull qwen3-coder:30b-a3b

# 3. Test it
ollama run qwen3-coder:30b-a3b "Hello, what can you do?"

# 4. Run as API server (for the orchestrator to call)
# Ollama runs a server automatically on http://localhost:11434
# Test the API:
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3-coder:30b-a3b",
  "prompt": "Say hello",
  "stream": false
}'
```

### Option B: LM Studio (GUI + API)

1. Download LM Studio from https://lmstudio.ai
2. Search for `Qwen3-Coder-30B-A3B` in the model browser
3. Download the GGUF Q4_K_M variant
4. Load the model and start the local server
5. API available at `http://localhost:1234/v1/chat/completions` (OpenAI-compatible)

### Option C: llama.cpp (Manual, Most Control)

```bash
# 1. Clone and build llama.cpp with CUDA
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)

# 2. Download the GGUF model
# From huggingface (pick one):
#   - lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
#   - Or use huggingface-cli:
pip install huggingface-hub
huggingface-cli download Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 --local-dir ./models/qwen3-coder-30b

# 3. Convert to GGUF if needed (or download pre-quantized GGUF)
# Pre-quantized GGUFs are available from bartowski or lmstudio-community on HuggingFace

# 4. Run the server
./build/bin/llama-server \
  -m ./models/qwen3-coder-30b-a3b-q4_k_m.gguf \
  -c 8192 \
  -ngl 99 \
  --host 0.0.0.0 \
  --port 8080

# API available at http://localhost:8080/v1/chat/completions (OpenAI-compatible)
```

### Disk Space Warning

Your `/home` partition has only **19 GB free**. The model GGUF is ~17 GB.

To free space:
```bash
# Check what's using space
du -sh ~/workspace/* | sort -rh | head -20
du -sh ~/.cache/* | sort -rh | head -10

# Common cleanups:
pip cache purge
conda clean --all
docker system prune -a    # if using docker
```

Or store the model on root (`/opt/models/`) which also has 19 GB free, or split across both.

## Orchestrator Architecture (Next Step)

```
User: "Pick up the red block"
         │
         ▼
┌─────────────────────────┐
│  orchestrator.py        │
│  (observe-reason-act)   │
│                         │
│  1. do.py state         │◄── JSON: joint states, object poses
│  2. do.py camera head   │◄── JPEG: scene image
│  3. LLM reasoning       │◄── Qwen3-Coder-30B-A3B
│  4. do.py arms/gripper  │──► shared memory commands
│  5. goto 1              │
└─────────────────────────┘
```

## Status

- [x] System specs documented
- [x] Model chosen (Qwen3-Coder-30B-A3B)
- [ ] Install ollama or llama.cpp
- [ ] Download model
- [ ] Build orchestrator.py
- [ ] Test observe-reason-act loop
