import trafilatura
import json

urls = [
    "https://n.news.naver.com/mnews/article/030/0003371870?sid=102", # 전자신문 (Naver)
    "https://www.news1.kr/bio/welfare-medical/5981328", # 뉴스1
    "https://www.chosun.com/national/national_general/2023/01/01/EXAMPLE", # 조선일보 (Mock)
]

for url in urls:
    print(f"Fetching {url}...")
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        result = trafilatura.extract(downloaded, output_format="json", with_metadata=True)
        if result:
            data = json.loads(result)
            print(f"--- {url} ---")
            print(f"Sitename: {data.get('sitename')}")
            print(f"Author: {data.get('author')}")
            print(f"Hostname: {data.get('hostname')}")
            print(f"Title: {data.get('title')}")
