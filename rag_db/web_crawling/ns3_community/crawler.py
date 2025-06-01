from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import shutil
import time
import json
import re

# 1. Chrome 옵션 설정
options = webdriver.ChromeOptions()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--headless=new")

# 2. 임시 user-data-dir 생성 (세션 격리)
temp_user_data_dir = tempfile.mkdtemp(prefix="selenium-profile-")
options.add_argument(f"--user-data-dir={temp_user_data_dir}")

# 3. ChromeDriver 실행
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# 4. 본문 텍스트만 추출 (이미지·링크 제거)
def extract_clean_text(element):
    for tag in element.find_elements(By.TAG_NAME, "img") + element.find_elements(By.TAG_NAME, "a"):
        driver.execute_script("arguments[0].remove();", tag)
    return element.text.strip()

# 5. 본문 이미지 여부 검사 (오직 /groups/ 경로의 이미지만)
def has_visible_content_images(element):
    imgs = element.find_elements(By.TAG_NAME, "img")
    for img in imgs:
        if not img.is_displayed():
            continue
        src = img.get_attribute("src") or ""
        if "groups/" in src:
            return True
    return False

# 6. 게시글 링크 수집
def collect_thread_links(start_url, max_pages=3):
    links = []
    driver.get(start_url)
    time.sleep(3)
    for _ in range(max_pages):
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='/g/ns-3-users/c/']"):
            href = a.get_attribute("href")
            if href and href not in links:
                links.append(href)
        try:
            nxt = driver.find_element(By.CSS_SELECTOR, "div[aria-label='다음 페이지']")
            driver.execute_script("arguments[0].click()", nxt)
            time.sleep(2)
        except:
            break
    return links

# 7. 질문-답변 파싱
def parse_thread(url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section[data-author]"))
        )
        secs = driver.find_elements(By.CSS_SELECTOR, "section[data-author]")
        if len(secs) < 2:
            print("❌ 답변 없음:", url)
            return None

        # 질문 본문만 추출 & clean
        q_sec = secs[0]
        try:
            q_region = q_sec.find_element(By.CSS_SELECTOR, "div[role='region']")
            raw_q = q_region.text
        except:
            raw_q = q_sec.text
        question = re.sub(r"\s+", " ", raw_q).strip()

        # Tommaso 섹션 찾기
        t_sec = next((s for s in secs[1:]
                      if s.get_attribute("data-author") == "Tommaso Pecorella"), None)
        if not t_sec:
            print("❌ Tommaso 답변 없음:", url)
            return None

        # 본문 이미지 포함 여부
        if has_visible_content_images(q_sec):
            print("🖼️ 질문 본문에 이미지 포함 → 제외:", url)
            return None
        if has_visible_content_images(t_sec):
            print("🖼️ Tommaso 답변 본문에 이미지 포함 → 제외:", url)
            return None

        # 답변 본문만 추출 & clean
        try:
            a_region = t_sec.find_element(By.CSS_SELECTOR, "div[role='region']")
            raw_a = a_region.text
        except:
            raw_a = t_sec.text
        answer = re.sub(r"\s+", " ", raw_a).strip()

        if not answer:
            print("⚠️ 답변 비어 있음:", url)
            return None

        print("✅ Tommaso 답변 수집:", url)
        return {
            "url": url,
            "question": question,
            "answer": answer
        }

    except Exception as e:
        print(f"⚠️ 페이지 로드 실패 ({url}): {e}")
    return None

# 8. 메인 실행 로직
if __name__ == "__main__":
    base_url = "https://groups.google.com/g/ns-3-users"
    threads = collect_thread_links(base_url, max_pages=3)

    results = []
    seen = set()
    for link in threads:
        if link in seen:
            continue
        seen.add(link)

        print(f"\n🔍 크롤링 중: {link}")
        qa = parse_thread(link)
        if qa:
            results.append(qa)

    with open("tommaso_qa.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📦 저장 완료: {len(results)}개 수집됨")

    driver.quit()
    shutil.rmtree(temp_user_data_dir, ignore_errors=True)
