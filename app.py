import os
import re
from flask import Flask, render_template, request, jsonify

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
            for line in file:
                match = pattern.match(line.strip())
                if match:
                    english_word, translation = match.groups()
                    words.append({"单词": english_word.strip(), "释意": translation})
                else:
                    print(f"Invalid format in line: {line.strip()}")
                # Stop reading after reaching the limit
                if len(words) >= limit:
                    break
        return words


txt_reader = TxtReader()


@app.route('/', methods=['GET'])
def index():
    file_name = request.args.get('file_name', 'words.txt')  # Default to 'words.txt' if no file selected
    words = txt_reader.read_words_from_txt(file_name)
    return render_template('index.html', words=words)


@app.route('/refresh_word_list', methods=['GET'])
def refresh_word_list():
    selected_file = request.args.get('file_name', 'words.txt')
    words = txt_reader.read_words_from_txt(selected_file)
    return jsonify(words)


if __name__ == '__main__':
    app.run(debug=True)
