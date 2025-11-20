# core/pdf_generator.py

import os
from fpdf import FPDF

# --- 설정: 필요에 따라 경로를 조정하세요 ---
BASE_DIR   = os.path.dirname(os.path.dirname(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "output")
FONT_PATH  = os.path.join(BASE_DIR, "asset/font", "GowunDodum-Regular.ttf")
# ---------------------------------------

def sanitize_text(text: str) -> str:
    """
    ASCII(0x20–0x7E), 완성형 한글(0xAC00–0xD7A3), 줄바꿈(\n)만 남기고
    나머지는 공백으로 교체합니다.
    """
    out = []
    for ch in text:
        code = ord(ch)
        if ch == "\n" or (0x20 <= code <= 0x7E) or (0xAC00 <= code <= 0xD7A3):
            out.append(ch)
        else:
            out.append(" ")
    return "".join(out)

class PDF(FPDF):
    def __init__(self, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.title = sanitize_text(title)
        self.set_auto_page_break(auto=True, margin=15)

        # 폰트 등록 (한 종류만 사용)
        if not os.path.isfile(FONT_PATH):
            raise FileNotFoundError(f"폰트를 찾을 수 없습니다: {FONT_PATH}")
        self.add_font("Gowun", "", FONT_PATH, uni=True)
        self.set_font("Gowun", size=14)

    def header(self):
        # 제목 헤더
        self.set_font("Gowun", size=16)
        self.cell(0, 10, f"뉴스 리포트 - {self.title}", ln=True, align="C")
        self.ln(5)

    def article(self, idx: int, title: str, date: str, source: str, link: str, body: str):
        # sanitize
        title  = sanitize_text(title)
        date   = sanitize_text(date)
        source = sanitize_text(source)
        link   = sanitize_text(link)
        body   = sanitize_text(body)

        # 1) 제목
        self.set_font("Gowun", size=12)
        self.multi_cell(0, 8, f"{idx}. {title}")

        # 2) 출처·날짜
        self.set_font("Gowun", size=10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"[출처] {source}    [날짜] {date}", ln=True)
        self.set_text_color(0, 0, 0)

        # 3) 링크 (파란색)
        if link.strip():
            self.set_text_color(0, 0, 255)
            self.multi_cell(0, 6, link)
            self.set_text_color(0, 0, 0)

        # 4) 본문
        self.set_font("Gowun", size=11)
        self.multi_cell(0, 6, body)
        self.ln(4)

def generate_pdf(articles: list, keyword: str) -> str:
    """
    articles: [{title, pub_date, source, link, body}, ...]
    keyword:   PDF 헤더에 들어갈 키워드
    """
    os.makedirs(REPORT_DIR, exist_ok=True)

    pdf = PDF(title=keyword)
    pdf.add_page()

    for i, art in enumerate(articles, start=1):
        pdf.article(
            idx     = i,
            title   = art.get("title", ""),
            date    = art.get("pub_date", ""),
            source  = art.get("source", ""),
            link    = art.get("link", ""),
            body    = art.get("body", "")
        )

    # 파일명에 키워드가 안전하게 들어가도록 알파벳/숫자만 남김
    safe_kw = "".join(ch for ch in keyword if ch.isalnum()) or "report"
    out_path = os.path.join(REPORT_DIR, f"news_report_{safe_kw}.pdf")

    pdf.output(out_path)
    return out_path
