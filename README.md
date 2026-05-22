# Hermes Multi-Agent System

A multi-agent orchestration system built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

## Architecture

Three specialized agents coordinating together:

| Agent | Role | Responsibility |
|-------|------|---------------|
| **Researcher** | Information Gathering | Web search, document analysis, fact verification |
| **Writer** | Content Creation | Drafting, structuring, formatting output |
| **Reviewer** | Quality Assurance | Reviewing output, catching errors, suggesting improvements |

```
┌─────────────────────────────────────────────┐
│              Orchestrator                     │
│         (routes tasks, manages flow)         │
├──────────┬──────────────┬───────────────────┤
│          │              │                   │
▼          ▼              ▼                   │
┌────────┐ ┌────────────┐ ┌──────────┐        │
│Research│ │   Writer   │ │ Reviewer │        │
│ Agent  │ │   Agent    │ │  Agent   │        │
└────┬───┘ └─────┬──────┘ └────┬─────┘        │
     │           │              │              │
     └───────────┴──────────────┘              │
              Shared Memory                    │
└─────────────────────────────────────────────┘
```

## Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.14+ installed
- Python 3.11+
- OpenRouter API key (or any supported LLM provider)

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/PiotrStyla/Hermes.git
cd Hermes

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env
# Edit .env with your API key

# 4. Run the orchestrator
python -m src.orchestrator
```

## Project Structure

```
├── src/
│   ├── orchestrator.py      # Main coordinator - routes tasks between agents
│   ├── agents/
│   │   ├── base.py          # Base agent class with shared functionality
│   │   ├── researcher.py    # Research & information gathering agent
│   │   ├── writer.py        # Content creation agent
│   │   └── reviewer.py      # Quality assurance agent
│   ├── memory/
│   │   ├── shared.py        # Shared memory store between agents
│   │   └── context.py       # Context management and retrieval
│   └── tools/
│       ├── web_search.py    # Web search tool
│       └── file_ops.py      # File operation tools
├── skills/                  # Custom Hermes skills for each agent
│   ├── research.md
│   ├── writing.md
│   └── review.md
├── config/
│   ├── agents.yaml          # Agent configurations
│   └── orchestrator.yaml    # Orchestration rules
├── tests/
│   └── ...
├── .env.example
├── requirements.txt
└── README.md
```

## How It Works

1. **Task arrives** → Orchestrator analyzes and routes it
2. **Researcher** gathers relevant information and context
3. **Writer** produces content based on research
4. **Reviewer** evaluates output, requests revisions if needed
5. **Loop** continues until quality threshold is met
6. **Output** is delivered with full provenance chain

## Configuration

Edit `config/agents.yaml` to customize each agent's behavior, model, and tools.

## License

MIT
