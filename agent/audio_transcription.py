import base64
import requests
from dotenv import load_dotenv
import os

load_dotenv()
bearer = os.getenv("BEARER_AUDIO_TRANSCRIPTION")

def audio_transcription(audio_base64:str) -> str:
    # Decodifica e salva em um arquivo temporário
    with open("temp_audio.mp3", "wb") as f: 
        f.write(base64.b64decode(audio_base64))

    # Agora envia o arquivo como antes
    headers = {
        "Authorization": f"Bearer {bearer}",
    }

    files = {
        'file': open("temp_audio.mp3", 'rb'),
        'model': (None, 'whisper-large-v3-turbo'),
        'language': (None, 'pt')
    }

    response = requests.post('https://api.groq.com/openai/v1/audio/transcriptions', headers=headers, files=files)
    result = response.json()
    return result
