"""Load the Building Code clause knowledge base and retrieve with BM25."""

from __future__ import annotations

import glob
import os
import re

from rank_bm25 import BM25Okapi

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KnowledgeBase:
    def __init__(self, kb_dir: str = KB_DIR):
        self.docs: list[dict] = []
        for path in sorted(glob.glob(os.path.join(kb_dir, "*.md"))):
            with open(path, encoding="utf-8") as f:
                raw = f.read().strip()
            lines = raw.splitlines()
            heading = lines[0].lstrip("# ").strip() if lines else os.path.basename(path)
            clause = heading.split("—")[0].strip() if "—" in heading else heading
            body = "\n".join(lines[1:]).strip()
            self.docs.append({"id": clause, "title": heading, "text": body})
        self._bm25 = (
            BM25Okapi([_tokenize(f"{d['title']} {d['text']}") for d in self.docs]) if self.docs else None
        )

    def search(self, query: str, k: int = 4) -> list[dict]:
        """Return the top-k clauses as [{id, title, text, score}], highest score first."""
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.docs, scores), key=lambda x: x[1], reverse=True)
        return [{**doc, "score": round(float(score), 3)} for doc, score in ranked[:k]]
