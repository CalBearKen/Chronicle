FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install wait-for-it for dependency management
RUN apt-get update && apt-get install -y wait-for-it

# Setup startup sequence
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"] 