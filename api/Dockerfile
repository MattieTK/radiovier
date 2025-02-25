FROM ghcr.io/astral-sh/uv:python3.13-bookworm

ADD . /app

WORKDIR /app

RUN uv sync --frozen

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y ffmpeg libpq-dev

EXPOSE 8000

# Get and extract models to the parent directory

# https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip
RUN wget https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip
RUN unzip vosk-model-spk-0.4.zip
RUN mv vosk-model-spk-0.4 ../vosk-model-spk-0.4
RUN rm -rf vosk-model-spk-0.4.zip

# https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
RUN wget https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
RUN unzip vosk-model-small-de-0.15.zip
RUN mv vosk-model-small-de-0.15 ../vosk-model-small-de-0.15
RUN rm -rf vosk-model-small-de-0.15.zip

# Start FastAPI with uvicorn enabling hot reloading; updated module path to match file structure
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
