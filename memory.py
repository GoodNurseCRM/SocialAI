import sqlite3
import os

class AgentMemory:
    def __init__(self, db_path="./sqlite_memory.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_post TEXT,
                drafted_text TEXT,
                status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networked_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                identifier TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                title TEXT,
                description TEXT,
                rationale TEXT,
                pros TEXT,
                cons TEXT,
                cost_estimate TEXT,
                expected_impact TEXT,
                implementation_steps TEXT,
                suggestion_type TEXT,
                urgency TEXT DEFAULT 'MEDIUM',
                auto_implementable INTEGER DEFAULT 0,
                implementation_data TEXT,
                status TEXT DEFAULT 'pending',
                result_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brief_date TEXT UNIQUE,
                brief_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                params TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def log_feedback(self, drafted_text: str, status: str, original_post: str = ""):
        """
        Logs a generated comment and whether it was approved or rejected.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO post_feedback (original_post, drafted_text, status) VALUES (?, ?, ?)",
            (original_post, drafted_text, status)
        )
        conn.commit()
        conn.close()
        print(f"Logged {status} feedback to memory.")

    def get_past_learnings(self, context_query: str, n_results: int = 3) -> str:
        """
        Retrieves past approved/rejected responses to inform the LLM style.
        Since we are using SQLite, it returns the most recent interactions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, original_post, drafted_text FROM post_feedback ORDER BY id DESC LIMIT ?", (n_results * 2,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No past memory available yet."
            
        learnings = ["--- PAST EXAMPLES ---"]
        for row in rows:
            learnings.append(f"Original Post: {row[1]}\nDrafted Response: {row[2]}\nOutcome: {row[0].upper()}")
            
        return "\n\n".join(learnings)
        
    def has_networked(self, platform: str, identifier: str) -> bool:
        """Checks if the bot has already connected/joined this specific profile/group."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM networked_profiles WHERE platform=? AND identifier=?", (platform, identifier))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
        
    def record_networked(self, platform: str, identifier: str):
        """Saves a profile/group into the anti-spam tracker database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO networked_profiles (platform, identifier) VALUES (?, ?)", (platform, identifier))
            conn.commit()
        except sqlite3.Error as e:
            print(f"DB Error tracking network event: {e}")
        finally:
            conn.close()
