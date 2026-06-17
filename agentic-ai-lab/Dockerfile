FROM python:3.12-slim

# Build tools for CrewAI's native deps (tiktoken, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# CrewAI's telemetry imports pkg_resources, which ships with setuptools.
# Python 3.12 slim no longer bundles it, AND setuptools >=81 removed
# pkg_resources entirely — so pin an older setuptools that still has it.
# Separate layer (after the cached crewai install) keeps rebuilds fast.
RUN pip install --no-cache-dir "setuptools<80"

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
