"""
Database models and initialization for ML Tutor Bot
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Course:
    id: int
    name: str
    description: str
    total_lessons: int


@dataclass
class Lesson:
    id: int
    course_id: int
    lesson_number: int
    title: str
    content: str


@dataclass
class UserProgress:
    user_id: int
    course_id: int
    current_lesson: int
    completed_lessons: int


@dataclass
class LessonCompletion:
    user_id: int
    lesson_id: int
    completed_at: datetime


@dataclass
class TestError:
    id: int
    user_id: int
    lesson_id: int
    question: str
    correct_answer: str
    user_answer: str
    created_at: datetime


class Database:
    def __init__(self, db_path: str = "ml_tutor.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Courses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                total_lessons INTEGER NOT NULL
            )
        """)
        
        # Lessons table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                lesson_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses (id),
                UNIQUE(course_id, lesson_number)
            )
        """)
        
        # User progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                current_lesson INTEGER DEFAULT 1,
                completed_lessons INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, course_id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        """)
        
        # Lesson completions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lesson_completions (
                user_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, lesson_id),
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            )
        """)
        
        # Test errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            )
        """)
        
        # RAG Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_preview TEXT,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                metadata TEXT,
                arxiv_id TEXT,
                authors TEXT,
                status TEXT DEFAULT 'processing'
            )
        """)
        
        # User documents relationship table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_documents (
                user_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, document_id),
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def create_course(self, name: str, description: str, total_lessons: int) -> int:
        """Create a new course and return its ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO courses (name, description, total_lessons)
            VALUES (?, ?, ?)
        """, (name, description, total_lessons))
        
        course_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return course_id
    
    def update_course(self, course_id: int, name: str = None, description: str = None, total_lessons: int = None):
        """Update course information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if total_lessons is not None:
            updates.append("total_lessons = ?")
            params.append(total_lessons)
        
        if updates:
            params.append(course_id)
            cursor.execute(f"""
                UPDATE courses 
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
        
        conn.close()
    
    def get_all_courses(self) -> List[Course]:
        """Get all courses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, total_lessons
            FROM courses ORDER BY id
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Course(id=row[0], name=row[1], description=row[2], total_lessons=row[3])
            for row in rows
        ]
    
    def get_course_by_name(self, name: str):
        """Get course by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM courses WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Course(id=row[0], name=row[1], description=row[2], total_lessons=row[3])
        return None
    
    def add_lesson(self, course_id: int, lesson_number: int, title: str, content: str):
        """Add a lesson to a course"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO lessons (course_id, lesson_number, title, content)
            VALUES (?, ?, ?, ?)
        """, (course_id, lesson_number, title, content))
        
        conn.commit()
        conn.close()
    
    def get_course(self, course_id: int) -> Optional[Course]:
        """Get course by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, total_lessons
            FROM courses WHERE id = ?
        """, (course_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Course(id=row[0], name=row[1], description=row[2], total_lessons=row[3])
        return None
    
    def get_lesson(self, course_id: int, lesson_number: int) -> Optional[Lesson]:
        """Get lesson by course ID and lesson number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, course_id, lesson_number, title, content
            FROM lessons WHERE course_id = ? AND lesson_number = ?
        """, (course_id, lesson_number))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Lesson(id=row[0], course_id=row[1], lesson_number=row[2], title=row[3], content=row[4])
        return None
    
    def get_user_progress(self, user_id: int, course_id: int) -> Optional[UserProgress]:
        """Get user progress for a course"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, course_id, current_lesson, completed_lessons
            FROM user_progress WHERE user_id = ? AND course_id = ?
        """, (user_id, course_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserProgress(user_id=row[0], course_id=row[1], current_lesson=row[2], completed_lessons=row[3])
        return None
    
    def init_user_progress(self, user_id: int, course_id: int):
        """Initialize user progress for a course"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO user_progress (user_id, course_id, current_lesson, completed_lessons)
            VALUES (?, ?, 1, 0)
        """, (user_id, course_id))
        
        conn.commit()
        conn.close()
    
    def update_user_progress(self, user_id: int, course_id: int, current_lesson: int, completed_lessons: int):
        """Update user progress"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_progress 
            SET current_lesson = ?, completed_lessons = ?
            WHERE user_id = ? AND course_id = ?
        """, (current_lesson, completed_lessons, user_id, course_id))
        
        conn.commit()
        conn.close()
    
    def complete_lesson(self, user_id: int, lesson_id: int):
        """Mark lesson as completed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO lesson_completions (user_id, lesson_id)
            VALUES (?, ?)
        """, (user_id, lesson_id))
        
        conn.commit()
        conn.close()
    
    def add_test_error(self, user_id: int, lesson_id: int, question: str, correct_answer: str, user_answer: str):
        """Add test error"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO test_errors (user_id, lesson_id, question, correct_answer, user_answer)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, lesson_id, question, correct_answer, user_answer))
        
        conn.commit()
        conn.close()
    
    def get_user_completed_lessons(self, user_id: int, course_id: int) -> List[int]:
        """Get list of completed lesson numbers for a user in a course"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.lesson_number
            FROM lesson_completions lc
            JOIN lessons l ON lc.lesson_id = l.id
            WHERE lc.user_id = ? AND l.course_id = ?
            ORDER BY l.lesson_number
        """, (user_id, course_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def get_user_test_errors(self, user_id: int) -> List[TestError]:
        """Get all test errors for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, lesson_id, question, correct_answer, user_answer, created_at
            FROM test_errors WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            TestError(
                id=row[0], user_id=row[1], lesson_id=row[2], 
                question=row[3], correct_answer=row[4], user_answer=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            for row in rows
        ]
    
    def get_user_course_stats(self, user_id: int, course_id: int) -> Dict[str, Any]:
        """Get user statistics for a course"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get progress
        progress = self.get_user_progress(user_id, course_id)
        
        # Get error count
        cursor.execute("""
            SELECT COUNT(*) FROM test_errors 
            WHERE user_id = ? AND lesson_id IN (
                SELECT id FROM lessons WHERE course_id = ?
            )
        """, (user_id, course_id))
        
        error_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "current_lesson": progress.current_lesson if progress else 1,
            "completed_lessons": progress.completed_lessons if progress else 0,
            "error_count": error_count
        }
    
    def load_course_from_json(self, json_path: str):
        """Load course data from JSON file"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create course
        course_id = self.create_course(
            name=data['course'],
            description=f"Курс по {data['course']}",
            total_lessons=len(data['lessons'])
        )
        
        # Add lessons
        for lesson_data in data['lessons']:
            self.add_lesson(
                course_id=course_id,
                lesson_number=lesson_data['lesson_number'],
                title=lesson_data['title'],
                content=lesson_data['content']
            )
        
        return course_id
    
    def clear_user_progress(self, user_id: int):
        """Clear all progress for a user (all courses)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete user progress for all courses
        cursor.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
        
        # Delete lesson completions
        cursor.execute("DELETE FROM lesson_completions WHERE user_id = ?", (user_id,))
        
        # Delete test errors
        cursor.execute("DELETE FROM test_errors WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Очищен весь прогресс пользователя {user_id}")
    
    # RAG Document methods
    def add_document(self, title: str, content_preview: str, file_type: str, user_id: int, 
                    file_size: int = None, metadata: dict = None, arxiv_id: str = None, 
                    authors: str = None) -> int:
        """Add a new document and return its ID (KISS: replaces old document)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Удаляем старый документ пользователя (KISS принцип)
        cursor.execute("DELETE FROM user_documents WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM documents WHERE user_id = ?", (user_id,))
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO documents (title, content_preview, file_type, file_size, 
                                 user_id, metadata, arxiv_id, authors, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processed')
        """, (title, content_preview, file_type, file_size, user_id, 
              metadata_json, arxiv_id, authors))
        
        doc_id = cursor.lastrowid
        
        # Link document to user
        cursor.execute("""
            INSERT INTO user_documents (user_id, document_id)
            VALUES (?, ?)
        """, (user_id, doc_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Добавлен документ {title} для пользователя {user_id} (заменил старый)")
        return doc_id
    
    def get_user_document(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get current document for a user (KISS: only one document per user)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.id, d.title, d.content_preview, d.file_type, d.file_size,
                   d.uploaded_at, d.metadata, d.arxiv_id, d.authors, d.status
            FROM documents d
            JOIN user_documents ud ON d.id = ud.document_id
            WHERE ud.user_id = ?
            ORDER BY d.uploaded_at DESC
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'content_preview': row[2],
                'file_type': row[3],
                'file_size': row[4],
                'uploaded_at': datetime.fromisoformat(row[5]) if row[5] else None,
                'metadata': json.loads(row[6]) if row[6] else {},
                'arxiv_id': row[7],
                'authors': row[8],
                'status': row[9]
            }
        return None
    
    def has_user_documents(self, user_id: int) -> bool:
        """Check if user has any documents"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM user_documents WHERE user_id = ?
        """, (user_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
