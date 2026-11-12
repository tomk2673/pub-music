FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY engine/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0
COPY engine/ /app/engine/
COPY studio/ /app/studio/
RUN useradd -m studio && chown -R studio:studio /app
USER studio
WORKDIR /app/engine
ENV HRAI_CLOUD=1 PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --workers 1 --threads 2 --timeout 600 --bind 0.0.0.0:$PORT server:app"]
