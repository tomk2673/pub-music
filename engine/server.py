"""Local studio server. Bind to loopback; no external uploads."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import zipfile
from flask import Flask, request, jsonify, send_file
from io import BytesIO
from analyze import analyze
from separate import separate

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
ROOT = Path(__file__).resolve().parent.parent
LOCK = Lock()
EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".webm"}

@app.before_request
def local_only():
    if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
        return jsonify(error="Local host required"), 403
    if request.method == "POST" and request.headers.get("Origin") != request.host_url.rstrip("/"):
        return jsonify(error="Same-origin request required"), 403

@app.get("/studio")
@app.get("/studio/")
def studio():
    return send_file(ROOT / "studio" / "index.html")

@app.get("/api/health")
def health():
    return jsonify(status="ok", engine="local-python")

@app.post("/api/<operation>")
def process(operation):
    if operation not in {"analyze", "separate"}:
        return jsonify(error="Unknown operation"), 404
    audio = request.files.get("audio")
    if not audio or Path(audio.filename or "").suffix.lower() not in EXT:
        return jsonify(error="Unsupported audio file"), 400
    if not LOCK.acquire(blocking=False):
        return jsonify(error="Engine busy"), 429
    try:
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / ("input" + Path(audio.filename).suffix.lower())
            audio.save(source)
            if operation == "analyze":
                return jsonify(analyze(str(source)))
            folder = separate(source, Path(tmp) / "output")
            result = BytesIO()
            with zipfile.ZipFile(result, "w", zipfile.ZIP_STORED) as archive:
                for name in ("vocals", "drums", "bass", "guitar", "piano", "other"):
                    archive.write(folder / (name + ".wav"), name + ".wav")
            result.seek(0)
            return send_file(result, mimetype="application/zip", as_attachment=True, download_name="HRAI-stems.zip")
    except Exception:
        app.logger.exception("Audio processing failed")
        return jsonify(error="Audio processing failed; check local server log"), 500
    finally:
        LOCK.release()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
