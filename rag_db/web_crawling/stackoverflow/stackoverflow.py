import time
import json
import cloudscraper
from bs4 import BeautifulSoup
import re

# Configuration
BASE_URL    = 'https://stackoverflow.com'
TAG         = 'ns-3'
DELAY       = 1                 # Delay between requests (seconds)
MAX_PAGES   = 30                # Number of pages to crawl (15 posts per page)
OUTPUT_FILE = 'ns3_qa.json'

scraper = cloudscraper.create_scraper()
HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'cookie': 'prov=17412cb4-95bb-42a0-b540-b9eb92e3817f; __cflb=02DiuFA7zZL3enAQJD3AX8ZzvyzLcaG7vcjPjo1wsSvkC; OptanonAlertBoxClosed=2025-05-26T11:27:27.666Z; usr=p=%5b160%7c%3bNewest%3b%3b%5d; __cf_bm=77DFPlfgCwkx9kVWUxlSW1ey133RgkpulzolsV4Da9A-1748330957-1.0.1.1-ksM8eB1.S5N3RfeNxjhHE9kNLA9Epa7hY5miwzOwHHqhdCu0R2AkeY1Ww.xRSnsXRix9VbN3XtT0_wR0o2Jny6ql9SiWvTH3.JuQRpEadjU; _cfuvid=ffAKE9dEimXDaPh4WkkSq_NU2A2_lyi4AuLYS7AcMz0-1748330957044-0.0.1.1-604800000; cf_clearance=hr8eN25o_9PldzcldPPNB4.gLszk7M8316CC2O518FE-1748330957-1.2.1.1-Ksg2TbTCjEoGc5GHvtqW6LnMA_excpo9qV202TLjttce77tTNRY1Uw9lq88AcSbClGBrNSgkPCmIgfLRKmZJI1szzG_Fw7tqLKQnaTiZf45oAFUbUoPuK67YeCw7n7PVxVdcNS5urxtky4I4phy6lBxXRJNBhxpfWb5bmAZHhDwRPOWNCNlWm6yUeYmmAS9yn45u6QYLFZXi0bMHyHH05_3TqjYc1N7Z7FVg1N54AHZf98Ke4e2H3T4oPnxwInS1DkUP5.nb2jvJmZGI6ib9Lcg5Au1cNDs3.x1mHwwgvBV3Zkz7hLwXdpTcvUqolaMV_tKC_onLTgQbg9w6ttqbzaeei1gJutwbYW9M9rzeRlA; OptanonConsent=isGpcEnabled=0&datestamp=Tue+May+27+2025+16%3A35%3A42+GMT%2B0900+(%ED%95%9C%EA%B5%AD+%ED%91%9C%EC%A4%80%EC%8B%9C)&version=202411.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=bc4f4caf-b41f-42dc-bf12-e20d28aafb0c&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0003%3A0%2CC0004%3A0&AwaitingReconsent=false&intType=2&geolocation=KR%3B46'
}

# Helpers
def slugify(title: str) -> str:
    """Convert title to URL slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip('-')
    return slug


def get_question_links(page: int) -> list:
    """Fetch question URLs from the tagged listing page."""
    url = f"{BASE_URL}/questions/tagged/{TAG}?tab=newest&page={page}"
    resp = scraper.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    links = []
    for summary in soup.select('div.s-post-summary'):
        a = summary.select_one('h3.s-post-summary--content-title a.s-link')
        if a and a.get('href'):
            links.append(BASE_URL + a['href'])
    return links


def parse_question(url: str) -> dict:
    """Parse question page for title, body, and best answer."""
    resp = scraper.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Title
    title_tag = soup.select_one('h1 a.question-hyperlink')
    title = title_tag.get_text(strip=True) if title_tag else ''

    # Question body
    q_body = soup.select_one('div.s-prose.js-post-body')
    question = q_body.get_text("\n", strip=True) if q_body else ''

    # Answer: accepted first, else highest-score
    answer = ''
    acc = soup.select_one('div.answer.js-accepted-answer')
    if acc:
        body = acc.select_one('div.s-prose.js-post-body')
        answer = body.get_text("\n", strip=True) if body else ''
    else:
        candidates = []
        for a_div in soup.select('div.answer'):
            body = a_div.select_one('div.s-prose.js-post-body')
            text = body.get_text("\n", strip=True) if body else ''
            score_tag = a_div.select_one('div.js-vote-count')
            try:
                score = int(score_tag.get_text(strip=True))
            except:
                score = 0
            candidates.append((score, text))
        if candidates:
            answer = max(candidates, key=lambda x: x[0])[1]

    return {'url': url, 'title': title, 'question': question, 'answer': answer}

# Main
def main():
    results = []
    for page in range(1, MAX_PAGES + 1):
        print(f"[Page {page}] fetching listings...")
        try:
            links = get_question_links(page)
        except Exception as e:
            print(f"Failed to fetch page {page}: {e}")
            break
        if not links:
            break

        for link in links:
            print(f"  -> parsing {link}")
            try:
                qa = parse_question(link)
                # Skip unanswered questions
                if not qa['answer'].strip():
                    print(f"    skipped {link} (no answer)")
                    continue
                results.append(qa)
            except Exception as e:
                print(f"    parse error for {link}: {e}")
            time.sleep(DELAY)

    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} Q&A entries to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
