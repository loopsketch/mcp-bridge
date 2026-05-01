FROM python:3.12-slim@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --system --uid 1000 --user-group --no-create-home app \
    && chown -R app:app /app

COPY --chown=app:app src ./src

USER app

CMD ["python", "src/llama-mcp.py"]
