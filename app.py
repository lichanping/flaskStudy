import json
import os
import re
from flask import Flask, render_template, request, send_file

app = Flask(__name__)
# Configure Flask to serve static files from the 'static' directory
app.static_folder = 'static'


def get_sub_folder_path(folder_name='data'):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_directory, folder_name)


class TxtReader:
    def __init__(self):
        self.data_folder = get_sub_folder_path('data')
        self.sound_folder = get_sub_folder_path('sounds')

    def read_words_from_txt(self, file_name, limit=50):
        file_path = os.path.join(self.data_folder, file_name)
        words = []
        pattern = re.compile(r'([a-zA-Z\'\s\-\.\/]+)\s*(.*)')
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
        # Construct the path to the selected file
        file_path = os.path.join(self.data_folder, selected_file)

        # Construct the new file name
        new_file_name = selected_file.replace('.txt', '_finish.txt')
        new_file_path = os.path.join(self.data_folder, new_file_name)

        # Move selected words to the new file
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read the existing content
            existing_content = file.readlines()

        with open(new_file_path, 'a', encoding='utf-8') as new_file:
            # Write selected words to the new file
            for word in selected_words:
                new_file.write(word+'\n')

        # Update the original file by removing selected words
        pattern = re.compile(r'([a-zA-Z\'\s\-\.\/]+)\s*(.*)')
        with open(file_path, 'w', encoding='utf-8') as file:
            # Write back the remaining content excluding selected words
            for line in existing_content:
                match = pattern.match(line.strip())
                if match:
                    english_word, translation = match.groups()
                    if english_word.strip() not in selected_words:
                        file.write(line)
                else:
                    print(f"Invalid format in line: {line.strip()}")

        return new_file_name


txt_reader = TxtReader()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        file_name = request.args.get('file_name', 'words.txt')  # Default to 'words.txt' if no file selected
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
            selected_check_words = json.loads(selected_check_words)
            return render_template('index.html', words=selected_check_words)
        elif action == 'resist_forgetting':
            selected_check_words = request.form.getlist('check_word')



if __name__ == '__main__':
    app.run(debug=True)
