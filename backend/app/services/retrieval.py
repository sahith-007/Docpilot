import math
import re
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import ClinicalNote
from app.schemas import EvidenceChunk

logger = get_logger(__name__)
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]{2,}")
_index: "ClinicalIndex | None" = None


@dataclass(frozen=True)
class NoteChunk:
    chunk_id: str
    note_id: str
    case_id: str
    note_type: str
    note_date: str
    title: str
    text: str


class ClinicalIndex(Protocol):
    def rebuild(self, notes: list[ClinicalNote]) -> None:
        ...

    def search(
        self,
        case_id: str,
        query: str,
        note_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        ...


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def chunk_note(note: ClinicalNote, max_words: int = 95) -> list[NoteChunk]:
    paragraphs = [part.strip() for part in note.body.split("\n") if part.strip()]
    chunks: list[NoteChunk] = []
    current: list[str] = []
    chunk_number = 1

    for paragraph in paragraphs:
        words = paragraph.split()
        if current and len(current) + len(words) > max_words:
            chunks.append(_make_chunk(note, chunk_number, " ".join(current)))
            chunk_number += 1
            current = []
        current.extend(words)

    if current:
        chunks.append(_make_chunk(note, chunk_number, " ".join(current)))
    return chunks


def _make_chunk(note: ClinicalNote, number: int, text: str) -> NoteChunk:
    return NoteChunk(
        chunk_id=f"{note.id}:chunk-{number}",
        note_id=note.id,
        case_id=note.case_id,
        note_type=note.note_type,
        note_date=note.note_date,
        title=note.title,
        text=text,
    )


class LocalClinicalIndex:
    def __init__(self) -> None:
        self.chunks: list[NoteChunk] = []
        self.idf: dict[str, float] = {}

    def rebuild(self, notes: list[ClinicalNote]) -> None:
        self.chunks = [chunk for note in notes for chunk in chunk_note(note)]
        doc_count = max(len(self.chunks), 1)
        document_frequency: dict[str, int] = {}
        for chunk in self.chunks:
            for token in set(tokenize(chunk.text)):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        self.idf = {
            token: math.log((doc_count + 1) / (count + 1)) + 1
            for token, count in document_frequency.items()
        }
        logger.info("local_index_rebuilt", chunks=len(self.chunks))

    def search(
        self,
        case_id: str,
        query: str,
        note_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        query_tokens = tokenize(query)
        query_set = set(query_tokens)
        scored: list[tuple[float, NoteChunk]] = []

        for chunk in self.chunks:
            if chunk.case_id != case_id:
                continue
            if note_types and chunk.note_type not in note_types:
                continue
            chunk_tokens = tokenize(chunk.text)
            if not chunk_tokens:
                continue
            overlap = query_set.intersection(chunk_tokens)
            weighted_overlap = sum(self.idf.get(token, 1.0) for token in overlap)
            phrase_bonus = sum(1.2 for token in query_tokens if token in chunk.text.lower())
            score = weighted_overlap + phrase_bonus
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_score = scored[0][0] if scored else 1
        return [
            EvidenceChunk(
                note_id=chunk.note_id,
                case_id=chunk.case_id,
                note_type=chunk.note_type,
                note_date=chunk.note_date,
                title=chunk.title,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=round(score / top_score, 3),
            )
            for score, chunk in scored[:limit]
        ]


class ChromaClinicalIndex:
    def __init__(self) -> None:
        import chromadb
        from langchain_openai import OpenAIEmbeddings

        self.client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self.collection = self.client.get_or_create_collection("docpilot_clinical_notes")
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

    def rebuild(self, notes: list[ClinicalNote]) -> None:
        chunks = [chunk for note in notes for chunk in chunk_note(note)]
        if not chunks:
            return
        vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=vectors,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "note_id": chunk.note_id,
                    "case_id": chunk.case_id,
                    "note_type": chunk.note_type,
                    "note_date": chunk.note_date,
                    "title": chunk.title,
                }
                for chunk in chunks
            ],
        )
        logger.info("chroma_index_rebuilt", chunks=len(chunks))

    def search(
        self,
        case_id: str,
        query: str,
        note_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        query_vector = self.embeddings.embed_query(query)
        where: dict[str, object] = {"case_id": case_id}
        if note_types:
            where = {"$and": [{"case_id": case_id}, {"note_type": {"$in": note_types}}]}
        result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        chunks: list[EvidenceChunk] = []
        for chunk_id, text, metadata, distance in zip(
            result.get("ids", [[]])[0],
            result.get("documents", [[]])[0],
            result.get("metadatas", [[]])[0],
            result.get("distances", [[]])[0],
            strict=False,
        ):
            chunks.append(
                EvidenceChunk(
                    note_id=metadata["note_id"],
                    case_id=metadata["case_id"],
                    note_type=metadata["note_type"],
                    note_date=metadata["note_date"],
                    title=metadata["title"],
                    chunk_id=chunk_id,
                    text=text,
                    score=round(max(0.0, 1.0 - float(distance)), 3),
                )
            )
        return chunks


def get_index() -> ClinicalIndex:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def _build_index() -> ClinicalIndex:
    if settings.openai_api_key and not settings.demo_mode:
        try:
            return ChromaClinicalIndex()
        except Exception as exc:
            logger.warning("chroma_unavailable_using_local_index", error=str(exc))
    return LocalClinicalIndex()


def rebuild_index(db: Session) -> None:
    notes = db.query(ClinicalNote).all()
    get_index().rebuild(notes)


def search_evidence(
    case_id: str,
    question: str,
    note_types: list[str] | None = None,
    limit: int = 5,
) -> list[EvidenceChunk]:
    return get_index().search(case_id, question, note_types, limit)

