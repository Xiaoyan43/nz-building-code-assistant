# NZ Building Code Assistant

**Ask a New Zealand Building Code question → get an answer grounded in, and citing, specific clauses — and a clear "I can't find that" when the clauses don't cover it.**

Architects and consent staff look up Building Code clauses constantly. This is a small internal tool that
retrieves the relevant clauses and has an LLM answer **only from them**, with citations — so it speeds up
lookup without making up code.

> **Honesty:** personal portfolio project, 2026, built with heavy AI assistance. The knowledge base is a
> handful of **paraphrased sample clauses** for demonstration — **not** the official text and **not legal
> advice**. The authoritative source is MBIE's Acceptable Solutions. **NZS 3604** is a paid standard and is
> deliberately **not** reproduced here. Real use would index the public MBIE Acceptable Solution documents.

## What it demonstrates
- **Retrieval-augmented generation (RAG)** — BM25 over a clause knowledge base, top-k passed to the model.
- **Grounding / anti-hallucination** — the model must answer only from retrieved clauses, **cite clause
  ids**, and set `grounded=false` (decline) when the clauses don't cover the question. No invented clause
  numbers or figures.
- **Structured tool-use output** at `temperature=0` (reproducible), validated before returning.
- **A real domain fit** for an architecture studio — code lookup with citations.

## Stack
Python · FastAPI · `rank-bm25` (retrieval) · Anthropic SDK (Claude, strict tool-use) · a single static HTML
page served by FastAPI (one process, nothing to npm-install).

## How it works
```
question → BM25 retrieve top-k clauses → Claude (answer only from clauses, cite ids, or decline) → cited answer
```

## Knowledge base
`backend/kb/*.md` — one clause per file (E2 external moisture, B1 structure, B2 durability, F4 safety from
falling, G12 water supplies, H1 energy efficiency, D1 access routes). Each is a short paraphrased summary
with a pointer to the official Acceptable Solution. Drop in more `.md` files and they're indexed on restart.

## Run it locally
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env        # then add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8010
```
Open http://localhost:8010 and ask a question. Or via curl:
```bash
curl -s -X POST http://localhost:8010/ask -H "Content-Type: application/json" \
  -d '{"question":"When do I need a barrier on a deck?"}'
```

## Roadmap
- [x] BM25 retrieval over a clause KB
- [x] Grounded, cited answers with a decline-when-unsure guardrail
- [x] One-page UI served by the API
- [ ] Index the real public MBIE Acceptable Solution PDFs (chunking + metadata)
- [ ] Embedding retrieval + rerank for fuzzier questions
- [ ] A small eval set (question → expected clause) measuring retrieval + citation accuracy
- [ ] Per-clause "show source" panel and answer history
