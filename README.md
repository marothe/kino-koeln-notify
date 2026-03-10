# kino_köln_notify

A lightweight Python notification utility (formerly `Kino Köln`) that scrapes [koeln.de/kino](https://www.koeln.de/kino/) and sends a daily Pushover message listing all movies currently showing in Cologne in their **original language (OV)** or **original language with German subtitles (OmU)**. It no longer relies on a static `movie_titles.txt` file; the list is generated dynamically from the website.

---

## What it does

- Scrapes the koeln.de cinema listings using `requests` and `BeautifulSoup`
- Filters movies showing in OV (Originalversion) or OmU (Original mit Untertiteln)
- Extracts the release year directly from the page
- Includes a direct link to each movie's detail page on koeln.de
- Sends the results as a Pushover notification, splitting into multiple messages if needed

---

## Requirements

Python 3.9+ and the following libraries:

```
pip3 install requests beautifulsoup4
```

No browser driver, no external API keys required.

---

## Configuration

The app reads its settings from environment variables, which makes it easy to run locally or inside Docker. At minimum you need to set:

```
PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_api_token
```

You can obtain these from [pushover.net](https://pushover.net). To avoid committing secrets, create a `.env` file in the project root and add the two lines above. The script uses `python-dotenv` (already included in `requirements.txt`) to load the file automatically.

### Docker Compose

A `docker-compose.yml` is included for convenience. It will build the image from the `Dockerfile` and load the `.env` file:

```yaml
version: '3'
services:
  kino:
    build: .
    env_file:
      - .env
    command: python kino_koeln.py
```

Start the container with:

```bash
docker-compose up --build
```

You can also run the script directly with the environment variables set:

```bash
export PUSHOVER_USER=... PUSHOVER_TOKEN=...
python3 kino_koeln.py
```

---

## Usage

Run straight from Python:

```bash
python3 kino_koeln.py
```

or using Docker Compose:

```bash
docker-compose up --build
```
You'll receive a Pushover notification formatted like this:

```
OV (Original Version):
Marty Supreme (2025)
https://www.koeln.de/kino/film/marty-supreme

Wuthering Heights - Sturmhöhe (2026)
https://www.koeln.de/kino/film/wuthering-heights---sturmhoehe

OmU (Original with Subtitles):
Father Mother Sister Brother (2025)
https://www.koeln.de/kino/film/father-mother-sister-brother
...
```

---

## Automating with a daily schedule

To run the script automatically every day, add it as a cron job on macOS:

```bash
crontab -e
```

Then add a line like this to run it every morning at 9am:

```
0 9 * * * /usr/bin/python3 /path/to/kino_koeln.py
```

---

## Notes

- Pushover messages are capped at 1024 characters. If there are many films, the script automatically splits the output into multiple messages.
- OmU screenings include a German subtitle track — useful if you want to follow along.
- The script reads from the live koeln.de page, so listings reflect what's currently showing.
- The file `movie_titles.txt` was previously used for example output and has been removed from the repository; it is not needed for operation.