import re
import textwrap
import unicodedata
import os
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# 유니코드 정규화: 특수 문자 → 일반 문자
def normalize_text(text):
    return unicodedata.normalize('NFKC', text)

# 불필요한 줄 제거 규칙
def is_useless_line(line):
    line = line.strip()
    if re.search(r"\s+\d{1,3}$", line):
        return True
    return (
        re.match(r"^(one|two|three|four|five|six|seven|eight|nine|ten)\b", line.lower()) or
        re.match(r"^\d+(\.\d+)+\s+[A-Z].*", line) or
        line.isupper() and len(line.split()) <= 3 or
        line.lower().startswith("fig.") or
        line.lower().startswith("table") or
        "ns-3 model library" in line.lower() or
        "chapter" in line.lower() or
        "contents" in line.lower() or
        re.match(r"^\s*\d+\s*$", line) or
        re.match(r"^\s*sep\s+\d{1,2},\s+\d{4}\s*$", line.lower())
    )

# 단일 PDF 처리 함수
def clean_pdf(input_path, output_path):
    reader = PdfReader(input_path)
    cleaned_lines = []

    for i, page in enumerate(reader.pages):
        if i < 6:
            continue
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            cleaned = [
                normalize_text(line.strip())
                for line in lines
                if line.strip() and not is_useless_line(line)
            ]
            cleaned_lines.extend(cleaned + [""])

    # 새 PDF 파일로 작성
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    x_margin, y_margin = 40, 40
    y = height - y_margin
    c.setFont("Helvetica", 11)

    for line in cleaned_lines:
        wrapped_lines = textwrap.wrap(line, width=100)
        for wline in wrapped_lines:
            if y < y_margin:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - y_margin
            c.drawString(x_margin, y, wline)
            y -= 15

    c.save()
    print(f"Cleaning completed: {output_path}")

# 폴더 전체 처리
input_dir = "/home/gpuadmin/ns3coder/psh/ns3.40_docs"
cleaned_dir = input_dir + "_cleaned"
os.makedirs(cleaned_dir, exist_ok=True)

# 모든 PDF 파일에 대해 반복 처리
for file in os.listdir(input_dir):
    if file.lower().endswith(".pdf"):
        input_path = os.path.join(input_dir, file)

        # 파일명 분리해서 _cleaned 붙이기
        name, ext = os.path.splitext(file)
        cleaned_filename = name + "_cleaned" + ext
        output_path = os.path.join(cleaned_dir, cleaned_filename)

        # PDF 정제 실행
        clean_pdf(input_path, output_path)