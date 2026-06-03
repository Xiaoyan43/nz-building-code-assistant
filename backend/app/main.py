import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .answerer import answer_question
from .config import settings
from .kb import KnowledgeBase

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

app = FastAPI(title="NZ Building Code Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

kb = KnowledgeBase()


class AskRequest(BaseModel):
    question: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.anthropic_model, "clauses_loaded": len(kb.docs)}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")
    if not settings.anthropic_api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY is not set — copy .env.example to .env and add your key.")

    retrieved = kb.search(question, k=settings.top_k)
    if not retrieved:
        raise HTTPException(503, "Knowledge base is empty — add clause files under backend/kb/.")

    try:
        result = answer_question(question, retrieved)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Answer generation failed: {e}") from e

    return {
        "question": question,
        **result,
        "retrieved": [{"id": c["id"], "title": c["title"], "score": c["score"]} for c in retrieved],
    }
