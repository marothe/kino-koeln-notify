# small image with Python and necessary packages
FROM python:3.11-slim

# create app directory
WORKDIR /app

# copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY kino_koeln.py .

# set environment variables defaults (can be overridden by compose)
ENV PUSHOVER_USER="" \
    PUSHOVER_TOKEN=""

# default command
CMD ["python", "kino_koeln.py"]
