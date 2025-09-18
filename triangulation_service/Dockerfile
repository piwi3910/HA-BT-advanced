FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY proxies.yaml .

# Environment variables
ENV CONFIG_PATH=/app/proxies.yaml
ENV MQTT_HOST=localhost
ENV MQTT_PORT=1883
ENV MQTT_USERNAME=
ENV MQTT_PASSWORD=

# Run the application
CMD ["python", "main.py"]