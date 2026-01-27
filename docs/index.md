---

title: Home
nav_order: 0

---

# DataBy AI Docs

Welcome to DataBy AI Docs on building autonomous AI Data Engineer.

**Key Features**

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

## Project References

- [Official Google Cloud Run with FastAPI](<https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service#local-shell>)
- [Official Jupyter Server Rest API Docs](https://jupyter-server.readthedocs.io/en/latest/developers/)
- [Demo Jupyter Kernel Gateway](https://medium.com/@tabindabhat/basics-of-jupyter-kernel-gateway-a54ddc4fd228)
- [Demo Unittesting & Integration Testing for Prototypes](https://www.geeksforgeeks.org/software-engineering/software-engineering-prototyping-model/)

