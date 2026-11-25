import os
import sys
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

class MemoryStore:
    """
    Pillar 3: SQLite FTS5 BM25 Keyword & Structured Episodic Memory Engine.
    High-performance SQLite with WAL journaling and FTS5 BM25 search.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "memory.db")
        else:
            self.db_path = db_path

        self._lock = threading.Lock()
        self._init_database()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_database(self):
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()

            # 1. Facts & Semantic Entity Memory
            cur.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                entity TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Episodic Conversation History
            cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 3. Project & Document Codebase Index
            cur.execute("""
            CREATE TABLE IF NOT EXISTS code_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                chunk_idx INTEGER NOT NULL,
                content TEXT NOT NULL,
                language TEXT,
                mtime REAL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 4. FTS5 Virtual Tables for BM25 Sub-Millisecond Search
            try:
                cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                    category,
                    entity,
                    content,
                    content='facts',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
                """)
            except Exception:
                pass

            try:
                cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
                    content,
                    action,
                    content='conversations',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
                """)
            except Exception:
                pass

            try:
                cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS code_chunks_fts USING fts5(
                    project_name,
                    file_path,
                    content,
                    content='code_chunks',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
                """)
            except Exception:
                pass

            conn.commit()
            conn.close()

    # ─── Fact Management (The Second Brain Facts) ─────────────────────────────

    def save_fact(self, category: str, entity: str, content: str) -> int:
        """Stores or updates a durable user or project fact"""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()

            # Check if this entity and category already exists
            cur.execute("SELECT id FROM facts WHERE category = ? AND entity = ?", (category.lower(), entity.lower()))
            existing = cur.fetchone()

            if existing:
                fact_id = existing["id"]
                cur.execute(
                    "UPDATE facts SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (content.strip(), fact_id)
                )
                try:
                    cur.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
                    cur.execute(
                        "INSERT INTO facts_fts(rowid, category, entity, content) VALUES (?, ?, ?, ?)",
                        (fact_id, category.lower(), entity.lower(), content.strip())
                    )
                except Exception:
                    pass
            else:
                cur.execute(
                    "INSERT INTO facts (category, entity, content) VALUES (?, ?, ?)",
                    (category.lower(), entity.lower(), content.strip())
                )
                fact_id = cur.lastrowid
                try:
                    cur.execute(
                        "INSERT INTO facts_fts(rowid, category, entity, content) VALUES (?, ?, ?, ?)",
                        (fact_id, category.lower(), entity.lower(), content.strip())
                    )
                except Exception:
                    pass

            conn.commit()
            conn.close()
            return fact_id

    def get_all_facts(self, limit: int = 50) -> list:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, category, entity, content, updated_at FROM facts ORDER BY updated_at DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def search_facts(self, query: str, limit: int = 5) -> list:
        """Fast BM25 full-text search across all stored facts"""
        clean_q = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
        if not clean_q:
            return self.get_all_facts(limit=limit)

        conn = self._get_connection()
        cur = conn.cursor()
        results = []

        try:
            # Query FTS index
            fts_query = " OR ".join([f'"{w}"*' for w in clean_q.split() if len(w) > 1])
            if fts_query:
                sql = """
                SELECT f.id, f.category, f.entity, f.content, f.updated_at, rank
                FROM facts_fts fts
                JOIN facts f ON fts.rowid = f.id
                WHERE facts_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """
                cur.execute(sql, (fts_query, limit))
                results = [dict(r) for r in cur.fetchall()]
        except Exception:
            # Fallback to standard LIKE
            sql = "SELECT id, category, entity, content, updated_at FROM facts WHERE content LIKE ? OR entity LIKE ? LIMIT ?"
            cur.execute(sql, (f"%{clean_q}%", f"%{clean_q}%", limit))
            results = [dict(r) for r in cur.fetchall()]

        conn.close()
        return results

    # ─── Episodic Conversation Logging ─────────────────────────────────────────

    def save_conversation_turn(self, role: str, content: str, action: str = None, session_id: str = "default") -> int:
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO conversations (session_id, role, content, action) VALUES (?, ?, ?, ?)",
                (session_id, role, content.strip(), action)
            )
            cid = cur.lastrowid
            try:
                cur.execute(
                    "INSERT INTO conversations_fts (rowid, content, action) VALUES (?, ?, ?)",
                    (cid, content.strip(), action or "")
                )
            except Exception:
                pass
            conn.commit()
            conn.close()
            return cid

    def get_recent_conversations(self, limit: int = 10, session_id: str = None) -> list:
        conn = self._get_connection()
        cur = conn.cursor()
        if session_id:
            cur.execute(
                "SELECT id, role, content, action, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
        else:
            cur.execute(
                "SELECT id, role, content, action, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return list(reversed(rows))

    def compact_conversations(self, max_turns: int = 100, session_id: str = None) -> dict:
        """
        Prunes old conversation turns to prevent unbounded SQLite database growth.
        Retains the most recent `max_turns` records and syncs FTS5 index.
        """
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()

            if session_id:
                cur.execute(
                    "SELECT id FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT -1 OFFSET ?",
                    (session_id, max_turns)
                )
            else:
                cur.execute(
                    "SELECT id FROM conversations ORDER BY id DESC LIMIT -1 OFFSET ?",
                    (max_turns,)
                )

            prune_rows = cur.fetchall()
            prune_ids = [r["id"] for r in prune_rows]
            pruned_count = len(prune_ids)

            if pruned_count > 0:
                placeholders = ",".join("?" for _ in prune_ids)
                cur.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", prune_ids)
                try:
                    cur.execute(f"DELETE FROM conversations_fts WHERE rowid IN ({placeholders})", prune_ids)
                except Exception:
                    pass
                conn.commit()

            conn.close()

        vac_res = self.vacuum()
        return {
            "success": True,
            "pruned_turns": pruned_count,
            "remaining_turns": max_turns,
            "size_kb": vac_res.get("size_kb", 0)
        }

    def search_conversations(self, query: str, limit: int = 5) -> list:
        clean_q = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
        if not clean_q:
            return []

        conn = self._get_connection()
        cur = conn.cursor()
        results = []

        try:
            fts_query = " OR ".join([f'"{w}"*' for w in clean_q.split() if len(w) > 1])
            if fts_query:
                sql = """
                SELECT c.id, c.role, c.content, c.action, c.timestamp
                FROM conversations_fts fts
                JOIN conversations c ON fts.rowid = c.id
                WHERE conversations_fts MATCH ?
                ORDER BY fts.rank
                LIMIT ?
                """
                cur.execute(sql, (fts_query, limit))
                results = [dict(r) for r in cur.fetchall()]
        except Exception:
            sql = "SELECT id, role, content, action, timestamp FROM conversations WHERE content LIKE ? LIMIT ?"
            cur.execute(sql, (f"%{clean_q}%", limit))
            results = [dict(r) for r in cur.fetchall()]

        conn.close()
        return results

    # ─── Codebase & Document Vector/Chunk Indexing (RAG) ───────────────────────

    def index_directory(self, dir_path: str, project_name: str = None, max_files: int = 150) -> dict:
        """
        Recursively indexes code, scripts, configs, and documents in a project directory.
        Chunks large files into coherent blocks and updates the FTS index.
        """
        root = Path(dir_path)
        if not root.exists() or not root.is_dir():
            return {"success": False, "message": f"Path '{dir_path}' is not a valid directory."}

        p_name = project_name or root.name
        supported_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
            ".md", ".txt", ".java", ".kt", ".rs", ".cpp", ".c", ".h", ".cs", ".go", ".yml", ".yaml"
        }
        ignored_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".idea", ".vscode", "data"}
        ignored_names = {"three.min.js", "package-lock.json", "yarn.lock", "test.txt", "memory.db"}

        files_to_index = []
        for p in root.rglob("*"):
            if p.is_file():
                # Skip ignored directories
                if any(part in ignored_dirs for part in p.parts):
                    continue
                # Skip minified bundles, lock files, and test files
                p_lower = p.name.lower()
                if p_lower in ignored_names or p_lower.endswith((".min.js", ".min.css", ".map")) or p_lower.startswith(("temp_", "test_")):
                    continue
                # Skip massive single-file vendor bundles (> 150 KB)
                try:
                    if p.stat().st_size > 150 * 1024:
                        continue
                except OSError:
                    continue

                if p.suffix.lower() in supported_exts:
                    files_to_index.append(p)
                    if len(files_to_index) >= max_files:
                        break

        indexed_chunks = 0
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()

            # Remove existing chunks for this project to refresh
            cur.execute("DELETE FROM code_chunks WHERE project_name = ?", (p_name,))
            try:
                cur.execute("DELETE FROM code_chunks_fts WHERE project_name = ?", (p_name,))
            except Exception:
                pass

            for file_path in files_to_index:
                try:
                    rel_path = str(file_path.relative_to(root))
                    mtime = file_path.stat().st_mtime
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    if not lines:
                        continue

                    # Chunk by ~50 lines with 10 lines overlap
                    chunk_size = 50
                    overlap = 10
                    i = 0
                    chunk_idx = 0

                    while i < len(lines):
                        chunk_lines = lines[i:i + chunk_size]
                        chunk_text = "".join(chunk_lines).strip()
                        if chunk_text:
                            cur.execute(
                                """
                                INSERT INTO code_chunks (project_name, file_path, file_name, chunk_idx, content, language, mtime)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (p_name, rel_path, file_path.name, chunk_idx, chunk_text, file_path.suffix.lstrip("."), mtime)
                            )
                            cid = cur.lastrowid
                            try:
                                cur.execute(
                                    "INSERT INTO code_chunks_fts (rowid, project_name, file_path, content) VALUES (?, ?, ?, ?)",
                                    (cid, p_name, rel_path, chunk_text)
                                )
                            except Exception:
                                pass
                            indexed_chunks += 1
                            chunk_idx += 1

                        i += (chunk_size - overlap)
                except Exception as ex:
                    continue

            conn.commit()
            conn.close()

        return {
            "success": True,
            "project_name": p_name,
            "files_indexed": len(files_to_index),
            "chunks_created": indexed_chunks,
            "message": f"Successfully indexed {len(files_to_index)} files ({indexed_chunks} semantic blocks) for project '{p_name}', Sir."
        }

    def search_codebase(self, query: str, project_name: str = None, limit: int = 5) -> list:
        """
        Fast RAG query across indexed code, APIs, endpoints, and documents.
        """
        clean_q = "".join(c if c.isalnum() or c.isspace() or c in "_/-" else " " for c in query).strip()
        if not clean_q:
            return []

        conn = self._get_connection()
        cur = conn.cursor()
        results = []

        try:
            tokens = [t.strip() for t in clean_q.split() if len(t.strip()) > 1]
            fts_query = " OR ".join([f'"{t}"*' for t in tokens])

            if fts_query:
                if project_name:
                    sql = """
                    SELECT c.id, c.project_name, c.file_path, c.file_name, c.chunk_idx, c.content, c.language
                    FROM code_chunks_fts fts
                    JOIN code_chunks c ON fts.rowid = c.id
                    WHERE code_chunks_fts MATCH ? AND c.project_name = ?
                    ORDER BY fts.rank
                    LIMIT ?
                    """
                    cur.execute(sql, (fts_query, project_name, limit))
                else:
                    sql = """
                    SELECT c.id, c.project_name, c.file_path, c.file_name, c.chunk_idx, c.content, c.language
                    FROM code_chunks_fts fts
                    JOIN code_chunks c ON fts.rowid = c.id
                    WHERE code_chunks_fts MATCH ?
                    ORDER BY fts.rank
                    LIMIT ?
                    """
                    cur.execute(sql, (fts_query, limit))

                results = [dict(r) for r in cur.fetchall()]
        except Exception:
            # Fallback LIKE query
            if project_name:
                sql = "SELECT id, project_name, file_path, file_name, chunk_idx, content, language FROM code_chunks WHERE content LIKE ? AND project_name = ? LIMIT ?"
                cur.execute(sql, (f"%{clean_q}%", project_name, limit))
            else:
                sql = "SELECT id, project_name, file_path, file_name, chunk_idx, content, language FROM code_chunks WHERE content LIKE ? LIMIT ?"
                cur.execute(sql, (f"%{clean_q}%", limit))
            results = [dict(r) for r in cur.fetchall()]

        conn.close()
        return results

    def get_memory_stats(self) -> dict:
        """Returns total counts across episodic memory, facts, and code index"""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM facts")
        facts_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM conversations")
        conv_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(DISTINCT file_path) as count FROM code_chunks")
        files_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM code_chunks")
        chunks_count = cur.fetchone()["count"]

        conn.close()
        return {
            "facts": facts_count,
            "conversations": conv_count,
            "indexed_files": files_count,
            "indexed_chunks": chunks_count
        }

    def vacuum(self) -> dict:
        """Forces WAL checkpoint and SQLite database compaction."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cur.execute("VACUUM")
            cur.execute("PRAGMA optimize")
            conn.close()
        p = Path(self.db_path)
        size_kb = round(p.stat().st_size / 1024, 1) if p.exists() else 0
        return {"success": True, "size_kb": size_kb}
