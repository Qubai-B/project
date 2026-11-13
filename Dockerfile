# Container for the guard's web interface (demo/live_app.py) in hosted mode.
# Build from the project root, or from the folder made by deploy/make_bundle.py:
#     docker build -t guard-interface .
#     docker run -p 7860:7860 -e GUARD_ACCESS_CODE=<choose a code> guard-interface
# The access code is compulsory: the container exits at once if GUARD_ACCESS_CODE is not set.
# On Vercel (container runtime, see vercel.json) set three environment variables in the project
# settings: GUARD_ACCESS_CODE, PORT=7860 (Vercel routes to port 80 unless PORT says otherwise) and
# GUARD_MAX_MB=4 (Vercel caps a request body at 4.5 MB).
# Debian 13 (trixie) is used because it ships Tesseract 5.5, the series the study used.
FROM python:3.11-slim-trixie

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

# Packages go into the system site-packages, not a user's home folder: some hosts start the
# container with a different user or HOME, and a per-user install is then invisible to Python.
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TLDEXTRACT_CACHE=/tmp/tldextract-cache
WORKDIR /app

COPY deploy/requirements-web.txt deploy/requirements-web.txt
RUN pip install --no-cache-dir -r deploy/requirements-web.txt \
 && python -c "import PIL, numpy, pytesseract, jinja2, presidio_analyzer, spacy; spacy.load('en_core_web_lg'); print('packages ok')" \
 && tesseract --version | head -n 1

COPY guard guard
COPY common common
COPY forms forms
COPY demo/live_app.py demo/live_page.html demo/
COPY data/benchmark/tax_self_assessment/I0001/filled/screenshot.png data/benchmark/tax_self_assessment/I0001/filled/screenshot.png
COPY data/benchmark/drivers_licence_renewal/I0001/filled/screenshot.png data/benchmark/drivers_licence_renewal/I0001/filled/screenshot.png
COPY data/benchmark/passport_application/I0001/filled/screenshot.png data/benchmark/passport_application/I0001/filled/screenshot.png

# Run as an ordinary user where the host allows it (uid 1000 is what Hugging Face Spaces expects).
# Nothing below depends on that user's home folder: the app only reads /app and writes to /tmp.
RUN useradd -m -u 1000 user
USER user

ENV GUARD_HOSTED=1 \
    PORT=7860
EXPOSE 7860
CMD ["python", "demo/live_app.py"]
