import json
import os
import re
import math
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
# Configure Flask to serve static files from the 'static' directory
app.static_folder = 'static'
DEFAULT_WORD_LIMIT = 50
REVIEW_INTERVALS = [0, 1, 2, 3, 5, 7, 9, 12, 14, 17, 21]

# Mapping of word list files to student folders
file_to_student_mapping = {
    '中考词汇.txt': '初二男',
    '高考词汇.txt': '英语',
    '雅思基础词汇.txt': '英语',
    '法语单词.txt': '法语',
    '你好法语.txt': '法语',
    '法语妈妈.txt': '妈妈',
    '中考考纲词组.txt': '中考考纲学生',
}


def get_sub_folder_path(folder_name='data'):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_directory, folder_name)


class TxtReader:
    def __init__(self):
        self.data_folder = get_sub_folder_path('data')
        self.db_path = os.path.join(self.data_folder, 'learning.db')
        self.database_url = os.getenv('DATABASE_URL', '').strip()
        self.is_postgres = bool(self.database_url)
        self.engine = self.create_engine()
        self.file_choices = list(file_to_student_mapping.keys())
        self.init_db()
        self.seed_words_if_needed()
        self.seed_default_students()
        self.backfill_default_student_file_access()

    def create_engine(self):
        if self.database_url:
            normalized = self.database_url
            if normalized.startswith('postgres://'):
                normalized = normalized.replace('postgres://', 'postgresql://', 1)
            return create_engine(normalized, pool_pre_ping=True, future=True)
        os.makedirs(self.data_folder, exist_ok=True)
        return create_engine(f"sqlite:///{self.db_path}", connect_args={'check_same_thread': False}, future=True)

    def init_db(self):
        id_col = 'SERIAL PRIMARY KEY' if self.is_postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS students (
                        id {id_col},
                        name TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS users (
                        id {id_col},
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        student_id INTEGER,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(student_id) REFERENCES students(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS words (
                        id {id_col},
                        source_file TEXT NOT NULL,
                        term TEXT NOT NULL,
                        meaning TEXT,
                        created_at TEXT NOT NULL,
                        UNIQUE(source_file, term)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS learning_actions (
                        id {id_col},
                        student_id INTEGER NOT NULL,
                        word_id INTEGER NOT NULL,
                        action_type TEXT NOT NULL,
                        action_time TEXT NOT NULL,
                        FOREIGN KEY(student_id) REFERENCES students(id),
                        FOREIGN KEY(word_id) REFERENCES words(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS student_word_progress (
                        student_id INTEGER NOT NULL,
                        word_id INTEGER NOT NULL,
                        mastery_level INTEGER NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'new',
                        last_action TEXT,
                        next_review_date TEXT,
                        PRIMARY KEY(student_id, word_id),
                        FOREIGN KEY(student_id) REFERENCES students(id),
                        FOREIGN KEY(word_id) REFERENCES words(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS review_schedule (
                        id {id_col},
                        student_id INTEGER NOT NULL,
                        word_id INTEGER NOT NULL,
                        review_date TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_from_action_id INTEGER,
                        UNIQUE(student_id, word_id, review_date),
                        FOREIGN KEY(student_id) REFERENCES students(id),
                        FOREIGN KEY(word_id) REFERENCES words(id),
                        FOREIGN KEY(created_from_action_id) REFERENCES learning_actions(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS learning_sessions (
                        id {id_col},
                        teacher_user_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        source_file TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'draft',
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        FOREIGN KEY(student_id) REFERENCES students(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS learning_session_words (
                        id {id_col},
                        session_id INTEGER NOT NULL,
                        word_id INTEGER NOT NULL,
                        display_order INTEGER NOT NULL,
                        initial_status TEXT NOT NULL,
                        final_learned INTEGER,
                        FOREIGN KEY(session_id) REFERENCES learning_sessions(id),
                        FOREIGN KEY(word_id) REFERENCES words(id),
                        UNIQUE(session_id, word_id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS student_source_files (
                        student_id INTEGER NOT NULL,
                        source_file TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY(student_id, source_file),
                        FOREIGN KEY(student_id) REFERENCES students(id)
                    )
                    """
                )
            )

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hint TEXT"))
            except Exception:
                # Column already exists in migrated databases.
                pass

    def seed_default_students(self):
        default_students = sorted(set(file_to_student_mapping.values()))
        with self.engine.begin() as conn:
            for student_name in default_students:
                exists = conn.execute(
                    text("SELECT id FROM students WHERE name = :name"),
                    {'name': student_name},
                ).first()
                if not exists:
                    conn.execute(
                        text("INSERT INTO students(name, created_at) VALUES (:name, :created_at)"),
                        {'name': student_name, 'created_at': datetime.now().isoformat()},
                    )

    def backfill_default_student_file_access(self):
        now = datetime.now().isoformat()
        with self.engine.begin() as conn:
            for source_file, student_name in file_to_student_mapping.items():
                student = conn.execute(
                    text("SELECT id FROM students WHERE name = :name"),
                    {'name': student_name},
                ).mappings().first()
                if not student:
                    continue
                exists = conn.execute(
                    text(
                        "SELECT 1 FROM student_source_files "
                        "WHERE student_id = :student_id AND source_file = :source_file"
                    ),
                    {'student_id': student['id'], 'source_file': source_file},
                ).first()
                if not exists:
                    conn.execute(
                        text(
                            "INSERT INTO student_source_files(student_id, source_file, created_at) "
                            "VALUES (:student_id, :source_file, :created_at)"
                        ),
                        {'student_id': student['id'], 'source_file': source_file, 'created_at': now},
                    )

    def seed_default_users(self):
        teacher_username = os.getenv('TEACHER_USERNAME', 'teacher').strip() or 'teacher'
        teacher_password = os.getenv('TEACHER_PASSWORD', 'teacher123')
        now = datetime.now().isoformat()

        with self.engine.begin() as conn:
            teacher = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {'username': teacher_username},
            ).first()
            if not teacher:
                conn.execute(
                    text(
                        """
                        INSERT INTO users(username, password_hash, password_hint, role, student_id, is_active, created_at)
                        VALUES (:username, :password_hash, :password_hint, 'teacher', NULL, 1, :created_at)
                        """
                    ),
                    {
                        'username': teacher_username,
                        'password_hash': generate_password_hash(teacher_password),
                        'password_hint': teacher_password,
                        'created_at': now,
                    },
                )

    def authenticate(self, username, password, role):
        with self.engine.begin() as conn:
            user = conn.execute(
                text(
                    """
                    SELECT u.id, u.username, u.password_hash, u.role, u.student_id, s.name AS student_name
                    FROM users u
                    LEFT JOIN students s ON s.id = u.student_id
                    WHERE u.username = :username
                      AND u.role = :role
                      AND u.is_active = 1
                    """
                ),
                {'username': username, 'role': role},
            ).mappings().first()

        if not user or not check_password_hash(user['password_hash'], password):
            return None
        return user

    def get_student_accounts(self):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                          SELECT u.id,
                              u.student_id,
                           u.username,
                           COALESCE(u.password_hint, '123456') AS password_hint,
                           s.name AS student_name
                    FROM users u
                    JOIN students s ON s.id = u.student_id
                    WHERE u.role = 'student' AND u.is_active = 1
                    ORDER BY u.username
                    """
                )
            ).mappings().all()

            account_list = []
            for row in rows:
                sources = conn.execute(
                    text(
                        """
                        SELECT source_file
                        FROM student_source_files
                        WHERE student_id = :student_id
                        ORDER BY source_file
                        """
                    ),
                    {'student_id': row['student_id']},
                ).mappings().all()
                account_list.append(
                    {
                        'username': row['username'],
                        'password_hint': row['password_hint'],
                        'student_name': row['student_name'],
                        'source_files': [s['source_file'] for s in sources],
                    }
                )
        return account_list

    def get_student_id_by_name(self, student_name):
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id FROM students WHERE name = :name"),
                {'name': student_name},
            ).mappings().first()
        return row['id'] if row else None

    def get_allowed_files_for_student(self, student_id):
        if not student_id:
            return []
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT source_file
                    FROM student_source_files
                    WHERE student_id = :student_id
                    ORDER BY source_file
                    """
                ),
                {'student_id': student_id},
            ).mappings().all()
        return [row['source_file'] for row in rows]

    def get_allowed_files_for_student_name(self, student_name):
        student_id = self.get_student_id_by_name(student_name)
        return self.get_allowed_files_for_student(student_id)

    def set_student_source_files(self, student_id, source_files):
        cleaned = [source_file for source_file in source_files if source_file in self.file_choices]
        now = datetime.now().isoformat()
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM student_source_files WHERE student_id = :student_id"),
                {'student_id': student_id},
            )
            for source_file in cleaned:
                conn.execute(
                    text(
                        """
                        INSERT INTO student_source_files(student_id, source_file, created_at)
                        VALUES (:student_id, :source_file, :created_at)
                        """
                    ),
                    {'student_id': student_id, 'source_file': source_file, 'created_at': now},
                )

    @staticmethod
    def _source_label(source_file):
        return source_file.replace('.txt', '').strip()

    def _build_default_student_username(self, student_name, source_files):
        cleaned_sources = [source for source in source_files if source in self.file_choices]
        source_label = self._source_label(cleaned_sources[0]) if cleaned_sources else '未分配词库'
        return f"{source_label}-{student_name}"

    def _ensure_unique_username(self, conn, desired_username):
        username = desired_username
        suffix = 2
        while conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {'username': username},
        ).first():
            username = f"{desired_username}-{suffix}"
            suffix += 1
        return username

    def create_student_account(self, student_name, username, password, source_files):
        student_id, student_name = self.ensure_student(student_name)
        cleaned_sources = [source_file for source_file in source_files if source_file in self.file_choices]
        if not cleaned_sources:
            return False, '请至少分配一个词库源'

        requested_username = username.strip() if username else ''
        if not requested_username:
            requested_username = self._build_default_student_username(student_name, cleaned_sources)

        requested_password = password.strip() if password else '123456'
        now = datetime.now().isoformat()

        with self.engine.begin() as conn:
            if username and conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {'username': requested_username},
            ).first():
                return False, '账号已存在'

            final_username = self._ensure_unique_username(conn, requested_username)

            conn.execute(
                text(
                    """
                    INSERT INTO users(username, password_hash, password_hint, role, student_id, is_active, created_at)
                    VALUES (:username, :password_hash, :password_hint, 'student', :student_id, 1, :created_at)
                    """
                ),
                {
                    'username': final_username,
                    'password_hash': generate_password_hash(requested_password),
                    'password_hint': requested_password,
                    'student_id': student_id,
                    'created_at': now,
                },
            )

        self.set_student_source_files(student_id, cleaned_sources)
        return True, f'创建成功: {final_username} / {requested_password}'

    def get_students(self):
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT name FROM students ORDER BY name")).mappings().all()
        return [row['name'] for row in rows]

    def ensure_student(self, student_name):
        if not student_name:
            student_name = '英语'
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id FROM students WHERE name = :name"),
                {'name': student_name},
            ).mappings().first()
            if not row:
                conn.execute(
                    text("INSERT INTO students(name, created_at) VALUES (:name, :created_at)"),
                    {'name': student_name, 'created_at': datetime.now().isoformat()},
                )
                row = conn.execute(
                    text("SELECT id FROM students WHERE name = :name"),
                    {'name': student_name},
                ).mappings().first()
        return row['id'], student_name

    def read_words_from_txt(self, file_name, limit=DEFAULT_WORD_LIMIT):
        file_path = os.path.join(self.data_folder, file_name)
        words = []
        pattern = re.compile(r'([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s–\.\/\?\？，,’0-9-]+)\s*(.*)')
        with open(file_path, 'r', encoding='utf-8') as file:
            for index, line in enumerate(file, start=1):  # Start index from 1
                if index > limit:  # Break if the limit is reached
                    break
                match = pattern.match(line.strip())
                if match:
                    english_word, translation = match.groups()
                    words.append({"索引": index, "单词": english_word.strip(), "释意": translation})
                else:
                    print(f"Invalid format in line: {line.strip()}")
        return words

    def seed_words_if_needed(self):
        with self.engine.begin() as conn:
            count_row = conn.execute(text("SELECT COUNT(*) AS total FROM words")).mappings().first()
            if count_row['total'] > 0:
                return

            now = datetime.now().isoformat()
            for file_name in self.file_choices:
                for word in self.read_words_from_txt(file_name, limit=10**9):
                    exists = conn.execute(
                        text("SELECT id FROM words WHERE source_file = :source_file AND term = :term"),
                        {'source_file': file_name, 'term': word['单词']},
                    ).first()
                    if not exists:
                        conn.execute(
                            text(
                                """
                                INSERT INTO words(source_file, term, meaning, created_at)
                                VALUES (:source_file, :term, :meaning, :created_at)
                                """
                            ),
                            {
                                'source_file': file_name,
                                'term': word['单词'],
                                'meaning': word['释意'],
                                'created_at': now,
                            },
                        )

    def get_words_for_mode(self, student_id, file_name, learning_mode='new', limit=DEFAULT_WORD_LIMIT):
        with self.engine.begin() as conn:
            today = datetime.now().strftime('%Y-%m-%d')
            if learning_mode == 'review':
                rows = conn.execute(
                    text(
                        """
                        SELECT w.id, w.term, w.meaning
                        FROM review_schedule rs
                        JOIN words w ON w.id = rs.word_id
                        WHERE rs.student_id = :student_id
                          AND rs.status = 'pending'
                          AND rs.review_date <= :today
                          AND w.source_file = :source_file
                        ORDER BY rs.review_date, rs.id
                        LIMIT :limit
                        """
                    ),
                    {'student_id': student_id, 'source_file': file_name, 'limit': limit, 'today': today},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT w.id, w.term, w.meaning
                        FROM words w
                        LEFT JOIN student_word_progress p
                          ON p.word_id = w.id AND p.student_id = :student_id
                        WHERE w.source_file = :source_file
                          AND (p.status IS NULL OR p.status != 'known')
                        ORDER BY w.id
                        LIMIT :limit
                        """
                    ),
                    {'student_id': student_id, 'source_file': file_name, 'limit': limit},
                ).mappings().all()

        words = []
        for idx, row in enumerate(rows, start=1):
            words.append({'索引': idx, '单词': row['term'], '释意': row['meaning'], 'id': row['id']})
        return words

    def get_words_from_file(self, file_name, limit=DEFAULT_WORD_LIMIT):
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, term, meaning
                    FROM words
                    WHERE source_file = :source_file
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {'source_file': file_name, 'limit': limit},
            ).mappings().all()

        return [
            {'id': row['id'], 'term': row['term'], 'meaning': row['meaning']}
            for row in rows
        ]

    def create_learning_session(self, teacher_user_id, student_id, file_name, decisions):
        now = datetime.now().isoformat()
        with self.engine.begin() as conn:
            if self.is_postgres:
                session_id = conn.execute(
                    text(
                        """
                        INSERT INTO learning_sessions(teacher_user_id, student_id, source_file, status, created_at)
                        VALUES (:teacher_user_id, :student_id, :source_file, 'training', :created_at)
                        RETURNING id
                        """
                    ),
                    {
                        'teacher_user_id': teacher_user_id,
                        'student_id': student_id,
                        'source_file': file_name,
                        'created_at': now,
                    },
                ).scalar_one()
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO learning_sessions(teacher_user_id, student_id, source_file, status, created_at)
                        VALUES (:teacher_user_id, :student_id, :source_file, 'training', :created_at)
                        """
                    ),
                    {
                        'teacher_user_id': teacher_user_id,
                        'student_id': student_id,
                        'source_file': file_name,
                        'created_at': now,
                    },
                )
                session_id = conn.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()['id']

            display_order = 1
            for word_id, status in decisions:
                conn.execute(
                    text(
                        """
                        INSERT INTO learning_session_words(session_id, word_id, display_order, initial_status, final_learned)
                        VALUES (:session_id, :word_id, :display_order, :initial_status, NULL)
                        """
                    ),
                    {
                        'session_id': session_id,
                        'word_id': word_id,
                        'display_order': display_order,
                        'initial_status': status,
                    },
                )
                display_order += 1

        return session_id

    def get_learning_session(self, session_id):
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT ls.*, s.name AS student_name
                    FROM learning_sessions ls
                    JOIN students s ON s.id = ls.student_id
                    WHERE ls.id = :session_id
                    """
                ),
                {'session_id': session_id},
            ).mappings().first()
        return row

    def get_session_words(self, session_id, initial_status=None):
        query = """
            SELECT lsw.id,
                   lsw.word_id,
                   lsw.display_order,
                   lsw.initial_status,
                   lsw.final_learned,
                   w.term,
                   w.meaning
            FROM learning_session_words lsw
            JOIN words w ON w.id = lsw.word_id
            WHERE lsw.session_id = :session_id
        """
        params = {'session_id': session_id}
        if initial_status:
            query += " AND lsw.initial_status = :initial_status"
            params['initial_status'] = initial_status
        query += " ORDER BY lsw.display_order"

        with self.engine.begin() as conn:
            rows = conn.execute(text(query), params).mappings().all()
        return rows

    def get_training_group(self, session_id, group_no, group_size=5):
        all_unknown = self.get_session_words(session_id, initial_status='unknown')
        total_groups = max(1, (len(all_unknown) + group_size - 1) // group_size)
        start = (group_no - 1) * group_size
        end = start + group_size
        return all_unknown[start:end], total_groups, len(all_unknown)

    def finalize_learning_session(self, session_id, learned_word_ids):
        learned_set = {int(word_id) for word_id in learned_word_ids}
        session_info = self.get_learning_session(session_id)
        if not session_info:
            return None

        all_words = self.get_session_words(session_id)
        known_terms = []
        newly_learned_terms = []
        with self.engine.begin() as conn:
            for row in all_words:
                if row['word_id'] in learned_set:
                    final_learned = 1
                else:
                    final_learned = 1 if row['initial_status'] == 'known' else 0

                conn.execute(
                    text(
                        """
                        UPDATE learning_session_words
                        SET final_learned = :final_learned
                        WHERE id = :id
                        """
                    ),
                    {'final_learned': final_learned, 'id': row['id']},
                )

                if row['initial_status'] == 'known' or final_learned == 1:
                    known_terms.append(row['term'])
                if row['initial_status'] == 'unknown' and final_learned == 1:
                    newly_learned_terms.append(row['term'])

            conn.execute(
                text(
                    """
                    UPDATE learning_sessions
                    SET status = 'completed', completed_at = :completed_at
                    WHERE id = :session_id
                    """
                ),
                {'completed_at': datetime.now().isoformat(), 'session_id': session_id},
            )

        self.mark_words_known(session_info['student_id'], session_info['source_file'], known_terms)
        if newly_learned_terms:
            self.schedule_review_words(session_info['student_id'], session_info['source_file'], newly_learned_terms)

        return {
            'known_count': len(known_terms),
            'newly_learned_count': len(newly_learned_terms),
            'student_name': session_info['student_name'],
            'source_file': session_info['source_file'],
        }

    def due_review_count(self, student_id, file_name=None):
        with self.engine.begin() as conn:
            today = datetime.now().strftime('%Y-%m-%d')
            if file_name:
                row = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) AS total
                    FROM review_schedule rs
                    JOIN words w ON w.id = rs.word_id
                    WHERE rs.student_id = :student_id
                      AND rs.status = 'pending'
                      AND rs.review_date <= :today
                      AND w.source_file = :source_file
                    """,
                    ),
                    {'student_id': student_id, 'source_file': file_name, 'today': today},
                ).mappings().first()
            else:
                row = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) AS total
                    FROM review_schedule
                    WHERE student_id = :student_id
                      AND status = 'pending'
                      AND review_date <= :today
                    """,
                    ),
                    {'student_id': student_id, 'today': today},
                ).mappings().first()
        return row['total']

    def get_word_ids_by_terms(self, selected_file, terms):
        if not terms:
            return []
        params = {'source_file': selected_file}
        term_keys = []
        for idx, term in enumerate(terms):
            key = f'term_{idx}'
            term_keys.append(f':{key}')
            params[key] = term

        sql = f"SELECT id, term FROM words WHERE source_file = :source_file AND term IN ({', '.join(term_keys)})"
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [row['id'] for row in rows]

    def upsert_progress(self, conn, student_id, word_id, status, next_review_date=None, mastery_delta=0):
        existing = conn.execute(
            text("SELECT mastery_level FROM student_word_progress WHERE student_id = :student_id AND word_id = :word_id"),
            {'student_id': student_id, 'word_id': word_id},
        ).mappings().first()
        mastery_level = max(0, (existing['mastery_level'] if existing else 0) + mastery_delta)
        payload = {
            'student_id': student_id,
            'word_id': word_id,
            'mastery_level': mastery_level,
            'status': status,
            'last_action': datetime.now().isoformat(),
            'next_review_date': next_review_date,
        }
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE student_word_progress
                    SET mastery_level = :mastery_level,
                        status = :status,
                        last_action = :last_action,
                        next_review_date = :next_review_date
                    WHERE student_id = :student_id AND word_id = :word_id
                    """
                ),
                payload,
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO student_word_progress(student_id, word_id, mastery_level, status, last_action, next_review_date)
                    VALUES (:student_id, :word_id, :mastery_level, :status, :last_action, :next_review_date)
                    """
                ),
                payload,
            )

    def mark_words_known(self, student_id, selected_file, terms):
        word_ids = self.get_word_ids_by_terms(selected_file, terms)
        if not word_ids:
            return
        with self.engine.begin() as conn:
            now = datetime.now().isoformat()
            for word_id in word_ids:
                conn.execute(
                    text(
                        "INSERT INTO learning_actions(student_id, word_id, action_type, action_time) "
                        "VALUES (:student_id, :word_id, 'known', :action_time)"
                    ),
                    {'student_id': student_id, 'word_id': word_id, 'action_time': now},
                )
                conn.execute(
                    text(
                        "UPDATE review_schedule SET status = 'done' "
                        "WHERE student_id = :student_id AND word_id = :word_id AND status = 'pending'"
                    ),
                    {'student_id': student_id, 'word_id': word_id},
                )
                self.upsert_progress(conn, student_id, word_id, status="known", next_review_date=None, mastery_delta=1)

    def schedule_review_words(self, student_id, selected_file, terms):
        word_ids = self.get_word_ids_by_terms(selected_file, terms)
        if not word_ids:
            return
        with self.engine.begin() as conn:
            now = datetime.now().isoformat()
            for word_id in word_ids:
                if self.is_postgres:
                    action_id = conn.execute(
                        text(
                            "INSERT INTO learning_actions(student_id, word_id, action_type, action_time) "
                            "VALUES (:student_id, :word_id, 'unknown', :action_time) RETURNING id"
                        ),
                        {'student_id': student_id, 'word_id': word_id, 'action_time': now},
                    ).scalar_one()
                else:
                    conn.execute(
                        text(
                            "INSERT INTO learning_actions(student_id, word_id, action_type, action_time) "
                            "VALUES (:student_id, :word_id, 'unknown', :action_time)"
                        ),
                        {'student_id': student_id, 'word_id': word_id, 'action_time': now},
                    )
                    action_id = conn.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()['id']

                first_date = (datetime.now() + timedelta(days=REVIEW_INTERVALS[0])).strftime("%Y-%m-%d")
                self.upsert_progress(
                    conn,
                    student_id,
                    word_id,
                    status="learning",
                    next_review_date=first_date,
                    mastery_delta=-1,
                )
                for day in REVIEW_INTERVALS:
                    review_date = (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d")
                    exists = conn.execute(
                        text(
                            "SELECT id FROM review_schedule "
                            "WHERE student_id = :student_id AND word_id = :word_id AND review_date = :review_date"
                        ),
                        {'student_id': student_id, 'word_id': word_id, 'review_date': review_date},
                    ).first()
                    if not exists:
                        conn.execute(
                            text(
                                """
                                INSERT INTO review_schedule(student_id, word_id, review_date, status, created_from_action_id)
                                VALUES (:student_id, :word_id, :review_date, 'pending', :created_from_action_id)
                                """
                            ),
                            {
                                'student_id': student_id,
                                'word_id': word_id,
                                'review_date': review_date,
                                'created_from_action_id': action_id,
                            },
                        )


txt_reader = TxtReader()
txt_reader.seed_default_users()


def current_user():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'student_id': session.get('student_id'),
        'student_name': session.get('student_name'),
    }


def login_required(roles=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user['id']:
                return redirect(url_for('login_student'))
            if roles and user['role'] not in roles:
                return redirect(url_for('index'))
            return func(*args, **kwargs)

        return wrapper

    return decorator


@app.route('/login/teacher', methods=['GET', 'POST'])
def login_teacher():
    teacher_username = os.getenv('TEACHER_USERNAME', 'teacher').strip() or 'teacher'
    teacher_password = os.getenv('TEACHER_PASSWORD', 'teacher123')
    error_message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = txt_reader.authenticate(username, password, role='teacher')
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['student_id'] = None
            session['student_name'] = None
            return redirect(url_for('index'))
        error_message = '账号或密码错误'

    return render_template(
        'login_teacher.html',
        error_message=error_message,
        teacher_username=teacher_username,
        teacher_password=teacher_password,
    )


@app.route('/login/student', methods=['GET', 'POST'])
def login_student():
    error_message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = txt_reader.authenticate(username, password, role='student')
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['student_id'] = user['student_id']
            session['student_name'] = user['student_name']
            return redirect(url_for('index'))
        error_message = '账号或密码错误'

    return render_template(
        'login_student.html',
        error_message=error_message,
        student_accounts=txt_reader.get_student_accounts(),
    )


@app.route('/teacher/students', methods=['GET', 'POST'])
@login_required(roles=['teacher'])
def teacher_students():
    error_message = None
    success_message = None

    if request.method == 'POST':
        action = request.form.get('action', 'create').strip()
        if action == 'create':
            student_name = request.form.get('student_name', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            source_files = request.form.getlist('source_files')

            if not student_name:
                error_message = '学生名称不能为空'
            else:
                ok, message = txt_reader.create_student_account(student_name, username, password, source_files)
                if ok:
                    success_message = message
                else:
                    error_message = message

        if action == 'update_files':
            username = request.form.get('username', '').strip()
            source_files = request.form.getlist('source_files')
            with txt_reader.engine.begin() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT student_id
                        FROM users
                        WHERE username = :username
                          AND role = 'student'
                          AND is_active = 1
                        """
                    ),
                    {'username': username},
                ).mappings().first()
            if row:
                txt_reader.set_student_source_files(row['student_id'], source_files)
                success_message = f'已更新 {username} 的词库权限'
            else:
                error_message = '未找到学生账号'

    return render_template(
        'teacher_students.html',
        students=txt_reader.get_student_accounts(),
        source_files=txt_reader.file_choices,
        error_message=error_message,
        success_message=success_message,
    )


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login_student'))


@app.route('/', methods=['GET', 'POST'])
@login_required(roles=['teacher', 'student'])
def index():
    user = current_user()
    selected_student = request.values.get('student_name', user['student_name'] or '英语')
    learning_mode = request.values.get('learning_mode', 'new')

    if user['role'] == 'student':
        selected_student = user['student_name']
        learning_mode = 'review'

    if learning_mode not in ['new', 'review']:
        learning_mode = 'new'

    student_id, selected_student = txt_reader.ensure_student(selected_student)
    available_files = txt_reader.get_allowed_files_for_student(student_id)

    selected_file = request.values.get('file_name', '')
    if selected_file not in available_files:
        selected_file = available_files[0] if available_files else ''

    if not selected_file:
        return render_template(
            'index.html',
            words=[],
            user=user,
            selected_file='',
            selected_student=selected_student,
            students=txt_reader.get_students(),
            files=[],
            learning_mode=learning_mode,
            due_review_count=0,
            no_file_access_message='该学生未分配任何词库源，请老师先到“学生管理”中分配。',
        )

    if request.method == 'GET':
        words = txt_reader.get_words_for_mode(student_id, selected_file, learning_mode)
        return render_template(
            'index.html',
            words=words,
            user=user,
            selected_file=selected_file,
            selected_student=selected_student,
            students=txt_reader.get_students(),
            files=available_files,
            learning_mode=learning_mode,
            due_review_count=txt_reader.due_review_count(student_id, selected_file),
        )
    elif request.method == 'POST':
        action = request.form['action']
        if user['role'] == 'student' and action == 'learn':
            action = 'mark_known'

        if action == 'check':
            pass
        elif action == 'learn':
            selected_check_words = request.form.getlist('check_word')
            txt_reader.mark_words_known(student_id, selected_file, selected_check_words)
            selected_unknown_words = request.form.getlist('selected_words')
            if selected_unknown_words:
                selected_unknown_words = json.loads(selected_unknown_words[0])
                review_words = [word_dict['单词'] for word_dict in selected_unknown_words]
                txt_reader.schedule_review_words(student_id, selected_file, review_words)
        elif action == 'mark_known':
            selected_check_words = request.form.getlist('check_word')
            txt_reader.mark_words_known(student_id, selected_file, selected_check_words)

        words = txt_reader.get_words_for_mode(student_id, selected_file, learning_mode)
        return render_template(
            'index.html',
            words=words,
            user=user,
            selected_file=selected_file,
            selected_student=selected_student,
            students=txt_reader.get_students(),
            files=available_files,
            learning_mode=learning_mode,
            due_review_count=txt_reader.due_review_count(student_id, selected_file),
        )

    words = txt_reader.get_words_for_mode(student_id, selected_file, learning_mode)
    return render_template(
        'index.html',
        words=words,
        user=user,
        selected_file=selected_file,
        selected_student=selected_student,
        students=txt_reader.get_students(),
        files=available_files,
        learning_mode=learning_mode,
        due_review_count=txt_reader.due_review_count(student_id, selected_file),
    )


@app.route('/new/start', methods=['GET', 'POST'])
@login_required(roles=['teacher'])
def new_start():
    page_size = 10
    decision_state_key = 'new_start_decisions'
    context_state_key = 'new_start_context'

    user = current_user()
    selected_student = request.values.get('student_name', '英语')
    student_id, selected_student = txt_reader.ensure_student(selected_student)
    allowed_files = txt_reader.get_allowed_files_for_student(student_id)

    selected_file = request.values.get('file_name', '')
    if selected_file not in allowed_files:
        selected_file = allowed_files[0] if allowed_files else ''

    words = txt_reader.get_words_from_file(selected_file) if selected_file else []
    total_words = len(words)
    total_pages = max(1, math.ceil(total_words / page_size))

    try:
        page = int(request.values.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, total_pages))

    current_context = {'student_name': selected_student, 'file_name': selected_file}
    if session.get(context_state_key) != current_context:
        session[context_state_key] = current_context
        session[decision_state_key] = {}

    decisions_state = session.get(decision_state_key, {})

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    words_page = words[start_idx:end_idx]

    if request.method == 'POST':
        student_id, selected_student = txt_reader.ensure_student(request.form.get('student_name', selected_student))
        selected_file = request.form.get('file_name', selected_file)
        allowed_files = txt_reader.get_allowed_files_for_student(student_id)
        if selected_file not in allowed_files:
            selected_file = allowed_files[0] if allowed_files else ''

        current_context = {'student_name': selected_student, 'file_name': selected_file}
        if session.get(context_state_key) != current_context:
            session[context_state_key] = current_context
            session[decision_state_key] = {}

        if not selected_file:
            return redirect(url_for('new_start', student_name=selected_student))

        words = txt_reader.get_words_from_file(selected_file)
        total_words = len(words)
        total_pages = max(1, math.ceil(total_words / page_size))
        try:
            page = int(request.form.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        words_page = words[start_idx:end_idx]

        decisions_state = session.get(decision_state_key, {})
        for word in words_page:
            decision = request.form.get(f"decision_{word['id']}")
            if decision in ['known', 'unknown']:
                decisions_state[str(word['id'])] = decision
            else:
                decisions_state.pop(str(word['id']), None)
        session[decision_state_key] = decisions_state

        intent = request.form.get('intent', 'start')
        if intent == 'next' and page < total_pages:
            return redirect(url_for('new_start', student_name=selected_student, file_name=selected_file, page=page + 1))
        if intent == 'prev' and page > 1:
            return redirect(url_for('new_start', student_name=selected_student, file_name=selected_file, page=page - 1))

        known_terms = []
        unknown_decisions = []
        for word in words:
            decision = decisions_state.get(str(word['id']))
            if decision == 'known':
                known_terms.append(word['term'])
            elif decision == 'unknown':
                unknown_decisions.append((word['id'], 'unknown'))

        if not known_terms and not unknown_decisions:
            return redirect(url_for('new_start', student_name=selected_student, file_name=selected_file, page=page))

        if known_terms:
            txt_reader.mark_words_known(student_id, selected_file, known_terms)

        session.pop(decision_state_key, None)
        session.pop(context_state_key, None)
        if unknown_decisions:
            session_id = txt_reader.create_learning_session(user['id'], student_id, selected_file, unknown_decisions)
            return redirect(url_for('new_train', session_id=session_id, group_no=1))

        return render_template(
            'new_result.html',
            user=user,
            result={
                'known_count': len(known_terms),
                'newly_learned_count': 0,
                'student_name': selected_student,
                'source_file': selected_file,
            },
            session_id=None,
        )

    for word in words_page:
        word['decision'] = decisions_state.get(str(word['id']), '')

    return render_template(
        'new_start.html',
        user=user,
        students=txt_reader.get_students(),
        selected_student=selected_student,
        selected_file=selected_file,
        files=allowed_files,
        words=words_page,
        page=page,
        total_pages=total_pages,
        total_words=total_words,
        page_size=page_size,
        no_file_access_message='' if allowed_files else '该学生未分配词库源，请先在学生管理页分配。',
    )


@app.route('/new/train/<int:session_id>/<int:group_no>', methods=['GET', 'POST'])
@login_required(roles=['teacher'])
def new_train(session_id, group_no):
    user = current_user()
    session_info = txt_reader.get_learning_session(session_id)
    if not session_info:
        return redirect(url_for('new_start'))

    group_words, total_groups, total_unknown = txt_reader.get_training_group(session_id, group_no)

    if total_unknown == 0:
        return redirect(url_for('new_review', session_id=session_id))
    if group_no > total_groups:
        return redirect(url_for('new_review', session_id=session_id))

    if request.method == 'POST':
        training_completed = request.form.get('training_completed', '0') == '1'
        if not training_completed:
            return render_template(
                'new_train.html',
                user=user,
                session_info=session_info,
                group_words=group_words,
                group_no=group_no,
                total_groups=total_groups,
                train_warning='请先按路线顺序完成本组学习，再点击主按钮进入下一步。',
            )

        if group_no >= total_groups:
            return redirect(url_for('new_review', session_id=session_id))
        return redirect(url_for('new_train', session_id=session_id, group_no=group_no + 1))

    return render_template(
        'new_train.html',
        user=user,
        session_info=session_info,
        group_words=group_words,
        group_no=group_no,
        total_groups=total_groups,
        train_warning=None,
    )


@app.route('/new/review/<int:session_id>', methods=['GET', 'POST'])
@login_required(roles=['teacher'])
def new_review(session_id):
    user = current_user()
    session_info = txt_reader.get_learning_session(session_id)
    if not session_info:
        return redirect(url_for('new_start'))

    all_words = txt_reader.get_session_words(session_id)

    if request.method == 'POST':
        learned_word_ids = request.form.getlist('learned_word_id')
        result = txt_reader.finalize_learning_session(session_id, learned_word_ids)
        return render_template(
            'new_result.html',
            user=user,
            result=result,
            session_id=session_id,
        )

    return render_template(
        'new_review.html',
        user=user,
        session_info=session_info,
        words=all_words,
    )


if __name__ == '__main__':
    app.run(debug=True)
