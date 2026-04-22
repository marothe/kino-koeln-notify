import os
import time
from datetime import datetime, timezone
from typing import Optional
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


def absolutize_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return BASE_URL + path


def parse_year(movie_container) -> Optional[int]:
    for item in movie_container.select("ul.meta li"):
        label = item.select_one(".label")
        if not label or label.get_text(strip=True) != "Jahr":
            continue

        for part in item.get_text(separator="\n").splitlines():
            part = part.strip()
            if part.isdigit() and len(part) == 4:
                return int(part)

    return None


def parse_screenings(movie_container, language: str) -> list:
    screenings = []

    for day in movie_container.select("ul.shows-by-date > li.kk-tab"):
        date_label = day.select_one(".date-container span")
        date_label = date_label.get_text(" ", strip=True) if date_label else "Aktuelles Programm"

        for event in day.select('div[itemprop="event"]'):
            time_tag = event.select_one(".time")
            time_value = time_tag.get_text(" ", strip=True) if time_tag else ""
            start_date = event.select_one('meta[itemprop="startDate"]')
            start_date = start_date.get("content", "") if start_date else ""

            for location in event.select('p[itemprop="location"]'):
                version = location.select_one(".kk-ov-show-version")
                if not version or version.get_text(" ", strip=True) != f"({language})":
                    continue

                cinema_tag = location.select_one('meta[itemprop="name"]')
                cinema_name = cinema_tag.get("content", "").strip() if cinema_tag else ""
                cinema_link = location.select_one("a[href]")
                cinema_url = absolutize_url(cinema_link["href"]) if cinema_link else ""

                if cinema_name and time_value:
                    screenings.append(
                        {
                            "dateLabel": date_label,
                            "startDate": start_date,
                            "time": time_value,
                            "cinema": cinema_name,
                            "cinemaUrl": cinema_url,
                            "language": language,
                        }
                    )

    return screenings


def summarize_cinemas(screenings: list) -> str:
    cinemas = []
    for screening in screenings:
        cinema = screening["cinema"]
        if cinema not in cinemas:
            cinemas.append(cinema)
    if len(cinemas) <= 3:
        return ", ".join(cinemas)
    return ", ".join(cinemas[:3]) + f" +{len(cinemas) - 3}"


def summarize_showtimes(screenings: list) -> tuple[str, str]:
    if not screenings:
        return "Aktuelles Programm", "Details auf koeln.de"

    grouped = {}
    for screening in screenings:
        grouped.setdefault(screening["dateLabel"], [])
        if screening["time"] not in grouped[screening["dateLabel"]]:
            grouped[screening["dateLabel"]].append(screening["time"])

    first_date = next(iter(grouped))
    first_times = ", ".join(grouped[first_date][:5])
    if len(grouped[first_date]) > 5:
        first_times += f" +{len(grouped[first_date]) - 5}"

    if len(grouped) > 1:
        first_times += f" | +{len(grouped) - 1} Tage"

    return first_date, first_times


def build_movie(base_movie: dict, language: str, screenings: list) -> dict:
    date_label, showtime = summarize_showtimes(screenings)
    return {
        **base_movie,
        "id": slug(f"{base_movie['title']}-{language}-{base_movie['url']}"),
        "cinema": summarize_cinemas(screenings),
        "language": language,
        "showtime": showtime,
        "date": date_label,
        "isOmu": language == "OmU",
        "isOv": language == "OV",
        "screenings": screenings,
    }


def get_movies(url: str):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    movies = []

    for li in soup.select("li.movie-container"):
        title_tag = li.select_one('h2 a[itemprop="name"], h2 a[href^="/kino/film/"]')
        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = absolutize_url(title_tag["href"])
        year = parse_year(li)
        description = li.select_one('[itemprop="description"]')
        description = (
            description.get_text(" ", strip=True)
            if description
            else "Live aus dem koeln.de Kinoprogramm."
        )

        base_movie = {
            "title": title,
            "year": year,
            "description": description,
            "isClassic": bool(year and year <= 2010),
            "url": link,
        }

        for language in ("OV", "OmU"):
            screenings = parse_screenings(li, language)
            if screenings:
                movies.append(build_movie(base_movie, language, screenings))

    return sorted(movies, key=lambda movie: (movie["language"], movie["title"]))


def get_ov_movies(url: str):
    movies = get_movies(url)
    ov_movies = [
        f"{movie['title']} ({movie['year'] or 'Jahr unbekannt'})\n{movie['cinema']} · {movie['date']} · {movie['showtime']}\n{movie['url']}"
        for movie in movies
        if movie["isOv"]
    ]
    omu_movies = [
        f"{movie['title']} ({movie['year'] or 'Jahr unbekannt'})\n{movie['cinema']} · {movie['date']} · {movie['showtime']}\n{movie['url']}"
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
