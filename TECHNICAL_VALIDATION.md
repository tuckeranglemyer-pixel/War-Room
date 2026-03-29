# The War Room — Technical Validation Report

## Benchmark Results

### RAG Pipeline Performance
| Operation | Latency | Dataset | Environment |
|-----------|---------|---------|-------------|
| Single ChromaDB query | 12ms | 31,668 chunks | M2 Mac |
| fetch_context_for_product() | 38ms | 4 queries, 20 results | M2 Mac |
| smart_evidence_fetch() | 4.2s | 10 AI-generated queries, 50 results | DGX + llama3:8b |
| Full swarm (20 scouts) | 8.4s | 20 parallel queries | M2 Mac, 10 workers |

### Inference Performance (DGX Spark)
| Model | Load Time | Round Duration | Memory |
|-------|-----------|---------------|--------|
| Llama 3.3-70B | ~3 min (first load) | 45-90s per round | 42 GB |
| Qwen3-32B | ~2 min (first load) | 30-60s per round | 20 GB |
| Mistral-Small-24B | ~1.5 min (first load) | 25-50s per round | 14 GB |
| llama3:8b (evidence curation) | ~15s | 5s (query generation) | 4.7 GB |

### Thermal Profile (DGX Spark)
| Phase | GPU Temp | CPU Temp | RAM Usage |
|-------|----------|----------|-----------|
| Idle | 40°C | 42°C | 6% (7.1 GB) |
| After evidence fetch | 60°C | 66°C | 5.3% |
| During 70B inference | 70°C | 80°C | 40% (48 GB) |
| Post-round cooldown (30s) | 51°C | 54°C | 40% |
| Thermal ceiling (auto-pause) | 75°C | — | — |

### End-to-End Debate Quality
| Mode | Models | Rounds | Avg Output Length | Evidence Citations |
|------|--------|--------|------------------|--------------------|
| safe_crew.py | 3 (sequential) | 4 | 1,200 chars/round | 4-8 per round |
| optimized_crew.py | 1 (qwen3:32b) | 4 | 2,500 chars/round | 8-12 per round |
| Demo fallback | Hardcoded | 4 | 1,800 chars/round | 6 per round |

### Known Limitations & Mitigations
| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| DGX Spark thermal shutdown during sustained 70B inference | High | safe_crew.py: sequential loading with cooling intervals |
| DGX Spark thermal shutdown during ChromaDB embedding | High | Pre-embed on Mac, transfer via Git |
| Venue WiFi blocks SSH (port 22) | Medium | Direct monitor access + GitHub sync |
| CrewAI max_iter=4 exhausts iterations on tool calls | High | optimized_crew.py: pre-inject evidence, remove tools, max_iter=1 |
| Small models (8B) skip tool calls entirely | Medium | Pre-seeded context injection guarantees evidence |

---

*All benchmarks collected during hackathon weekend on actual hardware.*
