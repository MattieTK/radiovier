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

from vosk import Model, SpkModel, KaldiRecognizer
import psycopg2
from googletrans import Translator
from pydub import AudioSegment
import io

# -------------------------------
# Configuration & Database Setup
# -------------------------------

# PostgreSQL connection parameters – adjust these for your environment.
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))


def get_db_connection():
    """Return a new PostgreSQL connection."""
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )


def init_db(conn):
    """Initialize the transcriptions and speakers tables if they don't exist."""
    with conn.cursor() as cur:
        # Create speakers table to store unique speaker vectors
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS speakers (
                id SERIAL PRIMARY KEY,
                spk_vector TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        # Create transcriptions table with a foreign key to speakers
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transcriptions (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                audio_hash TEXT,
                speaker_id INTEGER REFERENCES speakers(id),
                programme TEXT,
                language TEXT
            )
            """
        )
        conn.commit()


def get_or_create_speaker(conn, spk_vector):
    """
    Given a speaker vector (e.g. list of floats), convert it to a canonical JSON string.
    Check if an identical speaker record exists; if so, return its ID, otherwise create it.
    """
    # Convert the speaker vector to a JSON string for canonical representation.
    print("Got a speaker")
    spk_str = json.dumps(spk_vector)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM speakers WHERE spk_vector = %s", (spk_str,))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            cur.execute(
                "INSERT INTO speakers (spk_vector) VALUES (%s) RETURNING id", (spk_str,)
            )
            speaker_id = cur.fetchone()[0]
            conn.commit()
            return speaker_id


def save_transcription_to_db(
    conn, text, translation, audio_hash, speaker_id, programme, language
):
    """Saves a transcription entry (with UTC timestamp) into the PostgreSQL database."""
    timestamp = datetime.datetime.utcnow()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transcriptions (timestamp, text, translation, audio_hash, speaker_id, programme, language)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (timestamp, text, translation, audio_hash, speaker_id, programme, language),
        )
        conn.commit()
    return timestamp


# -------------------------------
# Audio & Transcription Settings
# -------------------------------

# Replace with your live stream URL
STREAMS = [
    {
        "name": "DLF",
        "url": "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3?aggregator=web",
        "model_path": "../vosk-model-small-de-0.15",
        "speaker_model_path": "../vosk-model-spk-0.4",
        "language": "de",
    },
    # ...add additional stream configurations as needed...
]

# Ensure the directory for audio snippets exists
AUDIO_DIR = "audio_snippets"
os.makedirs(AUDIO_DIR, exist_ok=True)

# -------------------------------
# Global Event Queue for SSE
# -------------------------------
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


def transcribe_stream(config):
    """
    Background worker that:
      - Connects to PostgreSQL and ensures the transcriptions and speakers tables exist.
      - Starts ffmpeg to capture audio.
      - Uses VOSK to transcribe German audio.
      - Buffers the audio corresponding to a final transcription.
      - Computes a hash for the audio snippet and saves it as an MP3 file.
      - Translates the transcription to English.
      - Uses the speaker model to perform speaker identification and saves a reference
        to the speaker (via a foreign key in the speakers table).
      - Saves the transcription, translation, audio hash, and speaker ID to the database.
      - Pushes new transcription events to a global queue for SSE.
    """
    # Connect to PostgreSQL and initialize tables
    conn = get_db_connection()
    init_db(conn)

    # Start ffmpeg to capture audio from the live stream
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        config["url"],
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
    ffmpeg_process = stream_audio(ffmpeg_cmd)
    audio_gen = audio_generator(ffmpeg_process)

    # Load the main VOSK model and initialize the recognizer (16kHz sample rate)
    model = Model(config["model_path"])
    rec = KaldiRecognizer(model, 16000)
    # Load the speaker model and set it for the recognizer
    spk_model = SpkModel(config["speaker_model_path"])
    rec.SetSpkModel(spk_model)

    # Buffer for audio corresponding to each finalized transcription
    audio_buffer = bytearray()

    try:
        for data in audio_gen:
            # Append incoming data to the audio buffer
            audio_buffer.extend(data)
            # Check if a final result is available
            if rec.AcceptWaveform(data):
                # print("Final result:", rec.Result())
                result = rec.Result()
                result_json = json.loads(result)
                transcript = result_json.get("text", "").strip()
                spk_vector = result_json.get("spk", None)  # Speaker vector
                print("Speaker vector:", spk_vector)
                if transcript:
                    # Compute hash of the buffered audio data
                    audio_hash = compute_audio_hash(audio_buffer)
                    # Save the audio snippet as an MP3 file
                    file_path = os.path.join(AUDIO_DIR, f"{audio_hash}.mp3")
                    save_audio_to_file(audio_buffer, file_path)
                    # Translate the transcript to English
                    translation = ""
                    if config["language"].lower() != "en":
                        translation = translate_to_english(transcript)
                    # Get or create a speaker record if a speaker vector is available
                    speaker_id = None
                    if spk_vector is not None:
                        speaker_id = get_or_create_speaker(conn, spk_vector)
                    # Save to database and get the timestamp
                    timestamp = save_transcription_to_db(
                        conn,
                        transcript,
                        translation,
                        audio_hash,
                        speaker_id,
                        config["name"],
                        config["language"],
                    )
                    # Prepare event data to push via SSE
                    event_data = {
                        "timestamp": timestamp.isoformat(),
                        "text": transcript,
                        "translation": translation,
                        "audio_hash": audio_hash,
                        "speaker_id": speaker_id,
                        "programme": config["name"],
                        "language": config["language"],
                    }
                    transcription_queue.sync_q.put(event_data)
                    print("New transcription:", event_data)
                # Clear the buffer after processing a segment
                audio_buffer = bytearray()
    except Exception as e:
        print(f"Error in stream {config['name']}: {e}")
    finally:
        ffmpeg_process.terminate()
        conn.close()


# -------------------------------
# FastAPI Application & API
# -------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to start the transcription worker at startup.
    """
    for stream in STREAMS:
        thread = Thread(target=transcribe_stream, args=(stream,), daemon=True)
        thread.start()
        print(f"Transcription worker started for {stream['name']}.")
    yield


app.router.lifespan_context = lifespan


@app.get("/api/transcriptions/recent")
async def get_recent_transcriptions(programme: str = None):
    print("Getting recent transcriptions")
    """
    Get transcriptions from the last 2 minutes.
    """
    conn = get_db_connection()
    query = """
            SELECT id, timestamp, text, translation, audio_hash, speaker_id, programme, language
            FROM transcriptions 
            WHERE timestamp >= NOW() - INTERVAL '10 minutes'
            """
    params = []
    if programme:
        query += " AND programme = %s"
        params.append(programme)
    query += " ORDER BY timestamp ASC LIMIT 50"
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    conn.close()
    return {
        "transcriptions": [
            {
                "timestamp": row[1].isoformat(),
                "text": row[2],
                "translation": row[3],
                "audio_hash": row[4],
                "speaker_id": row[5],
                "programme": row[6],
                "language": row[7],
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
            event = await transcription_queue.async_q.get()
            yield f"data: {json.dumps(event)}\n\n"

    return EventSourceResponse(event_generator())
