---

title: FastAPI
nav_order: 3
description: FastAPI Endpoints.

---


# Connecting External Users

This section details on how I connect open source datasets to this site.

## HuggingFace Services

Similar to how you would setup hugginface account to load and cache dataset for inferencing tasks.

## Kaggle Services

```bash
Kaggle API (server)
   ↓
Flask (fetch datasets)
   ↓
Jinja template (dropdown list)
   ↓
User selects dataset
   ↓
POST back to server
```
