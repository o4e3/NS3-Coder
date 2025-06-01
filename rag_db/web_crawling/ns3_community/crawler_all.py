from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tempfile, shutil, time, json, re

# ─── 1. Chrome Headless 설정 ───────────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
tmp_dir = tempfile.mkdtemp(prefix="sel-")
options.add_argument(f"--user-data-dir={tmp_dir}")

driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)


# ─── 2. 유틸 함수 ───────────────────────────────────────────────────────────

def extract_text(sec):
    """질문/답변 섹션에서 텍스트만 깔끔히 뽑아내기"""
    try:
        txt = sec.find_element(By.CSS_SELECTOR, "div[role='region']").text
    except:
        txt = sec.text
    return re.sub(r"\s+", " ", txt).strip()

def has_content_image(sec):
    """Google-Groups 내부이미지(‘groups/’ 포함)가 있으면 True"""
    for img in sec.find_elements(By.TAG_NAME, "img"):
        src = img.get_attribute("src") or ""
        if img.is_displayed() and "groups/" in src:
            return True
    return False


# ─── 3. 모든 스레드 링크 수집 (무한 스크롤) ────────────────────────────────────

def collect_all_threads(base_url):
    driver.get(base_url)
    time.sleep(2)  # 초기 로딩 대기

    thread_sel = "a[href*='/g/ns-3-users/c/']"
    links = set()
    prev_count = 0

    # 1) 스크롤 컨테이너 탐색 (jsname="scroll")
    try:
        scroll_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[jsname='scroll']"))
        )
        use_container = True
    except TimeoutException:
        scroll_box = None
        use_container = False

    # 2) 무한 스크롤 루프
    while True:
        # 현재 화면의 링크 수집
        for a in driver.find_elements(By.CSS_SELECTOR, thread_sel):
            href = a.get_attribute("href")
            if href:
                links.add(href)

        # 더 이상 늘지 않으면 종료
        if len(links) == prev_count:
            break
        prev_count = len(links)

        # 3) 스크롤: 컨테이너 vs 전체 윈도우
        if use_container:
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", 
                scroll_box
            )
        else:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 4) 새 로드 대기
        time.sleep(2)

    return list(links)


# ─── 4. 각 스레드 파싱 (질문 + Tommaso 답변) ─────────────────────────────────

def parse_thread(url):
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section[data-author]"))
    )
    secs = driver.find_elements(By.CSS_SELECTOR, "section[data-author]")
    if len(secs) < 2:
        print("❌ 답변 없음:", url)
        return None

    q, *rest = secs
    tom = next((s for s in rest if s.get_attribute("data-author") == "Tommaso Pecorella"), None)
    if not tom:
        print("❌ Tommaso 답변 없음:", url)
        return None

    if has_content_image(q) or has_content_image(tom):
        print("🖼️ 이미지 포함 → 제외:", url)
        return None

    question = extract_text(q)
    answer   = extract_text(tom)
    if not answer:
        print("⚠️ 답변 비어 있음:", url)
        return None

    print("✅ 수집 OK:", url)
    return {"url": url, "question": question, "answer": answer}


# ─── 5. 메인 실행부 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    BASE = "https://groups.google.com/g/ns-3-users"
    print("🔍 스레드 링크 전수 수집 중…")
    threads = collect_all_threads(BASE)
    print(f"➡️ 총 스레드 링크: {len(threads)}개 확보")

    results = []
    for u in threads:
        qa = parse_thread(u)
        if qa:
            results.append(qa)

    # 결과 저장
    with open("tommaso_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"📦 완료: 총 {len(results)}개 QA 수집됨")

    driver.quit()
    shutil.rmtree(tmp_dir)
