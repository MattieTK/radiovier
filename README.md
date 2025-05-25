# Live Audio Transcription and Translation System

This project is a web application designed to capture live audio streams, transcribe the speech into text, translate the transcriptions into English, identify different speakers, and display this information in real-time on a user-friendly interface.

## Key Features

*   **Live Audio Stream Processing:** Captures and processes audio from live streams in real-time.
*   **Speech-to-Text Transcription:** Utilizes VOSK for accurate speech-to-text conversion.
*   **Speaker Identification:** Capable of distinguishing between different speakers in the audio stream.
*   **Automatic Translation:** Translates transcribed text into English using Google Translate.
*   **Real-time Frontend Updates:** Employs Server-Sent Events (SSE) to deliver live updates to the web interface.
*   **Data Persistence:** Stores transcriptions, translations, and speaker identification data in a PostgreSQL database.
*   **API Access:** Provides API endpoints for retrieving transcription data and associated audio snippets.

## Project Structure

The project is organized into two main components:

*   **`api/`**: Contains the backend application built with Python and FastAPI. This component handles audio capture, transcription, translation, speaker identification, database interactions, and serving the API.
*   **`frontend/`**: Contains the frontend application built with Next.js (React/TypeScript). This component provides the user interface for displaying live transcriptions and interacting with the system.
*   **`docker-compose.yml`**: This file orchestrates the deployment of the entire application, managing the database, backend, and frontend services.
*   **`.env.example`**: A template for the environment variables required to configure the application.

## Setup and Installation

Follow these steps to get the project up and running:

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and provide the necessary values, especially for `DB_PASSWORD`. Other defaults are provided.

3.  **Download VOSK Models:**
    The application requires VOSK speech recognition models and speaker identification models.
    *   **German Language Model:** Download the VOSK model for German (e.g., `vosk-model-small-de-0.15`) from the [VOSK models page](https://alphacephei.com/vosk/models).
        *   Extract the model archive and place its contents into the `api/vosk-model-small-de-0.15` directory (create this directory if it doesn't exist).
    *   **Speaker Identification Model:** Download a speaker model (e.g., `vosk-model-spk-0.4`) from the same [VOSK models page](https://alphacephei.com/vosk/models).
        *   Extract the model archive and place its contents into the `api/vosk-model-spk-0.4` directory (create this directory if it doesn't exist).
    *   *Note: If you configure new streams with different languages, you will need to download and configure the appropriate models for those languages as well.*

4.  **Build and Run with Docker Compose:**
    This is the recommended way to run the application as it sets up all services (database, API, frontend).
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs the services in detached mode.

5.  **Database Initialization:**
    The first time the API starts, it will automatically create the necessary tables (`speakers` and `transcriptions`) in the PostgreSQL database.

## How to Use the Application

Once the application is running (after `docker-compose up --build`):

*   **Frontend:** Open your web browser and navigate to `http://localhost:3000`.
    *   You should see the main page displaying "Deutschlandfunk Transcriptions."
    *   Live transcriptions from the configured stream (initially Deutschlandfunk) will appear as they are processed.
    *   Each transcription entry will show the original text, the English translation (if the source language is not English), and a speaker ID.
    *   You can click on a transcription item to play the corresponding audio snippet.

*   **API:** The backend API is accessible at `http://localhost:8000`.
    *   You can explore the API endpoints (e.g., using a tool like Postman or directly in your browser for GET requests). The available endpoints are described in the "API Endpoints" section below.
    *   The API documentation (Swagger UI) should be available at `http://localhost:8000/docs`.

## API Endpoints

The backend provides the following API endpoints:

*   **`GET /api/transcriptions/recent`**:
    *   Retrieves recent transcriptions from the database.
    *   By default, it fetches transcriptions from the last 10 minutes, limited to 50 entries, ordered by timestamp.
    *   **Query Parameters:**
        *   `programme` (optional): Filter transcriptions by a specific programme name (e.g., "DLF" as defined in `api/main.py`).
    *   **Example:** `http://localhost:8000/api/transcriptions/recent?programme=DLF`

*   **`GET /api/audio/{audio_hash}`**:
    *   Serves an audio snippet (MP3) corresponding to the provided `audio_hash`.
    *   The `audio_hash` is available in the transcription objects returned by `/api/transcriptions/recent` and streamed via `/api/events`.
    *   **Example:** `http://localhost:8000/api/audio/some_long_sha256_hash.mp3` (The actual hash will be generated by the system).

*   **`GET /api/events`**:
    *   This is a Server-Sent Events (SSE) endpoint.
    *   It streams new transcription events (including the transcript, translation, speaker ID, audio hash, etc.) to connected clients in real-time.
    *   The frontend uses this endpoint to display live updates.

*   **API Documentation (Swagger UI):**
    *   Interactive API documentation is available at `http://localhost:8000/docs` when the API service is running. This interface allows you to view and test all available API endpoints.

## Configuration - Adding New Streams

The application is designed to process multiple audio streams. You can configure new streams by editing the `STREAMS` list in `api/main.py`.

Each entry in the `STREAMS` list is a dictionary with the following keys:

*   `name`: A user-friendly name for the stream (e.g., "DLF", "BBC Radio 4"). This name can be used as the `programme` query parameter in the `/api/transcriptions/recent` endpoint.
*   `url`: The URL of the live audio stream (e.g., an MP3 stream URL).
*   `model_path`: The path (relative to the `api` directory) to the VOSK language model for this stream. You will need to download the appropriate model if the stream is not in German (the default "DLF" stream's language).
*   `speaker_model_path`: The path (relative to the `api` directory) to the VOSK speaker identification model.
*   `language`: The language code for the stream (e.g., "de" for German, "en" for English). This is used to determine if translation is needed.

**Example `STREAMS` configuration in `api/main.py`:**

```python
STREAMS = [
    {
        "name": "DLF",
        "url": "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3?aggregator=web",
        "model_path": "../vosk-model-small-de-0.15",  # Relative to api/ directory
        "speaker_model_path": "../vosk-model-spk-0.4", # Relative to api/ directory
        "language": "de",
    },
    # Add another stream configuration:
    # {
    #     "name": "MyEnglishStream",
    #     "url": "your_english_stream_url_here",
    #     "model_path": "../vosk-model-en-us-0.22-lgraph", # Example English model path
    #     "speaker_model_path": "../vosk-model-spk-0.4",
    #     "language": "en",
    # },
]
```

**Important Considerations:**

*   **Model Paths:** Ensure the `model_path` and `speaker_model_path` correctly point to the VOSK model directories within the `api` container (e.g., place downloaded models in subdirectories like `api/vosk-model-en-us-0.22-lgraph/` and adjust the path). Docker volumes map the local `api/` directory to `/app/` in the container, so paths like `../vosk-model-small-de-0.15` from `api/main.py` would resolve to `/app/vosk-model-small-de-0.15` inside the container. It's generally cleaner to place models inside a subdirectory of `api/` (e.g. `api/models/vosk-model-small-de-0.15`) and reference them as `models/vosk-model-small-de-0.15`.
*   **Resource Usage:** Each stream runs in its own transcription thread. Adding many streams can significantly increase CPU and memory usage.
*   **Restart API Service:** After modifying `STREAMS` in `api/main.py`, you'll need to rebuild and restart the API service for the changes to take effect:
    ```bash
    docker-compose up --build -d api
    # or restart all services
    docker-compose restart api
    ```
    If you only changed `main.py` and not dependencies, a simple restart might suffice: `docker-compose restart api`.

## Technologies Used

*   **Backend:**
    *   Python
    *   FastAPI: Modern, fast (high-performance) web framework for building APIs.
    *   VOSK: Offline open-source speech recognition toolkit for transcription and speaker identification.
    *   Google Translate (`googletrans` library): For translating text to English.
    *   PostgreSQL (with pgvector extension potentially, though not explicitly used for vector similarity in the current code, the DB image `ramsrib/pgvector:16` suggests it's available): Robust open-source relational database.
    *   ffmpeg: For audio processing and stream capture.
    *   Pydub: For audio manipulation (e.g., converting WAV to MP3).
    *   Janus: For thread-safe queues (inter-thread communication).

*   **Frontend:**
    *   Next.js: React framework for server-side rendering and static site generation.
    *   React: JavaScript library for building user interfaces.
    *   TypeScript: Superset of JavaScript that adds static typing.
    *   Tailwind CSS: Utility-first CSS framework for rapid UI development.

*   **Orchestration & Environment:**
    *   Docker: Platform for developing, shipping, and running applications in containers.
    *   Docker Compose: Tool for defining and running multi-container Docker applications.
