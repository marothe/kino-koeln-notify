import os
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.koeln.de/kino/"
BASE_URL = "https://www.koeln.de"
PUSHOVER_USER = os.getenv("PUSHOVER_USER", "")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN", "")
KINO_WEBHOOK_URL = os.getenv("KINO_WEBHOOK_URL", "")
KINO_WEBHOOK_TOKEN = os.getenv("KINO_WEBHOOK_TOKEN", "")
MAX_LENGTH = 1024


def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


def get_movies(url: str):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    movies = {}

    for li in soup.select("ul > li"):
        title_tag = li.select_one("h2 a")
        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = BASE_URL + title_tag["href"]
        text = li.get_text()

        year = ""
        for item in li.select("li"):
            item_text = item.get_text(separator="\n").strip()
            if item_text.startswith("Jahr"):
                parts = item_text.split("\n")
                for part in parts:
                    part = part.strip()
                    if part.isdigit() and len(part) == 4:
                        year = part
                        break

        if "(OV)" in text:
            key = f"{title}-OV-{link}"
            movies[key] = {
                "id": slug(key),
                "title": title,
                "year": int(year) if year else None,
                "cinema": "koeln.de",
                "language": "OV",
                "showtime": "Details auf koeln.de",
                "date": "Aktuelles Programm",
                "description": "Live aus dem koeln.de Kinoprogramm.",
                "isClassic": bool(year and int(year) <= 2010),
                "isOmu": False,
                "isOv": True,
                "url": link,
            }
        if "(OmU)" in text:
            key = f"{title}-OmU-{link}"
            movies[key] = {
                "id": slug(key),
                "title": title,
                "year": int(year) if year else None,
                "cinema": "koeln.de",
                "language": "OmU",
                "showtime": "Details auf koeln.de",
                "date": "Aktuelles Programm",
                "description": "Live aus dem koeln.de Kinoprogramm.",
                "isClassic": bool(year and int(year) <= 2010),
                "isOmu": True,
                "isOv": False,
                "url": link,
            }

    return sorted(movies.values(), key=lambda movie: (movie["language"], movie["title"]))


def get_ov_movies(url: str):
    movies = get_movies(url)
    ov_movies = [
        f"{movie['title']} ({movie['year'] or 'Jahr unbekannt'})\n{movie['url']}"
        for movie in movies
        if movie["isOv"]
    ]
    omu_movies = [
        f"{movie['title']} ({movie['year'] or 'Jahr unbekannt'})\n{movie['url']}"
        for movie in movies
        if movie["isOmu"]
    ]

    return sorted(ov_movies), sorted(omu_movies), movies



def send_pushover_message(message: str, title: str) -> None:
    if not PUSHOVER_USER or not PUSHOVER_TOKEN:
        print("Pushover skipped – PUSHOVER_USER/PUSHOVER_TOKEN not configured")
        return

    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token":   PUSHOVER_TOKEN,
            "user":    PUSHOVER_USER,
            "message": message,
            "title":   title,
        },
    )
    if response.status_code == 200:
        print(f"Sent: {title}")
    else:
        print(f"Pushover failed – status {response.status_code}: {response.text}\n")


def send_in_chunks(entries: list, section_title: str) -> None:
    current = section_title + ":\n"
    for entry in entries if entries else ["- none -"]:
        line = entry + "\n"
        if len(current) + len(line) > MAX_LENGTH:
            send_pushover_message(current.strip(), "Kino Köln – OV/OmU heute")  
            current = line
        else:
            current += line
    if current.strip():
        send_pushover_message(current.strip(), "Kino Köln – OV/OmU heute")      


def publish_web_data(movies: list) -> None:
    if not KINO_WEBHOOK_URL:
        print("Web publish skipped – KINO_WEBHOOK_URL not configured")
        return

    headers = {"Content-Type": "application/json"}
    if KINO_WEBHOOK_TOKEN:
        headers["X-Kino-Token"] = KINO_WEBHOOK_TOKEN

    response = requests.post(
        KINO_WEBHOOK_URL,
        headers=headers,
        json={
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "source": "kino-koeln-notify",
            "movies": movies,
        },
        timeout=30,
    )
    response.raise_for_status()
    print(f"Published {len(movies)} movies to web")


def run():
    ov_movies, omu_movies, movies = get_ov_movies(URL)
    send_in_chunks(list(ov_movies), "OV (Original Version)")
    send_in_chunks(list(omu_movies), "OmU (Original with Subtitles)")
    publish_web_data(movies)


def wait_until_next_thursday(hour: int = 19, minute: int = 0) -> None:
    """Sleep until the next Thursday at the given hour:minute (local time)."""  
    now = datetime.now()
    days_ahead = (3 - now.weekday()) % 7  # 3 = Thursday
    # If it's already Thursday but past the target time, wait for next week     
    if days_ahead == 0 and (now.hour, now.minute) >= (hour, minute):
        days_ahead = 7
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)     
    target = target.replace(day=now.day + days_ahead)
    wait_seconds = (target - now).total_seconds()
    print(f"Next run scheduled for {target.strftime('%A %Y-%m-%d %H:%M')} — sleeping {wait_seconds/3600:.1f}h")
    time.sleep(wait_seconds)


if __name__ == "__main__":
    print("Kino Köln notifier started — runs every Thursday at 19:00")
    while True:
        wait_until_next_thursday(hour=19, minute=0)
        print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M')}")        
        run()
