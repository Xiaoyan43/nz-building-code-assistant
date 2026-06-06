# NZ Building Code Assistant — Target Architecture

A north-star architecture for upgrading the assistant from the current demo (FastAPI + BM25 over a few
paraphrased markdown clauses + Claude tool-use + static HTML) into a production-grade, **grounded** Q&A
tool over the real public NZ Building Code corpus. Build it **in phases** (see Roadmap).

> Legal/honesty constraints: index only **publicly available** MBIE Acceptable Solutions / Verification
> Methods. **Do NOT ingest NZS 3604 or other paid standards** (reference them by name only). Always show
> "not legal advice — confirm against the official Acceptable Solution." Keep `ANTHROPIC_API_KEY` server-side.

---

## 1. Goals & non-goals
- **Goals:** answer Building Code questions **grounded in retrieved clauses**, with clause + page citations
  and a "show source" panel; **decline** when the corpus doesn't cover it (no invented code); measurable
  retrieval + citation accuracy.
- **Non-goals:** legal advice; reproducing paid standards; answering from the model's parametric memory.

## 2. System overview
```
                ┌──────────── Frontend (Next.js or lightweight, Vercel) ────────────┐
 Browser ─────▶ │ Ask box · cited answer · "show source" panel · history · feedback │
                └───────────────┬──────────────────────────────────────────────────┘
                                │ HTTPS
                ┌───────────────▼──────────── Backend API (FastAPI, Docker) ─────────┐
                │ api/ → services/ → repositories/ → integrations/                    │
                │  • retrieval service (BM25 + dense pgvector → rerank)               │
                │  • answer service (Claude tool-use, grounded, cited, declines)      │
                │  • ingestion service (PDF → chunks → embeddings)                    │
                └───────┬───────────────────────────┬───────────────────────────────┘
                        │                            │
                Anthropic API                Supabase Postgres + pgvector
                (Claude)                     (clauses, chunks, embeddings, logs)

  Offline:  MBIE public PDFs ──▶ ingestion pipeline ──▶ chunks + metadata + embeddings
```

## 3. Tech stack
- **Backend:** Python · FastAPI · Pydantic v2 · Anthropic SDK · `rank-bm25` (or Postgres FTS) · an
  embedding model (e.g. a hosted embeddings API) · a reranker (cross-encoder or LLM rerank).
- **Data:** Supabase Postgres + pgvector (chunks, embeddings, sources, query logs, feedback).
- **Frontend:** start with the current static page; upgrade to Next.js (chat UI + source panel).
- **Infra/Quality:** Docker; Render/Fly (backend); Vercel (frontend); GitHub Actions; ruff + mypy + pytest.

## 4. Target folder structure
```
nz-building-code-assistant/
├── ingestion/               # download_sources.py, parse_pdf.py, chunk.py, embed.py, sources.yaml
├── backend/
│   └── app/
│       ├── api/             # routers: ask, sources, health, feedback
│       ├── services/        # retrieval, rerank, answer, ingestion
│       ├── repositories/    # chunks, embeddings, logs
│       ├── integrations/    # anthropic_client, embeddings_client
│       ├── schemas/         # AskRequest, AnswerResult, Clause, Citation
│       └── core/            # config, logging, security, errors
├── frontend/                # Next.js chat UI (or backend/static for the demo)
├── data/                    # processed chunks (NOT raw paid PDFs); .gitignore the raw downloads
├── eval/                    # qa_set.jsonl (question→expected clause), run_eval.py
├── infra/                   # Dockerfile, .github/workflows
└── docs/                    # ARCHITECTURE.md, sources & licensing notes
```

## 5. Data model (Postgres)
- **sources**: id, doc_code (e.g. 'E2/AS1'), title, version, url, retrieved_at, licence_note.
- **clauses**: id, source_id, clause_code (e.g. 'E2 3.2'), title, text, page, order_idx.
- **chunks**: id, clause_id, text, token_count, embedding vector(N), tsvector (FTS).
- **queries / feedback**: id, question, retrieved_ids[], answer, grounded, cited[], rating, created_at.

## 6. Key flows
- **Ingestion (offline):** download public PDFs (registry in `sources.yaml`) → parse → split into
  clause-aware chunks with metadata (doc, clause_code, page) → embed → upsert into Postgres. Re-runnable
  and versioned (track source version).
- **Ask:** question → hybrid retrieve (BM25/FTS + dense pgvector) → rerank top-k → Claude (tool-use,
  temp=0, prompt-cached) answers **only from chunks**, returns {answer, cited_clauses, grounded} →
  if `grounded=false`, show the decline message → log query + retrieved for eval.
- **Show source:** each citation links to the stored clause text + doc/page (so a human can verify).

## 7. Cross-cutting
- **Grounding guardrail (core value):** the model must cite clause codes it used and set `grounded=false`
  when retrieval doesn't cover the question — never invent clause numbers, R-values, heights, or distances.
- **Cost/abuse:** cache identical questions; rate-limit; daily cap; mock/sample mode for public demo.
- **Security:** no PII stored beyond the question; tight CORS; secrets in env; clear disclaimers.
- **Observability:** log retrieval hits + grounded rate; track which questions get declined (corpus gaps).
- **Testing:** unit (retrieval, answer parsing), integration (ask endpoint), and the eval harness in CI.

## 8. Roadmap (build in this order)
1. **Real corpus ingestion:** `sources.yaml` of public MBIE Acceptable Solutions; PDF→clause chunks +
   metadata → Postgres. Replace the handful of paraphrased markdown clauses.
2. **Hybrid retrieval + rerank:** BM25/FTS + pgvector dense retrieval, merged and reranked.
3. **Citations + source panel + history + feedback** in the UI.
4. **Next.js frontend** (chat UI) replacing the static page.
5. **Eval:** `qa_set.jsonl` (question→expected clause); measure retrieval recall@k, citation correctness,
   groundedness (and decline-correctness on out-of-corpus questions); wire into CI.
6. **Deploy:** Dockerise backend → Render/Fly; Postgres on Supabase; frontend → Vercel.

## 9. Definition of done (per phase)
Typed + linted, tests green, eval numbers logged, only public sources ingested (NZS 3604 excluded),
disclaimers present, no secrets in repo, README + this doc updated.
