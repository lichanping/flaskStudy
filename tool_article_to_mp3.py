import asyncio
import os
import random
import time

import edge_tts

from tool_generate_xls import get_sub_folder_path


class TextToSpeechConverter:
    def __init__(self):
        pass

    async def read_text_files(self, input_folder):
        # Get the path of the input folder
        input_folder_path = os.path.join(get_sub_folder_path(), input_folder)
        # Get the list of all text files in the input folder
        text_files = [file for file in os.listdir(input_folder_path) if file.endswith('.txt')]
        return text_files

    async def read_text_from_file(self, text_file_path):
        with open(text_file_path, 'r', encoding='utf-8') as file:
            # Read the entire content of the file
            return file.read().strip()  # Remove leading/trailing whitespace

    async def process_text_file(self, text_file_name, input_folder, output_folder):
        # Create the input file path
        input_file_path = os.path.join(get_sub_folder_path(), input_folder, text_file_name)
        text_content = await self.read_text_from_file(input_file_path)

        # Create VoicesManager instance
        voice_list = [
            "Microsoft Server Speech Text to Speech Voice (fr-FR, VivienneMultilingualNeural)",
            "Microsoft Server Speech Text to Speech Voice (fr-FR, RemyMultilingualNeural)"
        ]
        voice_name = random.choice(voice_list)
        # Generate the output file name
        output_file_name = text_file_name.replace(".txt", ".mp3")
        output_file = os.path.join(output_folder, output_file_name)

        # Generate TTS and save the output file
        communicate = edge_tts.Communicate(text_content, voice_name, rate="-10%")
        await communicate.save(output_file)
        print(f"Generated TTS for file: {text_file_name} using voice: {voice_name}")

    async def convert_text_to_speech(self, input_folder, output_folder):
        start_time = time.time()
        # Read all text files from the input folder
        text_files = await self.read_text_files(input_folder)
        # Process each text file
        for text_file_name in text_files:
            await self.process_text_file(text_file_name, input_folder, output_folder)
        end_time = time.time()  # Record end time
        elapsed_time = end_time - start_time  # Calculate elapsed time
        print(f"Total elapsed time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    input_folder = "TEXT_SOURCE"  # Specify the input folder containing text files
    output_folder = "VOICE_OUTPUT"  # Specify the output folder here
    output_folder_path = os.path.join(get_sub_folder_path(), output_folder)

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder_path, exist_ok=True)

    converter = TextToSpeechConverter()
    asyncio.run(converter.convert_text_to_speech(input_folder, output_folder_path))
