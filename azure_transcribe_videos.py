import azure.cognitiveservices.speech as speechsdk
import moviepy.editor as mp
import time
import os
import openai  # Install using: pip install openai

# Azure & OpenAI API credentials
AZURE_SUBSCRIPTION_ID = ''
AZURE_REGION = 'westus'
OPENAI_API_KEY = ''  # Add your OpenAI API key here

# Directory paths
VIDEO_INPUT_DIRECTORY = 'input_videos'
OUTPUT_DIRECTORY = 'results'

if not AZURE_SUBSCRIPTION_ID or not AZURE_REGION or not OPENAI_API_KEY:
    print('Please update the API keys in the script.')
    exit()

speech_config = speechsdk.SpeechConfig(subscription=AZURE_SUBSCRIPTION_ID, region=AZURE_REGION)

def speech_to_text(audio_filename):
    """Converts speech from audio to text using Azure Speech SDK."""
    audio_input = speechsdk.audio.AudioConfig(filename=audio_filename)
    speech_config.speech_recognition_language = "en-US"
    
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
    all_results = []

    def handle_final_result(evt):
        all_results.append(evt.result.text)

    done = False

    def stop_cb(evt):
        speech_recognizer.stop_continuous_recognition()
        nonlocal done
        done = True

    speech_recognizer.recognized.connect(handle_final_result)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    speech_recognizer.start_continuous_recognition()

    while not done:
        time.sleep(0.5)

    return " ".join(all_results)

def summarize_text(text):
    """Uses OpenAI GPT API to summarize the transcribed text."""
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "Summarize the following text."},
                  {"role": "user", "content": text}],
        temperature=0.5,
        max_tokens=500
    )
    return response['choices'][0]['message']['content'].strip()

def video_to_wav(file, output_file):
    """Extracts audio from video and saves it as a WAV file."""
    if os.path.exists(output_file):
        print(f'File already converted: {file}')
        return
    if file.endswith('.mp4'):
        print(f'Converting {file} to WAV...')
        clip = mp.VideoFileClip(os.path.join(VIDEO_INPUT_DIRECTORY, file))
        clip.audio.write_audiofile(output_file)
        print('Conversion finished.')

def cleanup_audio_files(directory):
    """Deletes intermediate audio files after processing."""
    for file in os.listdir(directory):
        if file.endswith('.wav'):
            os.remove(os.path.join(directory, file))

def main():
    """Processes all videos in the input directory, transcribes, summarizes, and saves results."""
    for file in os.listdir(VIDEO_INPUT_DIRECTORY):
        if not file.endswith('.mp4'):
            continue

        name = os.path.splitext(file)[0]
        wav_file = f'{OUTPUT_DIRECTORY}/{name}.wav'
        transcript_file = f'{OUTPUT_DIRECTORY}/{name}_transcript.txt'
        summary_file = f'{OUTPUT_DIRECTORY}/{name}_summary.txt'

        if os.path.exists(summary_file):
            print(f'Summary already exists for {file}')
            continue

        print(f'Processing {file}...')
        video_to_wav(file, wav_file)

        print('Transcribing audio...')
        full_text = speech_to_text(wav_file)
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(full_text)

        print('Summarizing text...')
        summary = summarize_text(full_text)
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)

    print('Processing complete. Cleaning up...')
    cleanup_audio_files(OUTPUT_DIRECTORY)

if __name__ == "__main__":
    main()