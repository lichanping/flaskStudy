import json
import os
import re
from datetime import datetime, timedelta

from flask import Flask, render_template, request
from sqlalchemy import create_engine, text

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
        self.database_url = os.getenv('DATABASE_URL', '').strip()
        self.is_postgres = bool(self.database_url)
        self.engine = self.create_engine()
        self.file_choices = list(file_to_student_mapping.keys())
        self.init_db()
        self.seed_words_if_needed()
        self.seed_default_students()

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
