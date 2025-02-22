import os
import asyncio
import subprocess
import datetime
import json
import hashlib
import wave
from threading import Thread
from contextlib import asynccontextmanager


from dateutil import parser

import janus

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from vosk import Model, KaldiRecognizer
import psycopg2
from googletrans import Translator
from pydub import AudioSegment
import io

# -------------------------------
# Configuration & Database Setup
# -------------------------------

# PostgreSQL connection parameters – adjust these for your environment.
DB_NAME = "postgres"  # Your PostgreSQL database name
DB_USER = "postgres"  # Your PostgreSQL user
DB_PASSWORD = "Lu.ik!*u2c*VCZFGUWZVmsdWyb6HqK"  # Your PostgreSQL password
DB_HOST = "localhost"
DB_PORT = 5432


def get_db_connection():
    """Return a new PostgreSQL connection."""
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )


def init_db(conn):
    """Initialize the transcriptions table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transcriptions (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                audio_hash TEXT
            )
            """
        )
        conn.commit()


def save_transcription_to_db(conn, text, translation, audio_hash):
    """Saves a transcription entry (with UTC timestamp) into the PostgreSQL database."""
    timestamp = datetime.datetime.utcnow()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO transcriptions (timestamp, text, translation, audio_hash) VALUES (%s, %s, %s, %s)",
            (timestamp, text, translation, audio_hash),
        )
        conn.commit()
    return timestamp


# -------------------------------
# Audio & Transcription Settings
# -------------------------------

# Replace with your live stream URL
STREAM_URL = "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3?aggregator=web"
# Path to your downloaded VOSK German model directory
MODEL_PATH = "vosk-model-small-de-0.15"

# ffmpeg command to capture live audio (raw PCM: 16-bit, mono, 16kHz)
FFMPEG_CMD = [
    "ffmpeg",
    "-i",
    STREAM_URL,
    "-f",
    "s16le",  # output raw PCM
    "-acodec",
    "pcm_s16le",  # audio codec
    "-ac",
    "1",  # mono channel
    "-ar",
    "16000",  # sample rate in Hz
    "pipe:1",  # output to stdout
]

# Ensure the directory for audio snippets exists
AUDIO_DIR = "audio_snippets"
os.makedirs(AUDIO_DIR, exist_ok=True)

# -------------------------------
# Global Event Queue for SSE
# -------------------------------
# Using janus to share a queue between threads and asyncio
transcription_queue = janus.Queue()

# -------------------------------
# Helper Functions
# -------------------------------


def audio_generator(ffmpeg_process, chunk_size=4000):
    """Generator that yields audio chunks from ffmpeg's stdout."""
    while True:
        data = ffmpeg_process.stdout.read(chunk_size)
        if not data:
            break
        yield data


def stream_audio(ffmpeg_cmd):
    """Starts ffmpeg to capture audio from the live URL."""
    process = subprocess.Popen(
        ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    return process


def compute_audio_hash(audio_data):
    """Computes a SHA-256 hash for the given audio data."""
    return hashlib.sha256(audio_data).hexdigest()


def save_audio_to_file(audio_data, file_path):
    """Saves raw PCM audio data to an MP3 file."""
    # Create WAV in memory first
    wav_stream = io.BytesIO()
    with wave.open(wav_stream, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(16000)  # sample rate
        wf.writeframes(audio_data)

    # Convert to MP3 using pydub
    wav_stream.seek(0)
    audio = AudioSegment.from_wav(wav_stream)
    audio.export(file_path, format="mp3", parameters=["-q:a", "8"])


translator = Translator()


def translate_to_english(text):
    """Translates the given text to English."""
    try:
        translation = translator.translate(text, dest="en").text
    except Exception as e:
        print("Translation error:", e)
        translation = ""
    return translation


# -------------------------------
# Transcription Worker
# -------------------------------


def transcription_worker():
    """
    Background worker that:
      - Connects to PostgreSQL and ensures the transcriptions table exists.
      - Starts ffmpeg to capture audio.
      - Uses VOSK to transcribe German audio.
      - Buffers the audio corresponding to a final transcription.
      - Computes a hash for the audio snippet and saves it as a WAV file.
      - Translates the transcription to English.
      - Saves the transcription, translation, and audio hash to the database.
      - Pushes new transcription events to a global queue for SSE.
    """
    # Connect to PostgreSQL and initialize table
    conn = get_db_connection()
    init_db(conn)

    # Start ffmpeg to capture audio from the live stream
    ffmpeg_process = stream_audio(FFMPEG_CMD)
    audio_gen = audio_generator(ffmpeg_process)

    # Load the VOSK model and initialize the recognizer (16kHz sample rate)
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, 16000)

    # Buffer for audio corresponding to each finalized transcription
    audio_buffer = bytearray()

    try:
        for data in audio_gen:
            # Append incoming data to the audio buffer
            audio_buffer.extend(data)
            # Check if a final result is available
            if rec.AcceptWaveform(data):
                result = rec.Result()
                result_json = json.loads(result)
                transcript = result_json.get("text", "").strip()
                if transcript:
                    # Compute hash of the buffered audio data
                    audio_hash = compute_audio_hash(audio_buffer)
                    # Save the audio snippet as an MP3 file
                    file_path = os.path.join(AUDIO_DIR, f"{audio_hash}.mp3")
                    save_audio_to_file(audio_buffer, file_path)
                    # Translate the transcript to English
                    translation = translate_to_english(transcript)
                    # Save to database and get the timestamp
                    timestamp = save_transcription_to_db(
                        conn, transcript, translation, audio_hash
                    )
                    # Prepare event data
                    event_data = {
                        "timestamp": timestamp.isoformat(),
                        "text": transcript,
                        "translation": translation,
                        "audio_hash": audio_hash,
                    }
                    # Push the new transcription to the async queue for SSE
                    transcription_queue.sync_q.put(event_data)
                    print("New transcription:", event_data)
                # Clear the buffer after processing a segment
                audio_buffer = bytearray()
    except Exception as e:
        print("Error during transcription:", e)
    finally:
        ffmpeg_process.terminate()
        conn.close()


# -------------------------------
# FastAPI Application & API
# -------------------------------

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to start the transcription worker at startup.
    """
    thread = Thread(target=transcription_worker, daemon=True)
    thread.start()
    print("Transcription worker started.")
    yield
    # Optionally, cleanup resources here


app.router.lifespan_context = lifespan


@app.get("/api/transcriptions/recent")
async def get_recent_transcriptions():
    """
    Get transcriptions from the last 2 minutes.
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT timestamp, text, translation, audio_hash 
            FROM transcriptions 
            WHERE timestamp >= NOW() - INTERVAL '2 minutes'
            ORDER BY timestamp ASC
            """
        )
        rows = cur.fetchall()
    conn.close()

    return {
        "transcriptions": [
            {
                "timestamp": row[0].isoformat(),
                "text": row[1],
                "translation": row[2],
                "audio_hash": row[3],
            }
            for row in rows
        ]
    }


@app.get("/api/audio/{audio_hash}")
async def get_audio(audio_hash: str):
    """
    Serve audio files by hash.
    """
    file_path = os.path.join(AUDIO_DIR, f"{audio_hash}.mp3")
    if not os.path.exists(file_path):
        return {"error": "Audio file not found"}, 404
    return FileResponse(file_path, media_type="audio/mpeg")


@app.get("/api/events")
async def sse_endpoint():
    """
    Server-Sent Events endpoint to stream new transcription events.
    """

    async def event_generator():
        while True:
            # Wait for a new event from the async side of the janus queue.
            event = await transcription_queue.async_q.get()
            # SSE format: "data: <json>\n\n"
            yield f"data: {json.dumps(event)}\n\n"

    return EventSourceResponse(event_generator())


@app.get("/api/transcriptions/before/{timestamp}")
async def load_previous(timestamp: str):
    """
    Load messages from a 2-minute window before the given ISO timestamp.
    """
    try:
        before_dt = parser.isoparse(timestamp)
    except Exception as e:
        return {"error": "Invalid timestamp format", "detail": str(e)}

    two_minutes = datetime.timedelta(minutes=2)
    start_dt = before_dt - two_minutes

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT timestamp, text, translation, audio_hash 
            FROM transcriptions 
            WHERE timestamp >= %s AND timestamp < %s 
            ORDER BY timestamp ASC
            """,
            (start_dt, before_dt),
        )
        rows = cur.fetchall()
    conn.close()
    return {
        "transcriptions": [
            {
                "timestamp": row[0].isoformat(),
                "text": row[1],
                "translation": row[2],
                "audio_hash": row[3],
            }
            for row in rows
        ]
    }
