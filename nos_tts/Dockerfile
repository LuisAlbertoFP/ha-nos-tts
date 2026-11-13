FROM python:3.11-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

# torch < 2.9: a partir de 2.9 coqui-tts exige torchcodec (+ ffmpeg) para la E/S de audio.
RUN pip install "torch==2.8.0" "torchaudio==2.8.0" --index-url https://download.pytorch.org/whl/cpu
RUN pip install coqui-tts "wyoming==1.5.4" "torch==2.8.0" "torchaudio==2.8.0" \
    --extra-index-url https://download.pytorch.org/whl/cpu
# Dependencias que coqui-tts importa y no declara.
RUN pip install six "aiohttp>=3.9"
# Motor ONNX experimental (ajuste `motor = onnx`).
RUN pip install onnx onnxruntime
# Falla la construcción si algo no importa (evita descubrirlo al arrancar).
RUN python3 -c "from TTS.utils.synthesizer import Synthesizer; import wyoming, wyoming.error, aiohttp, onnx, onnxruntime; print('imports ok')"

COPY server.py /app/server.py
COPY web /app/web

CMD ["python3", "/app/server.py", "--models", "/share/nos_tts", "--port", "10200"]
