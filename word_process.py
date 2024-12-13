import asyncio
import os
import re
from datetime import datetime

import edge_tts


class WordProcessor:
    def __init__(self):
        self.base_folder = os.path.dirname(os.path.abspath(__file__))
        self.data_folder = os.path.join(self.base_folder, 'data')
        self.daily_folder = os.path.join(self.data_folder, 'daily')

        for folder in [self.data_folder, self.daily_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def parse_line(self, line):
        """Parse line using regex to handle English phrases and Chinese text"""
        line = line.strip()
        if not line:
            return None, None

        # Regex pattern for English part: letters, spaces, and common punctuation
        pattern = r'^(?:\d+\.\s*)?([a-zA-Z\s\-\/\'\,\(\)\.]+?)([^a-zA-Z\s\-\/\'\,\(\)\.].+?)(?:\s*\(遗忘\s*\d+\s*次\))?$'
        match = re.match(pattern, line)

        if match:
            english = match.group(1).strip()
            chinese = match.group(2).strip()
            return english, chinese

        return None, None

    async def process_word_file(self, filename):
        english_voice = "Microsoft Server Speech Text to Speech Voice (en-GB, SoniaNeural)"
        chinese_voice = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"

        base_filename = os.path.splitext(filename)[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.daily_folder, f'{base_filename}_{timestamp}.mp3')
        file_path = os.path.join(self.daily_folder, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found in the daily folder.")
            return
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return

        with open(output_file, 'wb') as audio_file:
            for line_number, line in enumerate(lines, 1):
                try:
                    english_phrase, chinese_translation = self.parse_line(line)
                    if not english_phrase or not chinese_translation:
                        print(f"Skipping invalid line {line_number}: {line.strip()}")
                        continue

                    print(f"Processing: {english_phrase} - {chinese_translation}")

                    # English phrase twice
                    for _ in range(2):
                        communicate = edge_tts.Communicate(english_phrase, voice=english_voice)
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                audio_file.write(chunk["data"])
                        await asyncio.sleep(0.5)

                    # Chinese translation once
                    communicate = edge_tts.Communicate(chinese_translation, voice=chinese_voice)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])

                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"Error processing line {line_number}: {str(e)}")
                    continue

        print(f"\nAudio file created successfully: {output_file}")


async def main():
    processor = WordProcessor()
    await processor.process_word_file('每日英語.txt')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {str(e)}")
