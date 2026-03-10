# kino-koeln-notify

A lightweight Python notification utility that scrapes [koeln.de/kino](https://www.koeln.de/kino/) and sends a daily Pushover message listing all movies currently showing in Cologne in their **original language (OV)** or **original language with German subtitles (OmU)**. The list is built dynamically from the live website.

---

## What it does

- Fetches the cinema listings with `requests` and parses them using `BeautifulSoup`
- Identifies films tagged OV or OmU and pulls the release year
- Includes links back to the corresponding koeln.de detail pages
- Dispatches the results via Pushover, automatically splitting into multiple messages when needed

---

## Requirements

Python 3.9+ and these packages:

```bash
pip install -r requirements.txt
```

(The current `requirements.txt` already lists `requests`, `beautifulsoup4`, and `python-dotenv`.)

---

## Configuration

Environment variables drive the configuration. Define the following values before running:

```bash
PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_api_token
```

You obtain these credentials from [pushover.net](https://pushover.net). To keep them out of Git, put the two lines in a `.env` file at the project root; the script loads that file automatically.

### Docker

A simple `docker-compose.yml` is provided for containerized execution:

```yaml
version: "3.9"
services:
  kino:
    build: .
    environment:
      - PUSHOVER_USER=${PUSHOVER_USER}
      - PUSHOVER_TOKEN=${PUSHOVER_TOKEN}
    volumes:
      - ./:/app
    restart: unless-stopped
```

Start the service with:

```bash
docker-compose up --build
```

You can also run the script directly once the variables are exported:

```bash
export PUSHOVER_USER=... PUSHOVER_TOKEN=...
python kino_koeln_notify.py
```

---

## Usage

```bash
python kino_koeln_notify.py
```

(or via Docker Compose as shown above). Notifications look like:

```
OV (Original Version):
Marty Supreme (2025)
https://www.koeln.de/kino/film/marty-supreme

OmU (Original with Subtitles):
Father Mother Sister Brother (2025)
https://www.koeln.de/kino/film/father-mother-sister-brother
...
```

---

## Scheduling

For daily automation on Unix-like systems, add a cron entry:

```bash
crontab -e
```

Then include:

```
0 9 * * * /usr/bin/python3 /path/to/kino_koeln_notify.py
```

Adjust timing as desired.

---

## Notes

- Pushover limits each message to 1024 characters; the script splits long lists automatically.
- OmU movies have German subtitles, making them easy to follow.
- Live scraping ensures the data reflect the current listings.
- No static data file is required; `movie_titles.txt` was removed from the repository as part of the cleanup.