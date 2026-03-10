FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY . /app

# Install uv (dependency manager)
RUN python -m pip install --upgrade pip \
    && pip install uv

# Install dependencies defined in pyproject.toml
RUN uv sync

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]