import asyncio
import os
import random
import re
import time
from datetime import datetime, date
from datetime import timedelta
from os.path import dirname, abspath

import edge_tts
import pandas as pd
from edge_tts import VoicesManager
from ptest.decorator import TestClass, Test


def get_sub_folder_path(sub_dir_name='data'):
    """
    Create the destination folder if not exists.
    :param sub_dir_name: default is 'data'
    :return: sub folder's absolute path.
    """
    current_dir_name = dirname(__file__)
    abs_path = abspath(current_dir_name)
    sub_folder = os.sep.join([abs_path, sub_dir_name])
    return sub_folder


class TxtToXLSX:
    def __init__(self):
        self.data_folder = get_sub_folder_path()
        self.sound_folder = get_sub_folder_path('static/sounds')
        self.review_folder = get_sub_folder_path('data/review')
        self.ori_file = None
        self.generate_file = None
        self.missing_words = []

    def remove_old_files(self):
        review_folder = self.review_folder
        # Get today's date
        today = date.today()

        # Iterate through all files in the review folder
        for filename in os.listdir(review_folder):
            # Check if the file has a .txt extension and matches the date format
            if filename.endswith('.txt'):
                # Extract the date part from the filename
                try:
                    file_date = datetime.strptime(filename[:-4], '%Y-%m-%d').date()
                    # Check if the file date is older than today's date
                    if file_date < today:
                        file_path = os.path.join(review_folder, filename)
                        os.remove(file_path)
                        print(f"Removed file: {file_path}")
                except ValueError:
                    # Skip files that don't match the date format
                    continue

    def convert(self, file_name):
        extracted_data = self.read_text(file_name)
        # self.create_excel(extracted_data)

    def remove_duplicates_or_merge_translations(self, file_name):
        """
        Remove duplicate English words or merge their translations directly from the original text file.
        """
        file_path = os.path.join(self.data_folder, file_name)
        english_words = {}  # Dictionary to store English words and their translations
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = re.match(r'([a-zA-Zéèêàâôûç\'\s\-\.\/]+)\s*(.*)', line.strip())
                if match:
                    english_word, translation = match.groups()
                    translation = re.sub(r'\s+', '', translation)
                    english_word = english_word.strip()

                    if english_word.endswith(('adj.', 'adv.', 'n.', 'v.', 'phr.', 'vt.', 'prep.', 'vi.', 'det.',
                                              'pron.', 'conj.', 'int.', 'aux.', 'auxv.', 'num.')):
                        # If it does, move the part of speech to the translation
                        pos = english_word.split()[-1]  # Get the last part of the word as part of speech
                        english_word = english_word[
                                       :-len(pos)].strip()  # Remove the part of speech from the English word
                        translation = f"({pos}) {translation.strip()}"

                    # Replace "sb" with "somebody" and "sth" with "something" only in the English words part
                    english_word = english_word.replace("sb", "somebody").replace("sth", "something")
                    english_word = re.sub(r'sw(?!\w)', 'somewhere', english_word)
                    translation = translation.strip()
                    if english_word not in english_words:
                        # If the English word is encountered for the first time, initialize its translations as a list
                        english_words[english_word] = [translation]
                    else:
                        # If the English word already exists, append the new translation to its list of translations
                        existing_translation = english_words[english_word]
                        if translation not in existing_translation:
                            existing_translation.append(translation)

        # Write the unique English words and their translations back to the original file
        with open(file_path, 'w', encoding='utf-8') as file:
            for english_word, translations in english_words.items():
                # Merge translations into a single string, separated by semicolons
                merged_translations = ';'.join(translations)
                file.write(f"{english_word}\t{merged_translations}\n")

    def read_text(self, file_name):
        """
        Generate MissingSound.txt if audio not exists
        :param file_name:
        :return:
        """
        self.ori_file = file_name
        self.generate_file = os.path.join(self.data_folder, file_name.split('.')[0] + "_抗遗忘单词.xlsx")
        missing_sound_file = os.path.join(self.data_folder, "MissingSound.txt")  # Path to store missing sound words
        file_path = os.path.join(self.data_folder, file_name)
        data = []
        missing_words = []  # List to store missing sound words
        pattern = re.compile(r'([a-zA-Zéèêàâôûç\'\s\-\.\/]+)\s*(.*)')
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = pattern.match(line.strip())
                if match:
                    english_word, translation = match.groups()
                    english_word = english_word.strip()
                    # Replace "sb" with "somebody" and "sth" with "something" only in the English words part
                    english_word = english_word.replace("sb", "somebody").replace("sth", "something")
                    translation = translation.strip()
                    media = os.path.join(self.sound_folder, f"{english_word.strip()}.mp3")
                    exist = os.path.exists(media)
                    # print(f"English: {english_word}, Translation: {translation}, Sound: {exist}")
                    data.append({"单词": english_word, "释意": translation, "音频": str(exist)})
                    if not exist:
                        self.missing_words.append(english_word.strip())
                else:
                    print(f"Invalid format in line: {line.strip()}")
        # Write missing words to MissingSound.txt
        with open(missing_sound_file, 'w', encoding='utf-8') as missing_file:
            missing_file.write("\n".join(self.missing_words))

        return data

    def create_excel(self, data):
        df = pd.DataFrame(data)
        df.insert(0, '序号', range(1, len(df) + 1))
        df.to_excel(self.generate_file, index=False)
        print(f"Excel file '{self.generate_file}' created successfully.")


class TextToSpeechConverter:
    def __init__(self, txt_to_xlsx):
        self.txt_to_xlsx = txt_to_xlsx

    async def convert_text_to_audio(self, file_name, repeat=2, max_items=None):
        extracted_data = self.txt_to_xlsx.read_text(file_name)

        if max_items is not None and 0 < max_items < len(extracted_data):
            extracted_data = random.sample(extracted_data, max_items)

        output_file = os.path.join(self.txt_to_xlsx.data_folder, file_name.split('.')[0] + ".mp3")

        voices = await VoicesManager.create()
        voice_names = [
            "Microsoft Server Speech Text to Speech Voice (en-US, AvaMultilingualNeural)",
            "Microsoft Server Speech Text to Speech Voice (en-US, EmmaMultilingualNeural)",
            "Microsoft Server Speech Text to Speech Voice (en-US, EmmaNeural)",
            "Microsoft Server Speech Text to Speech Voice (en-US, MichelleNeural)"
        ]
        english_voice = voice_names[-1]
        # english_voice = voices.find(Gender="Female", Language="en")
        # english_voice = random.choice(english_voice)["Name"]
        chinese_voice = voices.find(
            Language='zh'
            , Gender="Male"
            , Locale="zh-CN"
        )

        with open(output_file, "wb") as file:
            current_date = datetime.now().strftime('%Y-%m-%d')
            print(f"测验时间: ___{current_date}___, 考核项：___重点语言点___")
            for index, item in enumerate(extracted_data):
                english_word = item['单词']
                chinese_meaning = item['释意']
                # print(f"English: {english_word}, Translation: {chinese_meaning}")
                # print(f"{index + 1}: {english_word}, 翻译为_______")
                print(f"{index + 1}: _______, 翻译为 {chinese_meaning}")

                english_voice_name = english_voice
                chinese_voice_name = random.choice(chinese_voice)["Name"]

                # Repeat English audio twice
                for _ in range(repeat):
                    english_stream = edge_tts.Communicate(english_word, voice=english_voice_name).stream()
                    async for chunk in english_stream:
                        if chunk["type"] == "audio":
                            file.write(chunk["data"])

                chinese_stream = edge_tts.Communicate(chinese_meaning, voice=chinese_voice_name).stream()

                async for chunk in chinese_stream:
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])

        print(f"Audio file '{output_file}' created successfully.")


@TestClass(run_mode='singleline')
class GenerateTool:
    @Test()
    def simplify_words(self):
        # remove duplicate words
        tool = TxtToXLSX()
        tool.remove_old_files()
        tool.remove_duplicates_or_merge_translations('高考词汇（持续更新中）.txt')

    @Test()
    def calculate_missing_words(self):
        tool = TxtToXLSX()
        # generate missing sounds
        tool.convert('高考词汇（持续更新中）.txt')  # commented the create_excel due to uselessness.

    @Test()
    def french_words(self):
        tool = TxtToXLSX()
        tool.remove_duplicates_or_merge_translations('法语单词（持续更新中）.txt')
        tool.convert('法语单词（持续更新中）.txt')  # commented the create_excel due to uselessness.

    @Test()
    def import_forgotten(self):
        data_folder = get_sub_folder_path('data')
        import_file_path = os.path.join(data_folder, 'Import.txt')
        # 读取 Import.txt 中的新词
        new_words = []
        with open(import_file_path, 'r', encoding='utf-8') as import_file:
            for line in import_file:
                new_words.append(line.strip())

        review_folder_path = os.path.join(data_folder, 'review')
        review_dates = []

        for days in [0, 1, 2, 3, 5, 7, 9, 12, 14, 17, 21]:
            review_date = datetime.now() + timedelta(days=days)
            review_date_str = review_date.strftime('%Y-%m-%d')
            review_dates.append(review_date_str)

            review_file_path = os.path.join(review_folder_path, f"{review_date_str}.txt")

            if os.path.exists(review_file_path):
                # 读取已有文件的内容
                existing_words = []
                with open(review_file_path, 'r', encoding='utf-8') as existing_file:
                    existing_words = [line.strip() for line in existing_file.readlines()]
                # 将新词添加到已有文件内容的开头
                combined_words = new_words + existing_words

                # 重新写入文件
                with open(review_file_path, 'w', encoding='utf-8') as updated_file:
                    for word in combined_words:
                        updated_file.write(word + '\n')
            else:
                with open(review_file_path, 'w', encoding='utf-8') as new_file:
                    for word in new_words:
                        new_file.write(word + '\n')

    @Test()
    def generate_media_word_list(self):
        def en_and_cn(file, max_items):
            start_time = time.time()  # Record start time
            converter = TextToSpeechConverter(tool)
            asyncio.run(converter.convert_text_to_audio(file, max_items=max_items))
            end_time = time.time()  # Record end time
            elapsed_time = end_time - start_time  # Calculate elapsed time
            print(f"Time taken: {elapsed_time} seconds")

        tool = TxtToXLSX()
        en_and_cn('中考考纲词组.txt', max_items=3)
