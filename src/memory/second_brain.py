import os
import re
from pathlib import Path
from .store import MemoryStore

class SecondBrain:
    """
    Pillar 3 Coordinator: SQLite FTS5 BM25 Episodic & Project Memory (The Second Brain).
    Extracts structured facts, indexes codebases, and provides BM25 keyword recall to JarvisBrain.
    """

    def __init__(self, db_path: str = None):
        self.store = MemoryStore(db_path)
        self._seed_default_memories_if_empty()

    def _seed_default_memories_if_empty(self):
        stats = self.store.get_memory_stats()
        if stats["facts"] == 0:
            self.store.save_fact(
                category="persona",
                entity="jarvis",
                content="JARVIS (Aether) is the user's high-intelligence cybernetic OS assistant running natively on Windows 11."
            )
            self.store.save_fact(
                category="user_preference",
                entity="coding_style",
                content="User prefers clean, modular code architecture with type annotations, zero bloat, and fast execution."
            )
            self.store.save_fact(
                category="team",
                entity="rahul",
                content="Rahul is the teammate and backend lead working on the authentication and database modules."
            )
            self.store.save_fact(
                category="project",
                entity="auth_module",
                content="The auth module exposes endpoints including POST /api/v1/auth/login, POST /api/v1/auth/refresh, and GET /api/v1/auth/me."
            )

    def extract_fact_from_text(self, text: str) -> dict:
        """
        Detects if the user is asking to store a memory/fact, extracts the entity, and saves it.
        e.g. 'remember that my name is Tony', 'remember that Rahul is on vacation', 'my preferred port is 8080'
        """
        t = text.strip()
        lower = t.lower()

        # Check for explicit "remember that..." or "remember ..."
        match = re.search(r"^(?:please\s+)?(?:remember\s+that|remember|note\s+that|save\s+to\s+memory)\s+(.+)", lower)
        if match:
            fact_body = t[match.start(1):].strip()

            # Determine category and entity
            category = "general"
            entity = "system"

            if any(w in fact_body.lower() for w in ["i prefer", "my favorite", "my preferred", "i like", "always"]):
                category = "user_preference"
                entity = "user"
            elif any(w in fact_body.lower() for w in ["name is", "my name"]):
                category = "identity"
                entity = "user"
            elif any(w in fact_body.lower() for w in ["rahul", "alex", "john", "colleague", "teammate", "friend"]):
                category = "team"
                # Extract first proper noun or word
                words = fact_body.split()
                entity = words[0].lower() if words else "team"
            elif any(w in fact_body.lower() for w in ["project", "repo", "api", "endpoint", "module", "port", "database"]):
                category = "project"
                entity = "project_spec"

            fact_id = self.store.save_fact(category, entity, fact_body)
            return {
                "success": True,
                "fact_id": fact_id,
                "category": category,
                "entity": entity,
                "content": fact_body,
                "reply": f"Understood, Sir. I have recorded this in permanent episodic memory: '{fact_body}'."
            }

        return {"success": False}

    def recall_context(self, query: str) -> dict:
        """
        Searches facts, episodic conversation logs, and indexed code chunks for a given query.
        Returns matching context to be injected into the LLM system prompt.
        """
        matched_facts = self.store.search_facts(query, limit=4)
        matched_code = self.store.search_codebase(query, limit=3)
        matched_convs = self.store.search_conversations(query, limit=2)

        prompt_lines = []
        if matched_facts:
            prompt_lines.append("[DURABLE USER & PROJECT FACTS]")
            for f in matched_facts:
                prompt_lines.append(f"- ({f['category'].upper()}) {f['entity']}: {f['content']}")

        if matched_code:
            prompt_lines.append("\n[INDEXED CODEBASE CONTEXT (RAG)]")
            for c in matched_code:
                prompt_lines.append(f"--- File: {c['project_name']}/{c['file_path']} ---")
                prompt_lines.append(c["content"][:350])

        context_str = "\n".join(prompt_lines).strip()
        return {
            "has_context": bool(context_str),
            "context_prompt": context_str,
            "facts": matched_facts,
            "code_chunks": matched_code,
            "conversations": matched_convs
        }

    def answer_memory_query_locally(self, query: str) -> dict:
        """
        Fast-path deterministic memory recall for questions like:
        - 'What was that API endpoint I wrote in the auth module last month?'
        - 'What is my coding style?'
        - 'Who is Rahul?'
        - 'What do you remember about X?'
        """
        q = query.lower()

        # 1. API endpoint / auth module query
        if any(w in q for w in ["api endpoint", "endpoint", "auth module", "login endpoint"]) and any(w in q for w in ["what", "where", "last month", "i wrote", "remember"]):
            facts = self.store.search_facts("auth module endpoint", limit=2)
            code = self.store.search_codebase("auth endpoint", limit=2)

            if facts or code:
                fact_text = facts[0]["content"] if facts else ""
                code_text = f" (Found in {code[0]['file_path']})" if code else ""
                return {
                    "action": "memory_recall",
                    "reply": f"According to episodic memory{code_text}: {fact_text} Sir."
                }

        # 2. Coding style / preferences query
        if any(w in q for w in ["coding style", "how do i code", "my preference", "programming style"]):
            facts = self.store.search_facts("coding style", limit=2)
            if facts:
                return {
                    "action": "memory_recall",
                    "reply": f"From our past sessions, your recorded coding preference is: {facts[0]['content']}, Sir."
                }

        # General user preference query (e.g. "What is my favorite programming language?", "What is my preferred editor?")
        pref_match = re.search(r"(?:what is my|do you know my|what are my)\s+(?:favorite|preferred|fav)\s+([a-zA-Z0-9_\s]+)", q)
        if pref_match:
            item = pref_match.group(1).strip()
            facts = self.store.search_facts(item, limit=2)
            if facts:
                return {
                    "action": "memory_recall",
                    "reply": f"According to episodic memory, your preference for {item} is: {facts[0]['content']}, Sir."
                }

        # 3. Teammate / person query (e.g. "Who is Rahul?", "Do you remember Rahul?")
        person_match = re.search(r"(?:who is|what do you know about|tell me about|remember)\s+([a-zA-Z]+)", q)
        if person_match:
            person_name = person_match.group(1).lower()
            if person_name not in ["the", "my", "this", "that", "it", "time", "weather", "you"]:
                facts = self.store.search_facts(person_name, limit=2)
                if facts:
                    return {
                        "action": "memory_recall",
                        "reply": f"Regarding {person_name.title()}: {facts[0]['content']}, Sir."
                    }

        # 4. Memory stats / overview
        if any(w in q for w in ["memory status", "memory stats", "show memory", "what do you remember", "second brain"]):
            stats = self.store.get_memory_stats()
            facts = self.store.get_all_facts(limit=3)
            facts_sample = "; ".join([f["content"] for f in facts])
            return {
                "action": "memory_stats",
                "reply": f"Second Brain telemetry: {stats['facts']} persistent facts, {stats['conversations']} conversational turns, and {stats['indexed_chunks']} indexed code blocks across {stats['indexed_files']} files. Active highlights: {facts_sample}."
            }

        # 5. Index codebase command
        if any(w in q for w in ["index codebase", "index project", "index repository", "index my code", "index repo"]):
            # Index current directory by default
            cur_dir = str(Path(__file__).resolve().parent.parent.parent)
            res = self.store.index_directory(cur_dir, project_name="piko-pc")
            return {
                "action": "index_codebase",
                "reply": res.get("message", "Project indexed into Second Brain.")
            }

        # 6. Compact memory command
        if any(w in q for w in ["compact memory", "clean memory", "prune memory", "compact conversations"]):
            res = self.compact_conversations(max_turns=50)
            return {
                "action": "compact_memory",
                "reply": f"Second Brain compaction complete: pruned {res['pruned_turns']} old turns, retained the latest {res['remaining_turns']} turns. Database size: {res['size_kb']} KB."
            }

        return {"action": None}

    def compact_conversations(self, max_turns: int = 100, session_id: str = None) -> dict:
        """Exposes storage compaction to JarvisBrain and UI API."""
        return self.store.compact_conversations(max_turns=max_turns, session_id=session_id)
