import urllib.parse
import feedparser
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# ⏱ 한국 시간대 기준 (표시용)
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

# 전역 변수로 API 키 저장
api_key = None

def set_api_key(key):
    global api_key
    api_key = key

def translate_to_english(korean_keyword: str) -> str:
    """
    GPT를 사용해 한국어 키워드를 영어로 번역 (한두 단어, 설명 없이)
    """
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        return korean_keyword

    client = OpenAI(api_key=api_key)

    prompt = f"Translate the Korean phrase to a concise English keyword (1~2 words, no explanation): {korean_keyword}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only short English keywords."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ 번역 실패: {e}")
        return korean_keyword

def parse_date(entry):
    date_str = entry.get("published") or entry.get("updated") or entry.get("dc_date")
    if not date_str:
        print("❌ 날짜 정보 없음:", entry.get("title", "제목 없음"))
        return None

    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z").astimezone(KST)
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).astimezone(KST)
        except ValueError:
            print("❌ 날짜 파싱 실패:", date_str)
            return None

def get_rss_news(keyword: str):
    """
    Google News RSS (국내 + 국외)에서 수집
    한국어 키워드는 자동 번역하여 국외 검색에 사용
    """
    encoded_kr = urllib.parse.quote(keyword)

    if any('\uac00' <= ch <= '\ud7a3' for ch in keyword):
        translated = translate_to_english(keyword)
    else:
        translated = keyword
    encoded_en = urllib.parse.quote(translated)

    rss_urls = {
        "국내": f"https://news.google.com/rss/search?hl=ko&gl=KR&ceid=KR:ko&q={encoded_kr}+when:24h",
        "국외": f"https://news.google.com/rss/search?hl=en&gl=US&ceid=US:en&q={encoded_en}+when:24h"
    }

    all_articles = []
    idx = 1

    for region, url in rss_urls.items():
        print(f"\n🌐 {region} RSS URL: {url}")
        feed = feedparser.parse(url)
        print(f"📦 수집된 기사 수: {len(feed.entries)}")

        for entry in feed.entries:
            pub_date = parse_date(entry)
            pub_date_str = pub_date.strftime("%Y-%m-%d %H:%M:%S") if pub_date else "날짜 없음"
            title = entry.get("title", "제목 없음").strip()
            link = entry.get("link", "링크 없음").strip()
            description = entry.get("description", "요약 없음").strip()

            # print(f"✅ [{idx}] {title} ({region})")
            # print(f"    📅 {pub_date_str}")
            # print(f"    🔗 {link}")
            # print(f"    📝 요약: {description}\n")

            all_articles.append([title, link, description, pub_date_str])
            idx += 1

    print(encoded_en)
    return all_articles

# 테스트용 실행
if __name__ == "__main__":
    get_rss_news("디지털 헬스케어")
