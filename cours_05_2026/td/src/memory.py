import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from openai import OpenAI


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class WorkingMemory:
    session_notes: List[str] = field(default_factory=list)
    last_retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    last_user_intent: str = ""
    recent_sources: List[str] = field(default_factory=list)
    recent_failed_queries: List[str] = field(default_factory=list)
    open_question: str = ""

    def add_note(self, note: str) -> None:
        if note:
            self.session_notes.append(note)
            self.session_notes = self.session_notes[-8:]

    def set_recent_sources(self, paths: List[str]) -> None:
        uniq = []
        for p in paths:
            if p and p not in uniq:
                uniq.append(p)
        self.recent_sources = uniq[:5]

    def add_failed_query(self, query: str) -> None:
        if query:
            self.recent_failed_queries.append(query)
            self.recent_failed_queries = self.recent_failed_queries[-5:]

    def summary_text(self) -> str:
        parts = []

        if self.last_user_intent:
            parts.append(f"Last user intent: {self.last_user_intent}")

        if self.open_question:
            parts.append(f"Open question: {self.open_question}")

        if self.session_notes:
            parts.append("Session notes:")
            parts.extend(f"- {n}" for n in self.session_notes[-5:])

        if self.recent_sources:
            parts.append("Recent useful sources:")
            parts.extend(f"- {p}" for p in self.recent_sources)

        if self.recent_failed_queries:
            parts.append("Recent failed or unhelpful queries:")
            parts.extend(f"- {q}" for q in self.recent_failed_queries)

        if self.last_retrieved_chunks:
            parts.append("Last retrieved chunks:")
            for c in self.last_retrieved_chunks[:3]:
                parts.append(
                    f"- {c.get('source_path')} [{round(float(c.get('score', 0.0)), 4)}]"
                )

        return "\n".join(parts).strip()


class PersistentMemoryStore:
    def __init__(
        self,
        memory_path: str,
        client: OpenAI,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self.memory_path = os.path.abspath(memory_path)
        self.client = client
        self.embedding_model = embedding_model
        self.records: List[Dict[str, Any]] = []
        self.load()

    def _embed(self, text: str) -> List[float]:
        """
        This is going to be used to embed the notes into a vector.
        """
        resp = self.client.embeddings.create(
            model=self.embedding_model,
            input=[text],
        )
        return resp.data[0].embedding

    def load(self) -> None:
        self.records = []
        if not os.path.exists(self.memory_path):
            return
        with open(self.memory_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.records.append(json.loads(line))

    def append(
        self,
        text: str,
        kind: str = "episodic",
        source: str = "agent",
        importance: int = 1,
    ) -> Dict[str, Any]:
        """
        This is going to be used to store the notes into the memory and slighty deduplicate them.
        """
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "Empty memory note"}

        if len(text) > 500:
            text = text[:500]

        # déduplication simple avant embedding (coûteux)
        for rec in reversed(self.records[-20:]):
            if (
                rec.get("kind") == kind
                and rec.get("text", "").strip().lower() == text.lower()
            ):
                return {
                    "ok": True,
                    "id": rec["id"],
                    "kind": rec["kind"],
                    "text": rec["text"],
                    "deduplicated": True,
                }

        new_emb = self._embed(text)

        # déduplication sémantique légère
        for rec in reversed(self.records[-30:]):
            score = _cosine_similarity(new_emb, rec["embedding"])
            if rec.get("kind") == kind and score > 0.97:
                return {
                    "ok": True,
                    "id": rec["id"],
                    "kind": rec["kind"],
                    "text": rec["text"],
                    "deduplicated": True,
                    "similarity": round(score, 4),
                }

        rec = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "kind": kind,
            "source": source,
            "importance": int(importance),
            "text": text,
            "embedding": new_emb,
        }
        with open(self.memory_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.records.append(rec)
        return {
            "ok": True,
            "id": rec["id"],
            "kind": kind,
            "text": text,
            "importance": rec["importance"],
        }

    def search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        This is going to be used to search the memories later by semantic similarity, not just keyword matching.
        """
        if not self.records:
            return {"ok": True, "query": query, "results": []}

        q = self._embed(query)
        scored = []
        for rec in self.records:
            base_score = _cosine_similarity(q, rec["embedding"])
            importance_bonus = 0.02 * int(rec.get("importance", 1))
            score = base_score + importance_bonus
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[:top_k]

        return {
            "ok": True,
            "query": query,
            "results": [
                {
                    "score": round(score, 4),
                    "id": rec["id"],
                    "kind": rec["kind"],
                    "source": rec["source"],
                    "text": rec["text"],
                    "importance": rec.get("importance", 1),
                }
                for score, rec in best
            ],
        }
