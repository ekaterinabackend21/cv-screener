# CV Screener

CV Screener is a Python CLI application for generating synthetic resumes, indexing
them in Elasticsearch, and answering questions about the indexed candidates.

The project is currently being built in stages. Resume generation is available now;
PDF ingest, embeddings, field search, semantic search, and the chat agent are next.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop, for local Elasticsearch
- An API key for an OpenAI-compatible text model

## Install

Clone the repository and enter it:

```bash
git clone <repository-url>
cd cv-screener
```

Install the locked Python environment:

```bash
uv sync
```

## Download the local embedding model

The embedding model is not stored in Git. Download it once after installing the
Python dependencies:

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

The model is downloaded from Hugging Face and cached in the user's local model
cache. The cache is reused on later runs. No Hugging Face API token is required for
this model.

Verify the model and its vector size:

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print(model.get_embedding_dimension())"
```

The command must print `384`. This matches the `dense_vector` dimension configured
in the Elasticsearch index mapping.

Create the local environment file:

```bash
cp .env.example .env
```

Edit `.env` and set the API key. The key must stay in `.env`; this file is ignored by
Git and must never be committed.

```dotenv
API_KEY=your-relaymodels-key
BASE_URL=https://api.relaymodels.com/v1
LLM_MODEL=gpt-5.6-luna
```

`LLM_MODEL` must be a plain model ID from the gateway catalog. Do not add an
`openai:` or `anthropic:` prefix.

## Start Elasticsearch

Start the local single-node cluster and the index bootstrap container:

```bash
docker compose up -d
```

The Elasticsearch API is available at `http://localhost:9200`. The one-shot
`create-index` service waits for Elasticsearch to become healthy, creates the index
named by `ELASTICSEARCH_INDEX`, and exits successfully. Re-running it is safe.

Check the cluster and index:

```bash
curl http://localhost:9200
curl http://localhost:9200/cv_candidates
docker compose ps -a
docker compose logs create-index
```

Stop the services without deleting the data volume:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the
local Elasticsearch data.

## Generate resumes

Generate one, three, five, or ten resumes. If `--count` is omitted, ten are created:

```bash
uv run cv-screener generate --count 1
uv run cv-screener generate --count 3
uv run cv-screener generate --count 5
uv run cv-screener generate --count 10
```

Each run first asks the text model for a varied set of candidate briefs, then creates
one profile and one PDF per brief. Roles may repeat, but the planner varies seniority,
location, technology focus, languages, and career history.

PDFs are written under:

```text
generated_cvs/cv-DD-MM-YYYY_HH-MM/
```

Each file is named `first_last_position.pdf`. The PDF is one A4 page and follows the
layout of `src/generation/resources/cv-example.pdf`: portrait area in the upper-left
header, profile, skills, experience, education, and languages.

### Images

The RelayModels catalog currently has no image-generation model, so image generation
is disabled by default. The PDF contains an empty `PHOTO` slot:

```dotenv
IMAGE_GENERATION_ENABLED=false
```

Do not pass `--with-images` while this setting is false. If an image-capable
OpenAI-compatible endpoint becomes available, set its exact model ID and enable it:

```dotenv
IMAGE_MODEL=<available-image-model-id>
IMAGE_GENERATION_ENABLED=true
```

Then run:

```bash
uv run cv-screener generate --count 1 --with-images
```

Generated image bytes are inserted into the PDF and are not saved as separate files.

For inspecting a single structured profile without producing a PDF:

```bash
uv run cv-screener generate-profile \
  --brief "Middle Python backend developer with PostgreSQL experience"
```

## Local embedding model

The ingest pipeline uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It produces 384-dimensional vectors, matching the current Elasticsearch mapping.
The model is not stored in this repository and must not be copied into `src/`.
The `sentence-transformers` dependency is included in the project, and the first-run
download command is shown above.

The model name is configurable through:

```dotenv
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The model is downloaded and ready locally; the ingest command will use it once that
pipeline is implemented.

## Current implementation status

Available:

- uv project and Python 3.12 environment;
- OpenAI-compatible text model configuration;
- runtime generation of varied candidate briefs;
- one-page PDF resume generation;
- local Elasticsearch Compose setup and index mapping;
- Elasticsearch Python client and connection helper.

Next:

1. PDF text extraction and LLM field extraction;
2. local embeddings and idempotent ingest;
3. field and semantic search commands;
4. chat agent with Elasticsearch tools;
5. tests, evaluations, and the complete final documentation.
