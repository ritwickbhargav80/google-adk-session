---
title: Plan My Weekend
description: ADK agent that plans personalized weekends using a MongoDB vector knowledge base and Gemini.
ms.date: 2026-10-17
---

## Overview

Plan My Weekend is a Google ADK agent. For each request it:

1. Embeds the user's query with `gemini-embedding-001`.
2. Retrieves matching activities, places and food from MongoDB Atlas Vector Search.
3. Builds an itinerary with `gemini-3.5-flash`, using only the retrieved data.

## Prerequisites

* Python 3.10 or later
* A Google account (for the Gemini API key)
* A MongoDB Atlas account (the free M0 tier is enough)
* Git Bash, PowerShell or any terminal

## Project layout

```text
New folder (2)/                  <- run all commands from here
├── README.md
├── .venv/                       <- created in Step 1
└── plan_my_weekend/             <- the ADK agent package
    ├── __init__.py
    ├── agent.py                 <- agent and search_weekend_knowledge tool
    ├── .env                     <- created in Step 5 (never commit)
    ├── data/
    │   └── weekend_data.json    <- source knowledge documents
    ├── eval/
    │   └── weekend_eval.evalset.json
    └── scripts/
        ├── check_embedding_dimensions.py
        ├── ingest.py
        └── test_retrieval.py
```

## Setup

Follow the steps in order.

### Step 1: Create and activate a virtual environment

Git Bash:

```sh
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

The prompt shows `(.venv)` when the environment is active. Activate it again in every new terminal.

### Step 2: Install dependencies

```sh
pip install google-adk "google-adk[eval]" pymongo google-genai python-dotenv
pip install "opentelemetry-api==1.42.1" "opentelemetry-sdk==1.42.1"
adk --version
```

The second command pins OpenTelemetry to versions that `google-adk` supports. Without it, `adk web` fails with `ImportError: cannot import name '_ExtendedAttributes'`.

### Step 3: Get a Gemini API key

1. Open <https://aistudio.google.com/apikey>.
2. Select **Create API key** and copy the key.

### Step 4: Create the MongoDB Atlas database

1. Sign in at <https://cloud.mongodb.com>.
2. Create a project, then select **Create a cluster** and choose the free **M0** tier. Pick the region closest to you.
3. Create a database user:
   * Go to **Security > Database Access > Add New Database User**.
   * Choose **Password** authentication and enter a username and password.
   * Give the user the **Read and write to any database** role.
4. Allow your IP address:
   * Go to **Security > Network Access > Add IP Address**.
   * Select **Add Current IP Address** (or `0.0.0.0/0` for testing only).
5. Copy the connection string:
   * Go to **Database > Clusters > Connect > Drivers**.
   * Choose **Python** and copy the `mongodb+srv://...` string.
   * Replace `<password>` in it with your database user's password. URL-encode special characters in the password.
6. Create the database and collection:
   * Go to **Database > Clusters > Browse Collections > Create Database**.
   * Database name: `weekend_planner`
   * Collection name: `knowledge`

These names must match the values in `.env` and the index in Step 7:

| Setting           | Value             |
|-------------------|-------------------|
| Database          | `weekend_planner` |
| Collection        | `knowledge`       |
| Vector index name | `vector_index`    |
| Vector field      | `embedding`       |

### Step 5: Create the .env file

Create `plan_my_weekend/.env` with your own values:

```dotenv
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=<your-gemini-api-key>
MONGODB_URI=<your-atlas-connection-string>
MONGODB_DATABASE=weekend_planner
MONGODB_COLLECTION=knowledge
```

> [!WARNING]
> Never commit `.env` or share these values. If a key or password is exposed, rotate it immediately.

### Step 6: Check the embedding dimensions

```sh
python plan_my_weekend/scripts/check_embedding_dimensions.py
```

The script prints a number (`3072` for `gemini-embedding-001` by default). Use that exact value as `numDimensions` in Step 7. A mismatch makes vector search return no results.

### Step 7: Create the Atlas Vector Search index

1. In Atlas, go to **Database > Clusters > Atlas Search** (or **Search & Vector Search**).
2. Select **Create Search Index**.
3. Choose **Vector Search** and **JSON Editor**, then select **Next**.
4. Set:
   * Index name: `vector_index`
   * Database and collection: `weekend_planner` / `knowledge`
5. Paste this definition, replacing `3072` if Step 6 printed a different number:

   ```json
   {
     "fields": [
       {
         "type": "vector",
         "path": "embedding",
         "numDimensions": 3072,
         "similarity": "cosine"
       }
     ]
   }
   ```

6. Select **Create Search Index** and wait until the status is **Active**.

The index name and path must match `agent.py` and `test_retrieval.py` exactly (`vector_index` and `embedding`).

### Step 8: Ingest the knowledge data

```sh
python plan_my_weekend/scripts/ingest.py
```

Expected output: `Inserted <n> documents.`

The script deletes all existing documents in the collection, then embeds and inserts every entry from `data/weekend_data.json`. Rerun it after editing the data file.

Each document has these fields:

| Field         | Example                                |
|---------------|----------------------------------------|
| `name`        | `Nahargarh Fort Sunset`                |
| `category`    | `activity`, `place` or `food`          |
| `location`    | `Jaipur`                               |
| `description` | Short text description                 |
| `budget`      | `200` (rupees)                         |
| `best_time`   | `Saturday evening`                     |
| `interests`   | `["photography", "sunset", "history"]` |
| `text`        | Generated by `ingest.py` for embedding |
| `embedding`   | Generated by `ingest.py`               |

### Step 9: Test retrieval

```sh
python plan_my_weekend/scripts/test_retrieval.py
```

The script runs a sample query ("a good sunset photography place in Jaipur") and prints the top 3 matches with scores. If nothing prints, check the index status and dimensions (Steps 6 and 7).

### Step 10: Run the agent

```sh
adk web --port 8080
```

Open <http://localhost:8080>, select `plan_my_weekend` in the agent dropdown, and ask for a weekend plan. Example:

```text
I'm visiting Jaipur this weekend. I have Saturday evening and Sunday morning free. I love photography and local food. Budget is 1500 for two people.
```

The `--reload` warning on Windows is expected and harmless.

### Step 11: Run the evaluation (optional)

```sh
adk eval plan_my_weekend plan_my_weekend/eval/weekend_eval.evalset.json
```

The first argument is the agent folder and the second is the eval set. Results are written to `plan_my_weekend/.adk/eval_history/`.

The eval set currently has no expected `final_response` or tool trajectory, so the default criteria (`tool_trajectory_avg_score` 1.0, `response_match_score` 0.8) cannot pass. Add expected values or supply a custom eval config before relying on the results.

## Troubleshooting

| Problem                                      | Cause and fix                                                                                                          |
|----------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `KeyError: 'MONGODB_URI'`                    | `.env` is missing or in the wrong place. It must be at `plan_my_weekend/.env`.                                         |
| `ImportError: ... '_ExtendedAttributes'`     | OpenTelemetry versions are mismatched. Rerun the pin in Step 2.                                                        |
| `adk: command not found`                     | The virtual environment is not active. Rerun Step 1 or run `.venv/Scripts/adk.exe`.                                    |
| `Invalid value for 'AGENT_MODULE_FILE_PATH'` | Pass the agent folder first: `adk eval plan_my_weekend <evalset.json>`.                                                |
| Vector search returns no results             | Index is not Active, the name is not `vector_index`, the path is not `embedding`, or `numDimensions` does not match.   |
| `ServerSelectionTimeoutError` or auth error  | Your IP is not allowed in Network Access, or the password in `MONGODB_URI` is wrong or not URL-encoded.                |
| `429 RESOURCE_EXHAUSTED`                     | The Gemini free tier allows 5 requests per minute per model. Wait a minute and retry, or use a billed key.             |
