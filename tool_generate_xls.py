import asyncio
import os
import random
import re
import sys
import time
from datetime import datetime, date
from datetime import timedelta
from os.path import dirname, abspath

import edge_tts
import pandas as pd
import unicodedata
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


class FrenchTTSProcessor:
    def __init__(self):
        # Path to the text file under user_data directory
        self.text_file_path = os.path.join(get_sub_folder_path(), 'MissingSound.txt')
        self.sound_folder = get_sub_folder_path('static/sounds')
        self.TEXT_LIST = self.read_texts_from_file(self.text_file_path)

        if not self.TEXT_LIST:
            print("The text list is empty. Please provide texts in MissingSound.txt.")
            sys.exit()

    def read_texts_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read each line and remove leading/trailing whitespace
            texts = [line.strip() for line in file.readlines() if line.strip()]
        return texts

    # Async function to process a batch of texts and convert them to speech
    async def process_text_batch(self, texts, use_michelle=False):
        for text in texts:
            # Create output file path for each text
            output_file = os.path.join(self.sound_folder, f"{text}.mp3")

            # Create VoicesManager instance
            voices = await VoicesManager.create()

            if use_michelle:
                # Choose voice: specific Michelle voice
                name = "Microsoft Server Speech Text to Speech Voice (en-US, MichelleNeural)"
                communicate = edge_tts.Communicate(text, name)
                await communicate.save(output_file)
            else:
                excluded_voices = [
                    'Microsoft Server Speech Text to Speech Voice (fr-FR, EloiseNeural)',
                    'Microsoft Server Speech Text to Speech Voice (fr-FR, VivienneMultilingualNeural)',
                    # 'Microsoft Server Speech Text to Speech Voice (fr-FR, HenriNeural)',
                    'Microsoft Server Speech Text to Speech Voice (fr-FR, RemyMultilingualNeural)'
                ]
                # Choose voice from the voice library
                all_voices = voices.find(Language="fr", Locale="fr-FR")  # For French voices
                # Filter out the excluded voices
                available_voices = [voice for voice in all_voices if voice["Name"] not in excluded_voices]
                selected_voice = random.choice(available_voices)["Name"]
                print(f"Processing text: '{text}' with voice: '{selected_voice}'")
                # Use Edge TTS API to convert text to speech and save as MP3 file
                communicate = edge_tts.Communicate(text, selected_voice, rate="-10%")
                await communicate.save(output_file)

    # Main function to process the entire TEXT_LIST in batches
    async def process_all_texts(self):
        start_time = time.time()  # Record start time
        batch_size = 10  # Define the batch size
        # Split the TEXT_LIST into batches
        batches = [self.TEXT_LIST[i:i + batch_size] for i in range(0, len(self.TEXT_LIST), batch_size)]

        # Process each batch sequentially
        for batch in batches:
            await self.process_text_batch(batch)

        end_time = time.time()  # Record end time
        elapsed_time = end_time - start_time  # Calculate elapsed time
        print(f"Total elapsed time for processing {len(self.TEXT_LIST)} texts: {elapsed_time:.2f} seconds")
        print(f"Average time per text: {elapsed_time / len(self.TEXT_LIST):.2f} seconds")


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
        for root, dirs, files in os.walk(review_folder):
            for filename in files:
                # Check if the file has a .txt extension and matches the date format
                if filename.endswith('.txt'):
                    # Extract the date part from the filename
                    try:
                        file_date = datetime.strptime(filename[:-4], '%Y-%m-%d').date()
                        # Check if the file date is older than today's date
                        if file_date < today:
                            file_path = os.path.join(root, filename)
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
        Normalize ligatures like ﬂ -> fl and ﬁ -> fi in the English part.
        """
        file_path = os.path.join(self.data_folder, file_name)
        english_words = {}  # Dictionary to store unique English words and their translations
        duplicates = {}  # Dictionary to store duplicate words with multiple translations
        previous_word = None

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                # Normalize the line to replace ligatures and other Unicode anomalies
                line = unicodedata.normalize('NFKC', line)  # Decompose and recompose Unicode

                # Replace specific ligatures
                line = line.replace('ﬂ', 'fl').replace('ﬁ', 'fi')

                match = re.match(r'([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s\-\.\/\?\？，,0-9]+)\s*(.*)', line)
                if match:
                    english_word, translation = match.groups()
                    english_word = english_word.strip()
                    translation = translation.strip()

                    # Handle part of speech
                    pos_match = re.search(
                        r'(adj\.|adv\.|n\.|v\.|phr\.|vt\.|prep\.|vi\.|det\.|pron\.|conj\.|int\.|aux\.|auxv\.|num\.|abbr\.|excl\.|link-v\.)$',
                        english_word)
                    if pos_match:
                        pos = pos_match.group()
                        english_word = english_word[: -len(pos)].strip()
                        translation = f"({pos}) {translation}"

                    # Replace abbreviations
                    english_word = re.sub(r'\bsb\b', 'somebody', english_word)
                    english_word = re.sub(r'\bsth\b', 'something', english_word)
                    english_word = re.sub(r'\bsw\b', 'somewhere', english_word)

                    if not english_word:  # Handle cases where `english_word` is empty
                        if previous_word:  # Append to the previous word's translation
                            if previous_word in english_words:
                                english_words[previous_word] += f" {translation}"
                            elif previous_word in duplicates:
                                duplicates[previous_word][-1] += f" {translation}"  # Fixed for lists
                        continue  # Skip to the next line

                    if english_word in duplicates:
                        duplicates[english_word].append(translation)  # Changed to `append` for lists
                    elif english_word in english_words:
                        # Move to duplicates
                        duplicates[english_word] = [english_words.pop(english_word), translation]  # Use list here
                    else:
                        # Add new word
                        english_words[english_word] = translation

                    previous_word = english_word
                else:
                    # Continuation of the previous line
                    if previous_word and previous_word in english_words:
                        english_words[previous_word] += f" {line}"
                    elif previous_word and previous_word in duplicates:
                        duplicates[previous_word][-1] += f" {line}"  # Fixed for lists

        # Write the cleaned data back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            for english_word, translation in english_words.items():
                file.write(f"{english_word}\t{translation}\n")
            for english_word, translations in duplicates.items():
                file.write(f"{english_word}\t{'; '.join(translations)}\n")

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
        pattern = re.compile(r'([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s\-\.\/\?\？，,0-9]+)\s*(.*)')
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
        self.daily_folder = get_sub_folder_path('data/daily')

    async def convert_text_to_audio(self, file_name, language="fr", repeat=2, max_items=None):
        file_name = os.path.join(self.daily_folder, file_name)
        extracted_data = self.txt_to_xlsx.read_text(file_name)

        if max_items is not None and 0 < max_items < len(extracted_data):
            extracted_data = random.sample(extracted_data, max_items)
        current_date = datetime.now().strftime('%Y-%m-%d')
        output_file = os.path.join(self.txt_to_xlsx.data_folder, file_name.split('.')[0] + f"-{current_date}.mp3")
        # output_file = os.path.join(self.txt_to_xlsx.data_folder, file_name.split('.')[0] + ".mp3")

        voices = await VoicesManager.create()
        # voice_names = [
        #     'Microsoft Server Speech Text to Speech Voice (fr-FR, VivienneMultilingualNeural)',
        #     'Microsoft Server Speech Text to Speech Voice (fr-FR, DeniseNeural)',
        #     'Microsoft Server Speech Text to Speech Voice (fr-FR, EloiseNeural)',
        # ]
        # english_voice = voice_names[0]
        if language == "fr":
            excluded_voices = [
                'Microsoft Server Speech Text to Speech Voice (fr-FR, EloiseNeural)',
                'Microsoft Server Speech Text to Speech Voice (fr-FR, VivienneMultilingualNeural)',
                # 'Microsoft Server Speech Text to Speech Voice (fr-FR, HenriNeural)',
                'Microsoft Server Speech Text to Speech Voice (fr-FR, RemyMultilingualNeural)'
            ]
            all_voices = voices.find(Language="fr", Locale="fr-FR")
            voice_list = [voice for voice in all_voices if voice["Name"] not in excluded_voices]
        elif language == "en":
            voice_list = voices.find(Language="en", Locale="en-GB")
        else:
            raise ValueError("Unsupported language specified. Please choose 'fr' for French or 'en' for English.")
        chinese_voice = voices.find(
            Language='zh'
            , Gender="Female"
            , Locale="zh-CN"
        )

        with open(output_file, "wb") as file:
            current_date = datetime.now().strftime('%Y-%m-%d')
            print(f"测验时间: ___{current_date}___, 考核项：___重点语言点___")
            for index, item in enumerate(extracted_data):
                english_word = item['单词']
                chinese_meaning = item['释意']
                # print(f"{index + 1}: {english_word}, 翻译为_______")
                # print(f"{index + 1}: _______, 翻译为 {chinese_meaning}")

                voice_name = random.choice(voice_list)["Name"]
                chinese_voice_name = random.choice(chinese_voice)["Name"]
                # chinese_voice_name = "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)"
                print(f"Word: {english_word}, Translation: {chinese_meaning}, Voice: {voice_name}")
                # Repeat English audio twice
                for _ in range(repeat):
                    if language == "fr":
                        english_stream = edge_tts.Communicate(english_word, voice=voice_name, rate="-10%").stream()
                    elif language == "en":
                        english_stream = edge_tts.Communicate(english_word, voice=voice_name).stream()

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
        tool.remove_duplicates_or_merge_translations('词库源/高考词汇（持续更新中）.txt')
        tool.remove_duplicates_or_merge_translations('词库源/雅思基础词汇(持续更新中).txt')
        tool.remove_duplicates_or_merge_translations('词库源/雅思词汇（百词斩）.txt')

    @Test()
    def calculate_missing_words(self):
        tool = TxtToXLSX()
        # generate missing sounds
        tool.convert('词库源/高考词汇（持续更新中）.txt')
        tool.convert('词库源/雅思基础词汇(持续更新中).txt')
        tool.convert('词库源/雅思词汇（百词斩）.txt')

    @Test()
    def french_words(self):
        files = [
            '词库源/法语单词（持续更新中）.txt',
            '词库源/你好法语（持续更新中）.txt'
        ]
        tool = TxtToXLSX()
        for file in files:
            tool.remove_duplicates_or_merge_translations(file)
            tool.convert(file)

        # Create an instance of FrenchTTSProcessor and call its method
        processor = FrenchTTSProcessor()
        asyncio.run(processor.process_all_texts())

    @Test()
    def import_forgotten(self):
        student_name = "英语"  # TBD

        data_folder = get_sub_folder_path('data')
        import_file_path = os.path.join(data_folder, 'Import.txt')
        # 读取 Import.txt 中的新词
        new_words = []
        with open(import_file_path, 'r', encoding='utf-8') as import_file:
            for line in import_file:
                new_words.append(line.strip())

        review_folder_path = os.path.join(data_folder, 'review', student_name)
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
        def en_and_cn(file, max_items, language="fr"):
            start_time = time.time()  # Record start time
            converter = TextToSpeechConverter(tool)
            asyncio.run(converter.convert_text_to_audio(file, language, max_items=max_items))
            end_time = time.time()  # Record end time
            elapsed_time = end_time - start_time  # Calculate elapsed time
            print(f"Time taken: {elapsed_time} seconds")

        tool = TxtToXLSX()
        en_and_cn('每日法語.txt', max_items=None, language="fr")
        # en_and_cn('每日英語.txt', max_items=None, language="en")
