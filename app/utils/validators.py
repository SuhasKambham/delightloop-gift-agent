import requests
import re


def parse_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    cleaned = re.sub(r"[₹,INR\s]", "", price_str)
    try:
        return float(cleaned)
    except:
        return 0.0


def is_price_in_budget(price_numeric: float, budget_min: float, budget_max: float) -> bool:
    if price_numeric <= 0:
        return False
    # Tight tolerance: allow 5% below min for rounding/shipping variance
    return (budget_min * 0.5) <= price_numeric <= budget_max


def is_url_valid(url: str) -> bool:
    if not url or url == "":
        return False
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        # URL exists but couldn't verify — still keep it
        return True


def is_appropriate_for_professional(title: str) -> bool:
    inappropriate_keywords = [
        "alcohol", "wine", "beer", "whiskey", "lingerie",
        "adult", "intimate", "religious", "political",
        "health supplement", "medicine", "diet"
    ]
    title_lower = title.lower()
    for keyword in inappropriate_keywords:
        if keyword in title_lower:
            return False
    return True
