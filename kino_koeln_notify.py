import os
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

URL           = "https://www.koeln.de/kino/"
BASE_URL      = "https://www.koeln.de"
PUSHOVER_USER  = os.environ["PUSHOVER_USER"]
PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
MAX_LENGTH    = 1024


def get_ov_movies(url: str):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    ov_movies = set()
    omu_movies = set()

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

        entry = f"{title} ({year})\n{link}"

        if "(OV)" in text:
            ov_movies.add(entry)
        if "(OmU)" in text:
            omu_movies.add(entry)

    return sorted(ov_movies), sorted(omu_movies)



def send_pushover_message(message: str, title: str) -> None:
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


def run():
    ov_movies, omu_movies = get_ov_movies(URL)
    send_in_chunks(list(ov_movies), "OV (Original Version)")
    send_in_chunks(list(omu_movies), "OmU (Original with Subtitles)")


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
