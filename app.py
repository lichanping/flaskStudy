import json
import os
import re
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, render_template, request

app = Flask(__name__)
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
        self.file_choices = list(file_to_student_mapping.keys())
        self.init_db()
        self.seed_words_if_needed()
        self.seed_default_students()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        os.makedirs(self.data_folder, exist_ok=True)
        with self.get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    term TEXT NOT NULL,
                    meaning TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_file, term)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    action_time TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(id),
                    FOREIGN KEY(word_id) REFERENCES words(id)
                )
                """
            )
            conn.execute(
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    def seed_default_students(self):
        default_students = sorted(set(file_to_student_mapping.values()))
        with self.get_conn() as conn:
            for student_name in default_students:
                conn.execute(
                    "INSERT OR IGNORE INTO students(name, created_at) VALUES (?, ?)",
                    (student_name, datetime.now().isoformat()),
                )

    def get_students(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT name FROM students ORDER BY name").fetchall()
        return [row["name"] for row in rows]

    def ensure_student(self, student_name):
        if not student_name:
            student_name = "英语"
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO students(name, created_at) VALUES (?, ?)",
                (student_name, datetime.now().isoformat()),
            )
            row = conn.execute("SELECT id FROM students WHERE name = ?", (student_name,)).fetchone()
        return row["id"], student_name

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
        with self.get_conn() as conn:
            count_row = conn.execute("SELECT COUNT(*) AS total FROM words").fetchone()
            if count_row["total"] > 0:
                return

            now = datetime.now().isoformat()
            for file_name in self.file_choices:
                for word in self.read_words_from_txt(file_name, limit=10**9):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO words(source_file, term, meaning, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (file_name, word["单词"], word["释意"], now),
                    )

    def get_words_for_mode(self, student_id, file_name, learning_mode="new", limit=DEFAULT_WORD_LIMIT):
        with self.get_conn() as conn:
            if learning_mode == "review":
                rows = conn.execute(
                    """
                    SELECT w.id, w.term, w.meaning
                    FROM review_schedule rs
                    JOIN words w ON w.id = rs.word_id
                    WHERE rs.student_id = ?
                      AND rs.status = 'pending'
                      AND rs.review_date <= DATE('now')
                      AND w.source_file = ?
                    ORDER BY rs.review_date, rs.id
                    LIMIT ?
                    """,
                    (student_id, file_name, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT w.id, w.term, w.meaning
                    FROM words w
                    LEFT JOIN student_word_progress p
                      ON p.word_id = w.id AND p.student_id = ?
                    WHERE w.source_file = ?
                      AND (p.status IS NULL OR p.status != 'known')
                    ORDER BY w.id
                    LIMIT ?
                    """,
                    (student_id, file_name, limit),
                ).fetchall()

        words = []
        for idx, row in enumerate(rows, start=1):
            words.append({"索引": idx, "单词": row["term"], "释意": row["meaning"], "id": row["id"]})
        return words

    def due_review_count(self, student_id, file_name=None):
        with self.get_conn() as conn:
            if file_name:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM review_schedule rs
                    JOIN words w ON w.id = rs.word_id
                    WHERE rs.student_id = ?
                      AND rs.status = 'pending'
                      AND rs.review_date <= DATE('now')
                      AND w.source_file = ?
                    """,
                    (student_id, file_name),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM review_schedule
                    WHERE student_id = ?
                      AND status = 'pending'
                      AND review_date <= DATE('now')
                    """,
                    (student_id,),
                ).fetchone()
        return row["total"]

    def get_word_ids_by_terms(self, selected_file, terms):
        if not terms:
            return []
        placeholders = ",".join(["?"] * len(terms))
        with self.get_conn() as conn:
            rows = conn.execute(
                f"SELECT id, term FROM words WHERE source_file = ? AND term IN ({placeholders})",
                [selected_file] + terms,
            ).fetchall()
        return [row["id"] for row in rows]

    def upsert_progress(self, conn, student_id, word_id, status, next_review_date=None, mastery_delta=0):
        existing = conn.execute(
            "SELECT mastery_level FROM student_word_progress WHERE student_id = ? AND word_id = ?",
            (student_id, word_id),
        ).fetchone()
        mastery_level = max(0, (existing["mastery_level"] if existing else 0) + mastery_delta)
        conn.execute(
            """
            INSERT INTO student_word_progress(student_id, word_id, mastery_level, status, last_action, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, word_id)
            DO UPDATE SET
                mastery_level = excluded.mastery_level,
                status = excluded.status,
                last_action = excluded.last_action,
                next_review_date = excluded.next_review_date
            """,
            (
                student_id,
                word_id,
                mastery_level,
                status,
                datetime.now().isoformat(),
                next_review_date,
            ),
        )

    def mark_words_known(self, student_id, selected_file, terms):
        word_ids = self.get_word_ids_by_terms(selected_file, terms)
        if not word_ids:
            return
        with self.get_conn() as conn:
            now = datetime.now().isoformat()
            for word_id in word_ids:
                conn.execute(
                    "INSERT INTO learning_actions(student_id, word_id, action_type, action_time) VALUES (?, ?, 'known', ?)",
                    (student_id, word_id, now),
                )
                conn.execute(
                    "UPDATE review_schedule SET status = 'done' WHERE student_id = ? AND word_id = ? AND status = 'pending'",
                    (student_id, word_id),
                )
                self.upsert_progress(conn, student_id, word_id, status="known", next_review_date=None, mastery_delta=1)

    def schedule_review_words(self, student_id, selected_file, terms):
        word_ids = self.get_word_ids_by_terms(selected_file, terms)
        if not word_ids:
            return
        with self.get_conn() as conn:
            now = datetime.now().isoformat()
            for word_id in word_ids:
                action = conn.execute(
                    "INSERT INTO learning_actions(student_id, word_id, action_type, action_time) VALUES (?, ?, 'unknown', ?)",
                    (student_id, word_id, now),
                )
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
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO review_schedule(student_id, word_id, review_date, status, created_from_action_id)
                        VALUES (?, ?, ?, 'pending', ?)
                        """,
                        (student_id, word_id, review_date, action.lastrowid),
                    )


txt_reader = TxtReader()


@app.route('/', methods=['GET', 'POST'])
def index():
    available_files = txt_reader.file_choices
    selected_file = request.values.get('file_name', '高考词汇.txt')
    if selected_file not in available_files:
        selected_file = '高考词汇.txt'

    selected_student = request.values.get('student_name', file_to_student_mapping.get(selected_file, '英语'))
    learning_mode = request.values.get('learning_mode', 'new')
    if learning_mode not in ['new', 'review']:
        learning_mode = 'new'

    student_id, selected_student = txt_reader.ensure_student(selected_student)

    if request.method == 'GET':
        words = txt_reader.get_words_for_mode(student_id, selected_file, learning_mode)
        return render_template(
            'index.html',
            words=words,
            selected_file=selected_file,
            selected_student=selected_student,
            students=txt_reader.get_students(),
            learning_mode=learning_mode,
            due_review_count=txt_reader.due_review_count(student_id, selected_file),
        )
    elif request.method == 'POST':
        action = request.form['action']
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
            selected_file=selected_file,
            selected_student=selected_student,
            students=txt_reader.get_students(),
            learning_mode=learning_mode,
            due_review_count=txt_reader.due_review_count(student_id, selected_file),
        )

    words = txt_reader.get_words_for_mode(student_id, selected_file, learning_mode)
    return render_template(
        'index.html',
        words=words,
        selected_file=selected_file,
        selected_student=selected_student,
        students=txt_reader.get_students(),
        learning_mode=learning_mode,
        due_review_count=txt_reader.due_review_count(student_id, selected_file),
    )


if __name__ == '__main__':
    app.run(debug=True)
