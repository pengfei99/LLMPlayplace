import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import pymupdf4llm
from openai import OpenAI

from src.safety import LIST_AUTHORIZED_FILE_EXTENSIONS


@dataclass
class RAGConfig:
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 400
    chunk_overlap: int = 120
    top_k_default: int = 4


@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    text: str
    start: int
    end: int
    embedding: List[float]


def _pdf_to_markdown(pdf_path: str) -> str:

    pdf_path = Path(pdf_path)
    md_path = pdf_path.with_suffix(".md")

    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

    markdown = pymupdf4llm.to_markdown(pdf_path)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return markdown


def _read_text_file(path: str) -> str:

    ext = os.path.splitext(path.lower())[1]

    if ext == ".pdf":
        return _pdf_to_markdown(path)

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    if not text.strip():
        return chunks

    step = max(1, chunk_size - chunk_overlap)
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + chunk_size)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "start": start,
                    "end": end,
                    "text": chunk_text,
                }
            )
        if end >= n:
            break
        start += step

    return chunks


def rerank_chunks_with_llm(
    client,
    model: str,
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Un utilitaire de reranking des chunks tres basique !
    """

    if not chunks:
        return []

    passages = []
    for i, c in enumerate(chunks):
        passages.append(f"[{i}] {c['text']}")

    prompt = f"""
    You are ranking document passages by relevance.

    User question:
    {query}

    Passages:
    {chr(10).join(passages)}

    Return ONLY a JSON list of the passage indices sorted by relevance.
    Example:
    [3, 1, 0]
    """

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        order = json.loads(resp.choices[0].message.content)
    except Exception:
        return chunks[:top_k]

    ranked = []
    for idx in order:
        if isinstance(idx, int) and idx < len(chunks):
            ranked.append(chunks[idx])

    return ranked[:top_k]


class RAGStore:
    def __init__(
        self,
        data_dir: str,
        index_path: str,
        client: OpenAI,
        cfg: Optional[RAGConfig] = None,
        debug: bool = False,
    ) -> None:
        self.data_dir = os.path.abspath(data_dir)
        self.index_path = os.path.abspath(index_path)
        self.client = client
        self.cfg = cfg or RAGConfig()
        self.chunks: List[Chunk] = []
        self.index = None
        self.embedding_matrix = None
        self.debug = debug

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        resp = self.client.embeddings.create(
            model=self.cfg.embedding_model,
            input=texts,
        )
        return [item.embedding for item in resp.data]

    def build_index(self) -> None:
        supported_ext = LIST_AUTHORIZED_FILE_EXTENSIONS
        records: List[Chunk] = []

        for root, _, files in os.walk(self.data_dir):
            for fn in files:
                ext = os.path.splitext(fn.lower())[1]
                if ext not in supported_ext:
                    print(f"Skipping {fn} because it is not a supported file extension")
                    continue

                print(f"Processing {fn}...")
                abs_path = os.path.join(root, fn)
                rel_path = os.path.relpath(abs_path, self.data_dir)

                text = _read_text_file(abs_path)
                chunk_specs = _chunk_text(
                    text,
                    chunk_size=self.cfg.chunk_size,
                    chunk_overlap=self.cfg.chunk_overlap,
                )
                if not chunk_specs:
                    print(f"No chunks found for {fn}")
                    continue

                embeddings = self._embed_texts([c["text"] for c in chunk_specs])

                for i, (spec, emb) in enumerate(zip(chunk_specs, embeddings)):
                    records.append(
                        Chunk(
                            chunk_id=f"{rel_path}::chunk_{i}",
                            source_path=rel_path,
                            text=spec["text"],
                            start=spec["start"],
                            end=spec["end"],
                            embedding=emb,
                        )
                    )

        self.chunks = records

        # construire le numpy array des embeddings
        embeddings = np.array([c.embedding for c in self.chunks]).astype("float32")

        if self.debug:
            print("chunks:", len(self.chunks))
            print("embeddings type:", type(embeddings))
            print("embeddings shape:", embeddings.shape)

        # on normalise les embeddings pour la cosine similarity
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]

        # index FAISS
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        self.embedding_matrix = embeddings

        self.save()

    def save(self) -> None:
        payload = {
            "data_dir": self.data_dir,
            "config": asdict(self.cfg),
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "source_path": c.source_path,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                }
                for c in self.chunks
            ],
        }

        with open(self.index_path + ".meta", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        faiss.write_index(self.index, self.index_path + ".faiss")

    def load(self) -> None:
        with open(self.index_path + ".meta", "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.chunks = []

        for rec in payload["chunks"]:
            self.chunks.append(
                Chunk(
                    chunk_id=rec["chunk_id"],
                    source_path=rec["source_path"],
                    text=rec["text"],
                    start=rec["start"],
                    end=rec["end"],
                    embedding=[],
                )
            )

        self.index = faiss.read_index(self.index_path + ".faiss")

    def build_or_load(self, rebuild: bool = False) -> None:
        if rebuild or (
            not os.path.exists(self.index_path + ".faiss")
            and not os.path.exists(self.index_path + ".meta")
        ):
            print(f"Building RAG index from {self.data_dir}...")
            self.build_index()
        else:
            print(f"Loading RAG index from {self.index_path}...")
            self.load()

    def retrieve(
        self, query: str, top_k: Optional[int] = None, rerank: bool = False
    ) -> Dict[str, Any]:
        """
        Get most relevant chunks from the index database based on the query.
        """

        top_k = top_k or self.cfg.top_k_default

        if self.index is None:
            return {"ok": False, "error": "RAG index not loaded"}

        # On commence par embedder notre query
        query_emb = self._embed_texts([query])[0]
        query_vec = np.array([query_emb]).astype("float32")

        # On normalise...
        faiss.normalize_L2(query_vec)

        # ... puis on cherche les chunks les plus pertinents via faiss
        scores, ids = self.index.search(query_vec, top_k)

        results = []

        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue

            chunk = self.chunks[idx]

            results.append(
                {
                    "score": float(score),
                    "chunk_id": chunk.chunk_id,
                    "source_path": chunk.source_path,
                    "start": chunk.start,
                    "end": chunk.end,
                    "text": chunk.text,
                }
            )

        if rerank and len(results) > 1:
            results = rerank_chunks_with_llm(
                client=self.client,
                model="gpt-5.4",
                query=query,
                chunks=results,
                top_k=top_k or 5,
            )
        else:
            results = results[: top_k or 5]

        return {
            "ok": True,
            "query": query,
            "results": results,
        }
