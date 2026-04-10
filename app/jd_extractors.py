import re
import requests
from bs4 import BeautifulSoup


def looks_like_url(text: str) -> bool:
    text = text.strip()
    return text.startswith("http://") or text.startswith("https://")


def clean_web_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_jd_url(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text("\n")
    text = clean_web_text(text)

    if len(text) < 200:
        raise ValueError(
            "The extracted page content looks too short. "
            "Please paste the JD text manually instead."
        )

    return text


def resolve_jd_input(jd_text: str, jd_url: str) -> str:
    """
    Priority:
    1. Use JD URL if provided
    2. Otherwise use pasted JD text
    """
    jd_url = jd_url.strip()
    jd_text = jd_text.strip()

    if jd_url:
        return extract_text_from_jd_url(jd_url)

    if jd_text:
        return jd_text

    return ""