# Autonomous AI Agent Backend FastAPI

DataBy AI Main Backend.

## **Features**

- **Server-Sent Events (SSE)**: A unidirectional protocol over standard HTTP where the server pushes updates to the client. The client initiates the connection and listens for a continuous stream of messages with the text/event-stream MIME type.
- **On-Event Support**:
  - Kaggle
  - Google Colab
  - Hugging Face
- **Project Management Externel Connections**
  - Notion
  - WandB

## **Workspace Requirements**

What is required to work use this repo by tech suites:

- Cloud Stack:
  - Google Cloud Setup and Generative AI Kit.
- Tech Stack:
  - Vite/React/Tailwind
  - Python FastAPI
- Database Stack:
  - Firebase Realtime Database.
  - Google Cloud Bucket.
- Jupyter Notebook Server - can privately serve with Hugging Face Space for free.

## **Project Directory Overview**

```bash
# tree -d -L 4 -I '(^|/)\.[^/]+|__pycache__|\.git|\.venv'

├── app                       # Project's directory
│   ├── config                # Project Configuration Files. `/prod` and `/dev` defines the config files for prod and dev environments, respectively.
│   │   ├── dev
│   │   └── prod
│   ├── src                   # Project's Core modules
│   │   ├── agent             # Contains base abstract designs to build AI Agents e.g. Generative AI Cloud Providers, Agent Builders, Agent Prompt Pipelines
│   │   ├── playground        # Contains AI agent's kernels terminal sessions controllers
│   │   ├── router            # Contains FastAPI Utils e.g. execeptions, dependencies
│   │   ├── service           # Contains servicing
│   │   └── tools             # Contains actionable methods accessible by the AI Agents
│   ├── static                # Static Files to mount onto FastAPI during local development. Note that this is not intended to be used in prod.
│   │   ├── css
│   │   └── js
│   └── utils                 # Contains setup utils for FastAPI REST Endpoints
└── tests                     # Contains Unittests and pytest cases
```

## **Local Dev Notes**

Ways to run application:

```bash
python -m app.main
# or for FastAPI
uvicorn app.main:app --reload
# or lazy start
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Note that it is preferrable to run as a module where `app` directory is the root. For example:

```bash

# Running a script from some child path
python -m app.src.agent.playground
```

## **Setup Files**

Utility methods for setting up workspace are stored in:

- `utils/on_startup.py`
- `utils/loader.py`
- `utils/paths.py`


## **Testing**

```bash
# To run all Unittestings
python -m unittest discover -s tests -p "test_*.py"
```

## **Core Checklist TODO**

**FastAPI**
- [x] SSE ENDPOINTS
- [ ] NextJS Connection
- [x] CORS

**AI Agentic Architecture**

- [x] Playground: Jupyter Kernel Connection
- [x] AI Agentic Workflow
- [x] AI Hosting Service & Providers
  - [x] Google GenAI Kit
- [x] AI Agent On-event terminals / kernels via the following backup sessions:
  - [x] Kaggle
  - [x] Jupyter Kernel Server (EC2)
  - [x] Jupyter Kernel Server (Git Codespace)
  - [ ] (Optional) Cloud Runs e.g. AWS or Google Cloud Run (depends on how I feel)
- [ ] AI Agent Session
- [ ] AgentRL Modules
  - [ ] Experimental Module Workspace
  - [ ] During Current Session
  - [ ] Across Different Sessions
    - [ ] Startup
    - [ ] Post Completion
    - [ ] Error Capturing

**External Connections**

- [ ] MongoDB
- [ ] SupaBase
- [ ] Google Bucket
- [ ] Google Workspace - Sheets Controller

**Deployment**

- [ ] Setup Workspace in Prod
- [ ] Setup Env Variables in clouds
- [ ] CI/CD Pipelines on git push
- [ ] Docs

## **Extensions**

- [ ] ML / AI Workflows

## To run Interactively

Run the following block

```python

import sys
from pathlib import Path
import importlib.util

BACKEND = Path("/Users/mimiphan/mimeus-app/databy-ai/backend").resolve()
assert (BACKEND / "app").is_dir(), f"Expected app/ under {BACKEND}, but it wasn't found."

# Put BACKEND first
if str(BACKEND) in sys.path:
    sys.path.remove(str(BACKEND))
sys.path.insert(0, str(BACKEND))

# Purge any previously imported wrong 'app'
for k in list(sys.modules.keys()):
    if k == "app" or k.startswith("app."):
        del sys.modules[k]

print("sys.path[0]:", sys.path[0])
print("find_spec('app'):", importlib.util.find_spec("app"))
print("find_spec('app.src'):", importlib.util.find_spec("app.src"))
print("find_spec('app.src.agent'):", importlib.util.find_spec("app.src.agent"))

```
