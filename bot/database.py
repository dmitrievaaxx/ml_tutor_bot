"""
Database models and initialization for ML Tutor Bot
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


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
