#!/usr/bin/env python3
import os
import json
import base64
import requests

# ─────────────────────────────────────────────────────────────────────────────
# ⚙️ 설정
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN", "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")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept":        "application/vnd.github.v3+json"
}

# NS-3 코드 여부 판단 키워드
NS3_KEYWORDS = [
    '#include "ns3/',
    "using namespace ns3",
    "NodeContainer",
    "NetDeviceContainer",
    "Ipv4AddressHelper",
    "PointToPointHelper",
    "Simulator::Run"
]


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 1) NS-3 코드 필터 함수
# ─────────────────────────────────────────────────────────────────────────────
def is_valid_ns3_code(code_text: str) -> bool:
    return any(kw in code_text for kw in NS3_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 2) GitHub에서 인기 저장소 자동 검색
# ─────────────────────────────────────────────────────────────────────────────
def search_repositories(queries, max_pages=2):
    seen = {}
    for q in queries:
        for page in range(1, max_pages + 1):
            url = f"{GITHUB_API}/search/repositories"
            params = {
                "q":       f"{q} in:name,description",
                "sort":    "stars",
                "order":   "desc",
                "page":    page,
                "per_page": 30
            }
            res = requests.get(url, headers=HEADERS, params=params)
            if res.status_code != 200:
                print("Error fetching repos:", res.status_code, res.text)
                break
            for repo in res.json().get("items", []):
                full = repo["full_name"]
                if full not in seen:
                    seen[full] = (repo["owner"]["login"], repo["name"])
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# 🔄 3) 저장소의 default branch 조회
# ─────────────────────────────────────────────────────────────────────────────
def get_default_branch(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get("default_branch", "main")
    return "main"


# ─────────────────────────────────────────────────────────────────────────────
# 📂 4) 리포지토리 전체 파일 트리 조회 (recursive)
# ─────────────────────────────────────────────────────────────────────────────
def list_all_files(owner: str, repo: str, branch: str):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}"
    params = {"recursive": "1"}
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        return []
    tree = res.json().get("tree", [])
    return [item["path"] for item in tree if item["type"] == "blob"]


# ─────────────────────────────────────────────────────────────────────────────
# 🔖 5) 코드 파일만 필터 (.cc/.cpp/.py)
# ─────────────────────────────────────────────────────────────────────────────
def filter_code_files(file_paths):
    exts = (".cc", ".cpp", ".py")
    return [p for p in file_paths if p.lower().endswith(exts)]


# ─────────────────────────────────────────────────────────────────────────────
# 📄 6) 파일 내용 가져오기 (base64 디코딩)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_file_content(owner: str, repo: str, path: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    content = res.json().get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="ignore")


# ─────────────────────────────────────────────────────────────────────────────
# 📄 7) README 수집
# ─────────────────────────────────────────────────────────────────────────────
def get_readme(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    content = res.json().get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="ignore")


# ─────────────────────────────────────────────────────────────────────────────
# 🏗️ 8) 저장소 단위 JSON 빌드
# ─────────────────────────────────────────────────────────────────────────────
def build_repo_json(owner: str, repo: str):
    # 브랜치 결정
    branch = get_default_branch(owner, repo)
    # 전체 파일 조회 → 코드 파일 필터
    all_files = list_all_files(owner, repo, branch)
    code_files = filter_code_files(all_files)

    # 실제 NS-3 키워드 포함 파일만 examples로 수집
    examples = []
    for path in code_files:
        content = fetch_file_content(owner, repo, path)
        if is_valid_ns3_code(content):
            examples.append({
                "file_path": path,
                "code":      content
            })

    # NS-3 코드가 하나도 없으면 스킵
    if not examples:
        print(f"🚫 Skipped non-NS3 repo: {owner}/{repo}")
        return None

    return {
        "repo_name":  f"{owner}/{repo}",
        "github_url": f"https://github.com/{owner}/{repo}",
        "readme":     get_readme(owner, repo),
        "examples":   examples
    }


# ─────────────────────────────────────────────────────────────────────────────
# ▶️ 9) 메인 실행부
# ─────────────────────────────────────────────────────────────────────────────
def main():
    queries = ["ns-3", "ns3", "ns3 simulation", "ns-3 example"]
    repos   = search_repositories(queries)

    output_dir = "./repo_jsons"
    os.makedirs(output_dir, exist_ok=True)

    for full_name, (owner, name) in repos.items():
        print(f"📦 Processing {full_name}")
        repo_json = build_repo_json(owner, name)
        if repo_json:
            out_path = os.path.join(output_dir, f"{owner}_{name}.json")
            with open(out_path, "w") as f:
                json.dump(repo_json, f, indent=2)
            print(f"✅ Saved: {out_path}")

if __name__ == "__main__":
    main()
