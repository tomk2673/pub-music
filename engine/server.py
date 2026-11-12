"""Local studio server. Bind to loopback; no external uploads."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import zipfile
import os
import hmac
from flask import Flask, request, jsonify, send_file
from io import BytesIO


app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
ROOT = Path(__file__).resolve().parent.parent
LOCK = Lock()
EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".webm"}

@app.before_request
def local_only():
    if os.environ.get("HRAI_CLOUD") == "1":
        origin = os.environ.get("HRAI_ORIGIN", "")
        token = os.environ.get("HRAI_ENGINE_TOKEN", "")
        if not origin.startswith("https://") or not token:
            return jsonify(error="Engine configuration missing"), 503
        if request.headers.get("Origin") != origin:
            return jsonify(error="Origin rejected"), 403
        if request.method == "OPTIONS":
            return "", 204
        if not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + token):
            return jsonify(error="Unauthorized"), 401
        return
    if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
        return jsonify(error="Local host required"), 403
    if request.method == "POST" and request.headers.get("Origin") != request.host_url.rstrip("/"):
        return jsonify(error="Same-origin request required"), 403

@app.after_request
def cors(response):
    origin = os.environ.get("HRAI_ORIGIN", "")
    if os.environ.get("HRAI_CLOUD") == "1" and origin and request.headers.get("Origin") == origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response

@app.get("/studio")
@app.get("/studio/")
def studio():
    return send_file(ROOT / "studio" / "index.html")

@app.get("/api/health")
def health():
    return jsonify(status="ok", engine="python", mode="cloud" if os.environ.get("HRAI_CLOUD") == "1" else "local")

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
                from analyze import analyze
                return jsonify(analyze(str(source)))
            from separate import separate
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
    app.run(host="0.0.0.0" if os.environ.get("HRAI_CLOUD") == "1" else "127.0.0.1", port=int(os.environ.get("PORT", "8765")), debug=False)
