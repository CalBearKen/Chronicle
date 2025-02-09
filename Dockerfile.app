FROM python:3.9-slim

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set proper permissions
RUN chown -R app:app /app

# Switch to non-root user
USER app

CMD ["python", "app.py"] 