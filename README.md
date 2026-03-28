# AgentForge — Self-Healing API Reliability Agent

An autonomous agent that monitors API endpoints in real-time, detects anomalies, diagnoses root causes via LLM, and takes corrective action — then learns from each incident to respond faster next time.

Built in 5 hours for the SJSU Applied Data Science Hackathon 2026.

## Architecture

```
Mock APIs → Nexla (normalize) → Agent Loop (observe → diagnose → act) → Dashboard
                                       ↕
                                  Case Memory ← Auto-Tune
```

**Data layer** — FastAPI chaos server with toggleable failure modes (latency spikes, error bursts, degraded responses). Nexla normalizes raw signals into a unified event schema; a fallback poller is included if Nexla setup is slow.

**Agent core** — Railtracks-orchestrated loop. The anomaly detector uses a z-score over a 60-second rolling window. When triggered, an LLM on DigitalOcean diagnoses root cause and recommends an action (reroute, alert, or wait). The executor carries it out.

**Self-improvement** — Every resolved incident is logged as a structured case. The auto-tuner adjusts detection thresholds based on outcomes (true positive → tighten, false positive → loosen). Similar past cases are injected into the LLM diagnosis prompt, so the agent gets faster and more accurate over time.

**Dashboard** — Lovable-generated frontend showing live metrics, an incident feed, and a response-time-delta chart that visualizes the agent learning.

## Project Structure

```
agentforge/
├── server/                  # Mock API + chaos injection
│   ├── main.py              # FastAPI app: /health, /checkout, /chaos/*
│   ├── chaos.py             # Failure mode toggle (latency, errors, degraded)
│   └── schemas.py           # Pydantic models + NormalizedEvent contract
├── agent/                   # Core agent loop (Railtracks)
│   ├── loop.py              # observe → diagnose → act
│   ├── detector.py          # Z-score anomaly detector
│   ├── diagnoser.py         # LLM root-cause chain
│   ├── executor.py          # REROUTE / ALERT / WAIT
│   └── config.py            # Thresholds, endpoints, model config
├── memory/                  # Self-improvement layer
│   ├── case_store.py        # Incident logging + similarity retrieval
│   └── auto_tune.py         # threshold_k adjustment from outcomes
├── ingestion/               # Data pipeline (Nexla)
│   ├── webhook.py           # Receives Nexla-pushed normalized events
│   └── poller.py            # Fallback: direct HTTP polling
├── dashboard/               # Frontend (Lovable)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── MetricsPanel.tsx
│   │   ├── IncidentFeed.tsx
│   │   └── ImprovementChart.tsx
│   └── package.json
├── requirements.txt
├── .env                     # API keys, model endpoint
├── docker-compose.yml       # server + agent + ingestion
└── README.md
```

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the mock API server

```bash
uvicorn server.main:app --port 8000 --reload
```

### 3. Start the agent (with fallback poller)

```bash
python -m agent.loop
```

### 4. Trigger chaos during the demo

```bash
# Latency spikes
curl -X POST http://localhost:8000/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{"mode": "latency", "latency_min": 2.0, "latency_max": 5.0}'

# Error bursts
curl -X POST http://localhost:8000/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{"mode": "errors", "error_rate": 0.5}'

# Degraded responses
curl -X POST http://localhost:8000/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{"mode": "degraded"}'

# Kill switch
curl -X POST http://localhost:8000/chaos/disable
```

## Demo Script

1. **Baseline** (30s) — Dashboard shows green metrics, agent is monitoring quietly.
2. **First incident** — Toggle latency spike. Agent detects in ~5-10s, diagnoses via LLM, reroutes traffic, posts summary to dashboard.
3. **Recovery** — Disable chaos. Agent logs the full incident as a case.
4. **Second incident** — Toggle error bursts. Agent recognizes a similar pattern from case memory, responds faster, references the prior incident. The response-time delta on the dashboard is the proof point.

## Sponsor Tools

| Tool | Role |
|---|---|
| Railtracks | Agent orchestration loop |
| Nexla | Real-time data ingestion + normalization |
| DigitalOcean | LLM inference for diagnosis |
| Lovable | Dashboard frontend |

## How Self-Improvement Works

Each incident produces a case record:

```json
{
  "id": "inc_001",
  "timestamp": "2026-04-18T14:32:01Z",
  "symptoms": {"endpoint": "/checkout", "z_score": 3.4, "error_rate": 0.18},
  "diagnosis": "Upstream payment gateway timeout",
  "action_taken": "REROUTE",
  "outcome": "resolved",
  "resolution_time_ms": 28400
}
```

The auto-tuner adjusts `threshold_k` on the anomaly detector: true positives tighten it (`k -= 0.1`, floor 1.5), false positives loosen it (`k += 0.2`, cap 4.0). Similar past cases are appended to the LLM diagnosis prompt, so the agent builds context over time.

## Environment Variables

```
DIGITALOCEAN_API_KEY=       # LLM inference endpoint
DIGITALOCEAN_MODEL_URL=     # Model serving URL
NEXLA_WEBHOOK_SECRET=       # Webhook auth (if using Nexla)
```