import os
import asyncio
import random
import time
from aiohttp import ClientError
import edge_tts
from edge_tts import VoicesManager

from tool_generate_xls import get_sub_folder_path


# Function to read texts from a text file
def read_texts_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        texts = [line.strip() for line in file.readlines() if line.strip()]
    return texts


# Path to the text file under user_data directory
text_file_path = os.path.join(get_sub_folder_path(), 'MissingSound.txt')

# Generate the TEXT_LIST from the text file
TEXT_LIST = read_texts_from_file(text_file_path)


# Async function to process a batch of texts and convert them to speech
async def process_text_batch(texts, use_michelle=False, max_retries=3, retry_delay=2):
    sound_folder = get_sub_folder_path('static/sounds')  # Get the sound folder path

    for text in texts:
        print(f"Processing text: {text}")
        output_file = os.path.join(sound_folder, f"{text}.mp3")

        for attempt in range(1, max_retries + 1):  # Retry loop
            try:
                # Create VoicesManager instance
                voices = await VoicesManager.create()

                if use_michelle:
                    # Use Michelle voice specifically
                    name = "Microsoft Server Speech Text to Speech Voice (en-US, MichelleNeural)"
                    communicate = edge_tts.Communicate(text, name)
                else:
                    # Choose a random British English voice
                    voice = voices.find(Language="en", Locale="en-GB")
                    communicate = edge_tts.Communicate(text, random.choice(voice)["Name"])

                # Save the output
                await communicate.save(output_file)
                print(f"Successfully processed text: {text}")
                break  # Exit the retry loop if successful

            except ClientError as e:
                print(f"ClientError occurred on attempt {attempt} for text '{text}': {e}")
                if attempt == max_retries:
                    print(f"Failed to process text '{text}' after {max_retries} attempts. Skipping...")
                else:
                    await asyncio.sleep(retry_delay * attempt)  # Exponential backoff


            except Exception as e:
                print(f"Unexpected error for text '{text}' on attempt {attempt}: {e}")
                if attempt == max_retries:
                    print(f"Skipping text '{text}' due to persistent errors.")
                else:
                    await asyncio.sleep(retry_delay * attempt)  # Exponential backoff


# Main function to process the entire TEXT_LIST in batches
async def _main() -> None:
    start_time = time.time()  # Record start time
    batch_size = 10  # Define the batch size
    # Split the TEXT_LIST into batches
    batches = [TEXT_LIST[i:i + batch_size] for i in range(0, len(TEXT_LIST), batch_size)]

    # Process each batch sequentially
    for batch in batches:
        await process_text_batch(batch, max_retries=3, retry_delay=2)

    end_time = time.time()  # Record end time
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"Total elapsed time for processing {len(TEXT_LIST)} texts: {elapsed_time:.2f} seconds")
    print(f"Average time per text: {elapsed_time / len(TEXT_LIST):.2f} seconds")


if __name__ == "__main__":
    # Execute the main function
    try:
        asyncio.run(_main())
    except RuntimeError as e:
        print(f"RuntimeError occurred: {e}")
