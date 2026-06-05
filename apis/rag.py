import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "docs"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
SIMILARITY_THRESHOLD = 0.28
TOP_K = 3

_chunks: list[str] = []
_embeddings: np.ndarray | None = None
_model = None


def _cargar_modelo():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("RAG: cargando modelo de embeddings...")
        _model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
        logger.info("RAG: modelo listo.")
    return _model


def _chunkear(texto: str) -> list[str]:
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + CHUNK_SIZE, len(texto))
        if fin < len(texto):
            for sep in ("\n\n", "\n", ". "):
                corte = texto.rfind(sep, inicio + CHUNK_SIZE // 2, fin)
                if corte != -1:
                    fin = corte + len(sep)
                    break
        chunk = texto[inicio:fin].strip()
        if len(chunk) > 60:
            chunks.append(chunk)
        if fin >= len(texto):
            break
        inicio = fin - CHUNK_OVERLAP
    return chunks


def init_rag() -> bool:
    global _chunks, _embeddings

    if not DOCS_DIR.exists():
        logger.warning("RAG: carpeta docs/ no encontrada.")
        return False

    todos_chunks = []
    for archivo in sorted(DOCS_DIR.glob("*.txt")):
        try:
            contenido = archivo.read_text(encoding="utf-8")
            nuevos = _chunkear(contenido)
            todos_chunks.extend(nuevos)
            logger.info("RAG: %s → %d chunks", archivo.name, len(nuevos))
        except Exception as e:
            logger.warning("RAG: error en %s: %s", archivo.name, e)

    if not todos_chunks:
        logger.warning("RAG: sin documentos para indexar.")
        return False

    _chunks = todos_chunks
    modelo = _cargar_modelo()
    _embeddings = modelo.encode(
        todos_chunks,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,
    )
    logger.info("RAG: %d chunks indexados y listos.", len(_chunks))
    return True


def buscar_contexto(query: str, top_k: int = TOP_K) -> str | None:
    if _embeddings is None or not _chunks:
        return None
    try:
        modelo = _cargar_modelo()
        q_emb = modelo.encode([query], convert_to_numpy=True)

        # Cosine similarity vectorizada
        norm_docs = _embeddings / np.clip(
            np.linalg.norm(_embeddings, axis=1, keepdims=True), 1e-10, None
        )
        norm_q = q_emb / np.clip(np.linalg.norm(q_emb), 1e-10, None)
        sims = (norm_docs @ norm_q.T).flatten()

        indices = np.argsort(sims)[::-1][:top_k]
        relevantes = [
            _chunks[i] for i in indices if sims[i] >= SIMILARITY_THRESHOLD
        ]
        if not relevantes:
            return None

        return "\n\n---\n\n".join(relevantes)

    except Exception as e:
        logger.error("RAG: error en búsqueda: %s", e)
        return None
