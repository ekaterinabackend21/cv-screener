# CV Screener

## Project description and capabilities

CV Screener is a Python CLI application for generating synthetic CVs, indexing them
in Elasticsearch, searching them by fields or meaning, and answering questions with
a tool-using chat agent.

The project has three functional blocks:

1. **Resume generation**
   - generates 1, 3, 5, or 10 varied fictional candidates at runtime;
   - creates one-page A4 PDF resumes based on the bundled reference layout;
   - generates a synthetic portrait for each resume through an image-capable provider;
   - stores each batch under `generated_cvs/cv-DD-MM-YYYY_HH-MM/`;
   - names files as `first_last_position.pdf`.

2. **Indexing and search**
   - extracts text from PDF files with `pypdf`;
   - extracts structured candidate fields with an LLM;
   - creates local 384-dimensional embeddings with
     `sentence-transformers/all-MiniLM-L6-v2`;
   - stores fields, full text, embeddings and source metadata in Elasticsearch;
   - supports structured field search and semantic search;
   - uses a SHA-256 file ID so re-ingesting the same PDF does not create duplicates.

3. **Chat agent**
   - provides an interactive CLI chat and one-question mode;
   - calls Elasticsearch tools;
   - has tools for field search, semantic search and lookup by candidate name;
   - answers only from returned candidates and reports when no match is found.

The repository also contains a fixed ten-PDF evaluation dataset in `evals/fixtures/`.

## Local setup and usage

### Requirements

- Python 3.12;
- [uv](https://docs.astral.sh/uv/);
- Docker Desktop;
- an API key for an OpenAI-compatible text and image provider.

### Install dependencies

```bash
git clone <repository-url>
cd cv-screener
uv sync
```

### Download the local embedding model

The model is downloaded once and cached locally. It is not stored in Git:

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

Verify its dimension:

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print(model.get_embedding_dimension())"
```

The output must be `384`.

### Configure the environment

```bash
cp .env.example .env
```

Set the real key in `.env`. Never commit this file.

For OpenRouter, for example:

```dotenv
API_KEY=your-openrouter-key
BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=provider/text-model-id
IMAGE_MODEL=openai/gpt-image-1-mini
IMAGE_GENERATION_ENABLED=true
OUTPUT_DIR=generated_cvs
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=cv_candidates
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Use exact model IDs from the provider catalog. OpenRouter image models can be listed
with:

```bash
curl https://openrouter.ai/api/v1/images/models \
  -H "Authorization: Bearer $API_KEY"
```

### Start Elasticsearch

```bash
docker compose up -d
```

The Compose setup starts a local single-node Elasticsearch and creates the index named
by `ELASTICSEARCH_INDEX`.

Check the services:

```bash
curl http://localhost:9200
curl http://localhost:9200/cv_candidates
docker compose ps -a
```

Stop services while preserving the data volume:

```bash
docker compose down
```

### Generate resumes

Images are enabled by default when `IMAGE_GENERATION_ENABLED=true`:

```bash
uv run cv-screener generate --count 1
uv run cv-screener generate --count 3
uv run cv-screener generate --count 5
uv run cv-screener generate --count 10
```

To skip the image API for one run:

```bash
uv run cv-screener generate --count 1 --without-images
```

If a generated profile does not fit on one page, the service automatically retries
with a more compact profile prompt.

### Ingest resumes

After generating a batch:

```bash
uv run cv-screener ingest \
  --input generated_cvs/cv-DD-MM-YYYY_HH-MM
```

The pipeline is:

```text
PDF -> text extraction -> LLM field extraction
    -> local embedding -> Elasticsearch document
```

Ingest requires the text-model API key. Embedding generation is local.

### Search resumes

Structured field search:

```bash
uv run cv-screener search \
  --mode field \
  --field skills \
  --value Python
```

Semantic search:

```bash
uv run cv-screener search \
  --mode semantic \
  --query "senior machine learning engineer" \
  --limit 5 \
  --min-score 0.70
```

Supported fields include `first_name`, `last_name`, `position`, `seniority`,
`location`, `skills`, `languages.name`, `languages.level`,
`experience.company`, `experience.technologies`, and `education.institution`.

### Chat with candidates

Interactive mode:

```bash
uv run cv-screener chat
```

One question:

```bash
uv run cv-screener chat \
  --question "Which candidates speak Spanish?"
```

Example questions:

```text
Who has experience with Python?
Which candidates speak Spanish?
Who would be the best fit for a senior ML role?
Summarize the profile of Haruto Nishimura.
```

Use `/exit`, `/quit`, or `Ctrl-D` to leave interactive mode.

## Fixed evaluation run

The `evals/` directory contains ten fixed PDF fixtures, a manifest and a five-case
evaluation script. This dataset is separate from normal generated resumes so results
are reproducible.

The manifest supports:

- `expected_any`: at least one listed candidate must appear;
- `expected_all`: every listed candidate must appear;
- `expected_none`: the answer must report no matching candidate.

If the fixture PDFs are replaced, update the names and questions in
`evals/manifest.json`.

### 1. Start Elasticsearch

```bash
docker compose up -d
```

### 2. Create a separate eval index

The environment prefix overrides `.env` only for this command:

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  docker compose run --rm create-index
```

### 3. Ingest the fixed fixtures

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  uv run cv-screener ingest --input evals/fixtures
```

### 4. Run the evals

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  uv run python evals/run_evals.py
```

The script sends five real questions to the configured text model and prints each
answer with `PASS` or `FAIL`:

```text
Passed: 5/5
Overall: PASS
```

The eval run requires `API_KEY`, `BASE_URL` and `LLM_MODEL`, and consumes five model
requests. It does not modify the default `cv_candidates` index.

## Repository status and limitations

Implemented:

- resume generation with synthetic portraits;
- PDF ingestion and structured extraction;
- local embeddings and Elasticsearch indexing;
- field and semantic search;
- tool-using CLI chat;
- fixed five-case evaluation suite.

Not implemented yet:

- API-free automated unit tests;
- programmatic eval assertion that every chat answer contained a tool call;
- the planned architectural refactor described in `NOTES.md`.
