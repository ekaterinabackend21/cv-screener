# CV Screener

CV Screener is a Python CLI application for generating synthetic resumes, indexing
them in Elasticsearch, and answering questions about the indexed candidates.

The project is currently being built in stages. Resume generation, PDF ingest,
embeddings, field/semantic search, and the CLI chat agent are available.

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

## Ingest PDF resumes

After generating a batch and starting Elasticsearch, index its PDF files:

```bash
uv run cv-screener ingest \
  --input generated_cvs/cv-DD-MM-YYYY_HH-MM
```

The ingest pipeline performs these steps for every PDF:

```text
PDF → pypdf text extraction → LLM structured-field extraction
    → local 384-dimensional embedding → Elasticsearch document
```

The source PDF is the only input data source. The image is ignored during text
extraction. Elasticsearch stores the structured fields, complete extracted text,
embedding, source path, and SHA-256 file hash. Re-ingesting the same file updates the
same document instead of creating a duplicate.

Ingest requires both a running Elasticsearch container and the configured text-model
API key because structured fields are extracted from the PDF by the LLM. The local
embedding model itself does not require an API key.

## Search indexed resumes

Search does not require an LLM API call for field mode. Elasticsearch must be
running and the index must contain ingested resumes.

Search a structured field:

```bash
uv run cv-screener search \
  --mode field \
  --field skills \
  --value Python
```

Supported examples include `first_name`, `last_name`, `position`, `seniority`,
`location`, `skills`, `languages.name`, `languages.level`,
`experience.company`, `experience.technologies`, and `education.institution`.
Nested fields such as `languages.name` are searched within the same nested object.

Search by meaning with the local embedding model:

```bash
uv run cv-screener search \
  --mode semantic \
  --query "senior machine learning engineer with Python experience"
```

Limit the number of returned candidates with `--limit 5`. For semantic search,
`--min-score` can remove weak matches:

```bash
uv run cv-screener search \
  --mode semantic \
  --query "senior machine learning engineer" \
  --limit 5 \
  --min-score 0.70
```

If no candidates reach the threshold, the command prints an empty JSON list.
Results include the candidate fields and the Elasticsearch similarity score.

## Chat with the indexed candidates

Start an interactive CLI chat after indexing the resumes:

```bash
uv run cv-screener chat
```

Ask questions such as:

```text
Who has experience with Python?
Which candidates speak Spanish?
Who would be the best fit for a senior ML role?
Summarize the profile of Mara Vogel.
```

The agent has three Elasticsearch tools:

- structured field search;
- semantic search with the local embedding model;
- lookup of one candidate by full name.

It receives only the results returned by those tools. The system instructions require
the agent to call a tool before making claims about candidates, name candidates in
answers, and report when no matching candidate is found. Use `/exit`, `/quit`, or
`Ctrl-D` to leave the interactive session.

For a single non-interactive question:

```bash
uv run cv-screener chat \
  --question "Which candidates speak Spanish?"
```

## Run the fixed chat evaluations

The repository contains a reproducible evaluation dataset in `evals/fixtures/` and
five cases in `evals/manifest.json`. The fixture PDFs are kept separate from the
normal generated dataset so that new resume generations cannot change the expected
results.

The manifest stores the questions and expected candidate names. If the fixture PDFs
are replaced, update the names in `evals/manifest.json` to match the new dataset.
Use accent-insensitive full names; the evaluation script normalizes case and accents
before checking answers.

Each case uses one of three expectation types:

- `expected_any`: at least one listed candidate must be named;
- `expected_all`: every listed candidate must be named;
- `expected_none`: the answer must explicitly report that no candidate matches.

To freeze a new generated batch, copy its ten PDFs into `evals/fixtures/`, then edit
the five questions and expected names in `evals/manifest.json`.

Start Elasticsearch if it is not already running:

```bash
docker compose up -d
```

Create a separate evaluation index. The environment-variable prefix overrides the
value from `.env` for this command only:

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  docker compose run --rm create-index
```

Ingest the fixed PDFs into that index:

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  uv run cv-screener ingest --input evals/fixtures
```

Run the five chat evaluations against the same index:

```bash
ELASTICSEARCH_INDEX=cv_candidates_eval \
  uv run python evals/run_evals.py
```

The script sends five real questions to the configured text model and prints each
`PASS` or `FAIL`, the returned answer, and the final total. A successful run ends
with:

```text
Passed: 5/5
Overall: PASS
```

The eval run requires `API_KEY`, `BASE_URL` and `LLM_MODEL` in `.env`, and uses five
paid model requests. It does not modify the default `cv_candidates` index. To use a
different fixed dataset, replace the PDFs in `evals/fixtures/`, update the manifest,
and ingest into a new evaluation index name.

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

Image generation is enabled by default. To avoid image API calls, disable it in
`.env`; the PDF will then contain an empty `PHOTO` slot:

```dotenv
IMAGE_GENERATION_ENABLED=true
```

When image generation is enabled, the regular command generates portraits:

```bash
uv run cv-screener generate --count 1
```

Use `--without-images` for a one-off run without portraits. If the setting is false,
`--with-images` remains available only after re-enabling it in `.env`. For OpenRouter, set its
OpenAI-compatible base URL and an image model ID from the image-model catalog:

```dotenv
BASE_URL=https://openrouter.ai/api/v1
IMAGE_MODEL=openai/gpt-image-1-mini
IMAGE_GENERATION_ENABLED=true
```

Then run:

```bash
uv run cv-screener generate --count 1 --with-images
```

The image request uses OpenRouter's `/api/v1/images` endpoint. Generated image bytes
are inserted into the PDF and are not saved as separate files.

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

The model is downloaded and ready locally; both ingest and semantic search use it.

## Current implementation status

Available:

- uv project and Python 3.12 environment;
- OpenAI-compatible text model configuration;
- runtime generation of varied candidate briefs;
- one-page PDF resume generation;
- local Elasticsearch Compose setup and index mapping;
- Elasticsearch Python client and connection helper;
- PDF ingest with structured extraction and local embeddings;
- field and semantic search commands;
- tool-using CLI chat agent.
- fixed evaluation fixtures, manifest, and five-case eval runner.

Available next:

1. API-free unit tests;
2. final NOTES.md and clean-environment verification.
