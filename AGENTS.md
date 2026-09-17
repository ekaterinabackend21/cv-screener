# Project instructions

- Write an English docstring for every function and method added or modified.
- Keep `readme.md` current. It must document a clean local setup, normal workflow,
  and the separate fixed evaluation workflow.
- Do not read, print, or commit real API keys or .env contents.
- Ask before running any real model request that may incur charges. Compilation,
  CLI help, mocked checks and local Elasticsearch checks are allowed without a model
  request.
- Keep runtime candidate data in memory. Persist generated resumes as PDF files;
  fixed evaluation PDFs may be stored under `evals/fixtures/`.
- Organize code by feature under src; shared configuration and model access live at its root.
- Use the single `API_KEY` and OpenAI-compatible `BASE_URL` configuration for text
  and image providers. OpenRouter image generation uses its `/api/v1/images` endpoint.
- Resume generation supports `1`, `3`, `5`, and `10` candidates. Images are enabled
  by default; `--without-images` is the explicit opt-out.
- Elasticsearch stores structured fields, full text, local embeddings and source
  metadata. Keep normal data in `cv_candidates` and run fixed evaluations against a
  separate index such as `cv_candidates_eval`.
- The chat agent must answer from Elasticsearch tool results. When changing chat or
  eval code, preserve checks for named candidates and no-match responses. Add a
  programmatic assertion of tool calls when test work resumes.
- The fixed eval suite lives in `evals/fixtures/`, `evals/manifest.json`, and
  `evals/run_evals.py`; update the manifest when replacing fixture PDFs.
- API-free automated tests are not implemented yet. Do not add formal tests unless
  the user explicitly resumes test work; when resumed, add meaningful coverage for
  search, CLI validation and chat tool behavior rather than placeholder tests.
- Keep architectural refactoring and remaining limitations documented in `NOTES.md`.
