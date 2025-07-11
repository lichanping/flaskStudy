import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta
from math import ceil

from flask import Flask, render_template, request, send_file

app = Flask(__name__)
# Configure Flask to serve static files from the 'static' directory
app.static_folder = 'static'
DEFAULT_WORD_LIMIT = 50

# Mapping of word list files to student folders
file_to_student_mapping = {
    '高考词汇.txt': '英语',
    '雅思基础词汇.txt': '英语',
    '法语单词.txt': '法语',
    '你好法语.txt': '法语',
    '法语妈妈.txt': '妈妈',
    '中考考纲词组.txt': '中考考纲学生',
    '中考词汇.txt': '中考学生'
}


def get_sub_folder_path(folder_name='data'):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_directory, folder_name)


class TxtReader:
    def __init__(self):
        self.data_folder = get_sub_folder_path('data')
        self.base_review_folder = os.path.join(self.data_folder, 'review')

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

    def move_words_to_new_file(self, selected_file, selected_words):
        # Construct the paths to the files
        file_path = os.path.join(self.data_folder, selected_file)
        new_file_name = selected_file.replace('.txt', '_finish.txt')
        new_file_path = os.path.join(self.data_folder, new_file_name)

        # Count the occurrences of each selected word
        selected_word_counts = Counter(selected_words)
        moved_word_counts = Counter()  # Track how many times each word has been moved
        remaining_lines = []  # Lines that will stay in the original file

        with open(file_path, 'r', encoding='utf-8') as file, \
                open(new_file_path, 'a', encoding='utf-8') as new_file:
            for line in file:
                # Match each line with the expected pattern
                word_match = re.match(r'([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s–\.\/\?\？，,’0-9-]+)\s*(.*)', line.strip())
                if word_match:
                    english_word, translation = word_match.groups()
                    stripped_word = english_word.strip()

                    # Check if the word is selected and the move count hasn't exceeded the allowed count
                    if stripped_word in selected_word_counts and \
                            moved_word_counts[stripped_word] < selected_word_counts[stripped_word]:
                        new_file.write(line.strip() + '\n')
                        moved_word_counts[stripped_word] += 1  # Increment moved count
                    else:
                        remaining_lines.append(line)  # Keep the line in the original file
                else:
                    # If no match, keep the line in the original file
                    remaining_lines.append(line)

        # Update the original file with the remaining lines
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(remaining_lines)

        return new_file_name

    def add_words_to_review_files(self, selected_file, selected_words):
        if not selected_words:
            return None

        # Determine the student folder based on the selected file
        student_folder = file_to_student_mapping.get(selected_file, '英语')
        review_folder_for_student = os.path.join(self.base_review_folder, student_folder)
        translations = {}
        with open(os.path.join(self.data_folder, selected_file), 'r', encoding='utf-8') as file:
            for line in file:
                word_match = re.match(r'([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s–\.\/\?\？，,’0-9-]+)\s*(.*)', line.strip())
                if word_match:
                    english_word, translation = word_match.groups()
                    translations[english_word.strip()] = translation.strip()

        os.makedirs(review_folder_for_student, exist_ok=True)
        review_dates = []

        for days in [0, 1, 2, 3, 5, 7, 9, 12, 14, 17, 21]:
            review_date = datetime.now() + timedelta(days=days)
            review_date_str = review_date.strftime('%Y-%m-%d')
            review_dates.append(review_date_str)

            review_file_path = os.path.join(review_folder_for_student, f"{review_date_str}.txt")

            content = []
            for word in selected_words:
                clean_word = word.strip()  # Remove any whitespace around the word

                if clean_word in translations:
                    content.append(f"{clean_word}\t{translations[word]}")
                else:
                    raise ValueError(f"Translation not found for word: {clean_word}")

            content_to_write = '\n'.join(content)
            # Check if review file exists
            if os.path.exists(review_file_path):
                # Read existing content
                with open(review_file_path, 'r', encoding='utf-8') as review_file:
                    existing_content = review_file.read()
                # Combine existing content and new content
                content_to_write = content_to_write + '\n' + existing_content

            with open(review_file_path, 'w', encoding='utf-8') as review_file:
                review_file.write(content_to_write)

        print(f'Words scheduled for review on {review_dates}')
        return review_dates


txt_reader = TxtReader()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        file_name = request.args.get('file_name', '高考词汇.txt')  # Default to 'words.txt' if no file selected
        words = txt_reader.read_words_from_txt(file_name)
        return render_template('index.html', words=words)
    elif request.method == 'POST':
        action = request.form['action']
        if action == 'check':
            selected_file = request.form.get('selected_file', 'words.txt')  # Default to 'words.txt' if no file selected
            words = txt_reader.read_words_from_txt(selected_file)
            return render_template('index.html', words=words)
        elif action == 'learn':
            selected_file = request.form['file_name']
            selected_check_words = request.form.getlist('check_word')
            new_file_name = txt_reader.move_words_to_new_file(selected_file, selected_check_words)
            selected_check_words = request.form.getlist('selected_words')[0]
            selected_check_words = json.loads(selected_check_words)  # 选择x的word的list:
            review_words = [word_dict['单词'] for word_dict in selected_check_words]
            review_dates = txt_reader.add_words_to_review_files(selected_file, review_words)
            new_file_name = txt_reader.move_words_to_new_file(selected_file, review_words)
            words = txt_reader.read_words_from_txt(selected_file)
            return render_template('index.html', words=words)
        elif action == 'mark_known':
            selected_file = request.form['file_name']
            selected_check_words = request.form.getlist('check_word')
            # 只移动 ✓ 单词，不调度复习
            txt_reader.move_words_to_new_file(selected_file, selected_check_words)
            # Round up to the nearest multiple of 5
            remaining_limit = max(0, DEFAULT_WORD_LIMIT - len(selected_check_words))
            remaining_limit = ceil(remaining_limit / 5) * 5
            words = txt_reader.read_words_from_txt(selected_file, limit=remaining_limit)
            return render_template('index.html', words=words)
        return None
    return None


if __name__ == '__main__':
    app.run(debug=True)
