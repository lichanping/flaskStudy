import asyncio
import os
import edge_tts
import re
from datetime import datetime
import time


class WordProcessor:
    def __init__(self):
        # Create path for data/daily structure
        self.base_folder = os.path.dirname(os.path.abspath(__file__))
        self.data_folder = os.path.join(self.base_folder, 'data')
        self.daily_folder = os.path.join(self.data_folder, 'daily')

        # Create folders if they don't exist
        for folder in [self.data_folder, self.daily_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    async def process_word_file(self, filename):
        # Setup voices
        english_voice = "Microsoft Server Speech Text to Speech Voice (en-GB, SoniaNeural)"
        chinese_voice = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"

        # Get filename without extension
        base_filename = os.path.splitext(filename)[0]

        # Create output filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.daily_folder, f'{base_filename}_{timestamp}.mp3')

        # Read from daily folder
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

        # Process each line and create audio
        with open(output_file, 'wb') as audio_file:
            for line_number, line in enumerate(lines, 1):
                try:
                    # Skip empty lines
                    if not line.strip():
                        continue

                    # Parse the line
                    parts = line.strip().split('\t')
                    if len(parts) != 2:
                        print(f"Skipping invalid line {line_number}: {line.strip()}")
                        continue

                    english_word = parts[0].strip()
                    chinese_translation = parts[1].strip()

                    # Remove part of speech notation if present
                    chinese_translation = re.sub(r'\([^)]*\)\s*', '', chinese_translation)

                    print(f"Processing: {english_word} - {chinese_translation}")

                    # English word twice
                    for _ in range(2):
                        communicate = edge_tts.Communicate(english_word, voice=english_voice)
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                audio_file.write(chunk["data"])
                        await asyncio.sleep(0.5)  # Small pause between repetitions

                    # Chinese translation once
                    communicate = edge_tts.Communicate(chinese_translation, voice=chinese_voice)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])

                    # Pause between words
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
