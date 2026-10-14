FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app ./app
COPY payouts ./payouts
COPY lib ./lib
COPY jobs ./jobs
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app.api:create_app()"]
