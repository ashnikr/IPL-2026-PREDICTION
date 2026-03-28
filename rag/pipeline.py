"""
RAG (Retrieval-Augmented Generation) Pipeline.

Retrieves live cricket information from:
  - News articles
  - Injury updates
  - Squad announcements
  - Pitch reports

Uses ChromaDB as vector store for fast retrieval.
Integrates with OpenAI or local embeddings for semantic search.
"""

import json
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from utils.logger import logger
from config.settings import settings

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False
    logger.info("ChromaDB not installed. RAG will use keyword search fallback.")

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class IPLRAGPipeline:
    """RAG pipeline for cricket knowledge retrieval."""

    def __init__(self):
        self.data_dir = settings.data_dir / "rag"
        self.data_dir.mkdir(exist_ok=True)
        self.documents = []
        self.collection = None

        if HAS_CHROMA:
            self._init_chromadb()

    def _init_chromadb(self):
        """Initialize ChromaDB vector store."""
        try:
            self.client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
            ))
            self.collection = self.client.get_or_create_collection(
                name="ipl_knowledge",
                metadata={"description": "IPL cricket knowledge base"},
            )
            logger.info("ChromaDB initialized")
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e}")
            self.collection = None

    def ingest_documents(self, documents: list[dict]):
        """
        Ingest documents into the knowledge base.

        Each document: {"text": "...", "source": "...", "category": "..."}
        """
        logger.info(f"Ingesting {len(documents)} documents...")

        for doc in documents:
            text = doc.get("text", "")
            source = doc.get("source", "unknown")
            category = doc.get("category", "general")
            doc_id = hashlib.md5(text[:200].encode()).hexdigest()

            # Store locally
            self.documents.append({
                "id": doc_id,
                "text": text,
                "source": source,
                "category": category,
                "ingested_at": datetime.now().isoformat(),
            })

            # Add to vector store
            if self.collection is not None:
                try:
                    self.collection.add(
                        documents=[text],
                        metadatas=[{"source": source, "category": category}],
                        ids=[doc_id],
                    )
                except Exception as e:
                    logger.warning(f"Failed to add to ChromaDB: {e}")

        # Save local backup
        self._save_documents()
        logger.info(f"Ingested {len(documents)} documents. Total: {len(self.documents)}")

    def ingest_from_scrapers(self):
        """Automatically ingest data from all scrapers."""
        logger.info("Auto-ingesting from scrapers...")

        documents = []

        # 1. Injury updates
        try:
            from scrapers.cricbuzz_scraper import CricbuzzScraper
            cb = CricbuzzScraper()
            injuries = cb.get_injury_updates()
            for inj in injuries:
                documents.append({
                    "text": inj.get("headline", ""),
                    "source": "cricbuzz",
                    "category": "injury",
                })
        except Exception as e:
            logger.warning(f"Injury ingestion failed: {e}")

        # 2. Team stats as knowledge
        try:
            from models.bayesian_model import BayesianPredictor
            bayesian = BayesianPredictor()
            bayesian.load()
            for team, stats in bayesian.team_strengths.items():
                text = (
                    f"{team} has a Bayesian strength of {stats.get('mean_strength', 0.5):.3f}. "
                    f"Wins: {stats.get('wins', 0)}, Losses: {stats.get('losses', 0)}."
                )
                documents.append({
                    "text": text,
                    "source": "bayesian_model",
                    "category": "team_stats",
                })
        except Exception as e:
            logger.warning(f"Team stats ingestion failed: {e}")

        # 3. Venue knowledge
        try:
            import pandas as pd
            matches = pd.read_csv(settings.processed_data_dir / "matches_processed.csv")
            for venue in matches["venue"].dropna().unique():
                vm = matches[matches["venue"] == venue]
                if len(vm) >= 5:
                    avg_score = vm.get("inn1_total_runs", pd.Series()).mean()
                    text = (
                        f"Venue: {venue}. Total matches: {len(vm)}. "
                        f"Average first innings score: {avg_score:.0f}."
                    )
                    documents.append({
                        "text": text,
                        "source": "historical_data",
                        "category": "venue",
                    })
        except Exception as e:
            logger.warning(f"Venue ingestion failed: {e}")

        # 4. Squad information
        try:
            from scrapers.live_data_scraper import LiveDataScraper
            live = LiveDataScraper()
            squads = live.get_team_squads()
            for team, players in squads.items():
                player_names = [p if isinstance(p, str) else p.get("name", "") for p in players]
                text = f"{team} squad: {', '.join(player_names[:15])}"
                documents.append({
                    "text": text,
                    "source": "squad_data",
                    "category": "squad",
                })
        except Exception as e:
            logger.warning(f"Squad ingestion failed: {e}")

        if documents:
            self.ingest_documents(documents)

    def query(self, question: str, n_results: int = 5) -> list[dict]:
        """Query the knowledge base."""
        logger.info(f"RAG query: {question[:80]}...")

        # Try ChromaDB first
        if self.collection is not None:
            try:
                results = self.collection.query(
                    query_texts=[question],
                    n_results=n_results,
                )
                if results and results.get("documents"):
                    return [
                        {
                            "text": doc,
                            "metadata": meta,
                            "distance": dist,
                        }
                        for doc, meta, dist in zip(
                            results["documents"][0],
                            results["metadatas"][0],
                            results["distances"][0],
                        )
                    ]
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}")

        # Fallback: keyword search
        return self._keyword_search(question, n_results)

    def _keyword_search(self, question: str, n_results: int) -> list[dict]:
        """Simple keyword-based search fallback."""
        if not self.documents:
            self._load_documents()

        keywords = question.lower().split()
        scored = []

        for doc in self.documents:
            text = doc["text"].lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {"text": doc["text"], "metadata": {"source": doc["source"], "category": doc["category"]}}
            for _, doc in scored[:n_results]
        ]

    def get_context_for_match(self, team1: str, team2: str, venue: str = "") -> str:
        """Get relevant context for a specific match prediction."""
        queries = [
            f"{team1} vs {team2}",
            f"{team1} recent form",
            f"{team2} recent form",
            f"{venue} pitch conditions" if venue else "",
            f"{team1} injuries",
            f"{team2} injuries",
        ]

        all_results = []
        for q in queries:
            if q:
                results = self.query(q, n_results=2)
                all_results.extend(results)

        # Deduplicate and format
        seen = set()
        context_parts = []
        for r in all_results:
            text = r["text"]
            if text not in seen:
                seen.add(text)
                context_parts.append(text)

        return "\n".join(context_parts[:10])

    def _save_documents(self):
        """Save documents to disk."""
        filepath = self.data_dir / "documents.json"
        with open(filepath, "w") as f:
            json.dump(self.documents, f, indent=2, default=str)

    def _load_documents(self):
        """Load documents from disk."""
        filepath = self.data_dir / "documents.json"
        if filepath.exists():
            with open(filepath) as f:
                self.documents = json.load(f)
            logger.info(f"Loaded {len(self.documents)} documents from disk")
