# Swipe2Eat LLM Service

A lightweight Python microservice for LLM-based food recommendations.

## What this service does
- Connects to PostgreSQL using `.env`
- Loads user profile and available food from the database
- Applies internal candidate shortlisting to prepare cleaner LLM input
- Calls Ollama / Mistral to generate a friendly recommendation reply
- Returns a graceful high-demand message if the LLM service is unavailable

## Folder structure
```text
swipe2eat_llm_refactor/
├── app/
│   ├── main.py
│   ├── recommendation.py
│   ├── aggregator.py
│   ├── llm_client.py
│   ├── selector.py
│   ├── validators.py
│   ├── analytics.py
│   └── cache_store.py
├── tests/
│   └── test_smoke.py
├── schema_ai_analytics.sql
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

## Environment variables
Create a `.env` file in the project root:

```env
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=appdb
DB_USER=your-db-user
DB_PASS=your-db-password
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=mistral
FLASK_SECRET_KEY=change-me
PORT=5000
```

## Run locally
```bash
pip install -r requirements.txt
cd app
python main.py
```

Open:
- `http://localhost:5000/`
- Health check: `http://localhost:5000/health`

## Build Docker image
From the project root:

```bash
docker build -t swipe2eat-llm-service .
```

## Run Docker container
```bash
docker run --env-file .env -p 5000:5000 swipe2eat-llm-service
```

## Share with team / deploy to AWS
Recommended process:
1. Download this folder or zip.
2. Test locally with your `.env` and Ollama.
3. Build Docker image locally.
4. Push code to GitHub.
5. Teammate or DevOps can build from GitHub on AWS, or you can push the image to Amazon ECR.
6. Run the container on EC2 or ECS.

## Notes
- This service does not expose backend business-rule scoring as a public API mode.
- If the LLM is unavailable, the API returns a user-friendly high-demand message.
"# LLM_OLLAMA_INTEGRATION" 
