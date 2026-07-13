import spacy
import re

from yahooquery import search

nlp = spacy.load("en_core_web_sm")

FINANCE_SPECIAL_SYMBOLS = {
    # Indexes
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "sensex": "^BSESN",
    "dow jones": "^DJI",
    "nasdaq": "^IXIC",
    "s&p 500": "^GSPC",

    # Crypto
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",

    # Metals
    "gold": "GC=F",
    "silver": "SI=F"
}

def choose_best_match(quotes):

    if not quotes:
        return None

    def score(item):

        score = 0

        symbol = item.get("symbol", "")
        quote_type = item.get("quoteType", "")
        exchange = item.get("exchange", "")
        name = item.get("shortname", "").lower()

        if quote_type == "EQUITY":
            score += 50

        if symbol.endswith(".NS"):
            score += 25

        if exchange in ["NSI", "NSE"]:
            score += 25

        if exchange in ["NMS", "NYQ"]:
            score += 20

        if name:
            score += 5

        return score

    quotes = sorted(quotes, key=score, reverse=True)

    return quotes[0]


def get_candidates(question):

    candidates = []

    question = question.strip()

    candidates.append(question)

    #
    # Remove common finance words ONLY
    #

    finance_words = [

        "stock",
        "stocks",
        "share",
        "shares",
        "price",
        "value",
        "today",
        "current",
        "chart",
        "graph"

    ]

    cleaned = question.lower()

    for word in finance_words:

        cleaned = re.sub(rf"\b{word}\b", "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)

    return candidates

def extract_company(question):

    doc = nlp(question)

    companies = []

    for ent in doc.ents:

        if ent.label_ == "ORG":

            companies.append(ent.text)

    if companies:

        return companies[0]

    return None


def resolve_symbol(question):

    question_lower = question.lower()

    #
    # Special symbols
    #

    for key, symbol in FINANCE_SPECIAL_SYMBOLS.items():

        if key in question_lower:

            return {

                "symbol": symbol,
                "name": key

            }

    #
    # Try multiple candidates
    #

    candidates = get_candidates(question)

    for candidate in candidates:

        print("Searching :", candidate)

        try:

            result = search(candidate)

            quotes = result.get("quotes", [])

            if not quotes:
                continue

            best = choose_best_match(quotes)

            if best:

                return {

                    "symbol": best.get("symbol"),

                    "name": best.get("shortname", candidate)

                }

        except Exception as ex:

            print(ex)

            continue

    return None