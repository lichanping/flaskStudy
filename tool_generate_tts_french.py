import os
import asyncio
import random
import time

import edge_tts
from edge_tts import VoicesManager

from tool_generate_xls import get_sub_folder_path, TxtToXLSX


# Function to read texts from a text file
def read_texts_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        # Read each line and remove leading/trailing whitespace
        texts = [line.strip() for line in file.readlines() if line.strip()]
    return texts


# Path to the text file under user_data directory
text_file_path = os.path.join(get_sub_folder_path(), 'MissingSound.txt')

# Generate the TEXT_LIST from the text file
TEXT_LIST = read_texts_from_file(text_file_path)

# Get the sound folder path
sound_folder = get_sub_folder_path('static/sounds')


# Async function to process a batch of texts and convert them to speech
async def process_text_batch(texts, use_michelle=False):
    for text in texts:
        print(f"Processing text: {text}")
        # Create output file path for each text
        output_file = os.path.join(sound_folder, f"{text}.mp3")

        # Create VoicesManager instance
        voices = await VoicesManager.create()

        if use_michelle:
            # Choose voice: specific Michelle voice
            # voice = "en-US-MichelleNeural"
            name = "Microsoft Server Speech Text to Speech Voice (en-US, MichelleNeural)"
            communicate = edge_tts.Communicate(text, name)
            await communicate.save(output_file)
        else:
            # Choose voice from the voice library
            # command:"edge-tts --list-voices"
            voice = voices.find(Language="fr", Locale="fr-FR")  # For French voices
            # voice = voices.find(Gender="Male", Language="en")
            # Use Edge TTS API to convert text to speech and save as MP3 file
            communicate = edge_tts.Communicate(text, random.choice(voice)["Name"])
            await communicate.save(output_file)


# Main function to process the entire TEXT_LIST in batches
async def _main() -> None:
    start_time = time.time()  # Record start time
    batch_size = 10  # Define the batch size
    # Split the TEXT_LIST into batches
    batches = [TEXT_LIST[i:i + batch_size] for i in range(0, len(TEXT_LIST), batch_size)]

    # Process each batch sequentially
    for batch in batches:
        await process_text_batch(batch)

    end_time = time.time()  # Record end time
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"Total elapsed time for processing {len(TEXT_LIST)} texts: {elapsed_time:.2f} seconds")
    print(f"Average time per text: {elapsed_time / len(TEXT_LIST):.2f} seconds")


if __name__ == "__main__":
    # Execute the main function
    asyncio.run(_main())
