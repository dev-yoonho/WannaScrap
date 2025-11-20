from datetime import datetime, timezone, timedelta
import json
import urllib.request
import urllib.parse


client_id = "JdKosGRYkm1y2cDwiUrl"
client_secret = "7B4eLHFpQv"

def set_api_keys(id, secret):
    global client_id, client_secret
    client_id = id
    client_secret = secret

def get_naver_news(keyword, sort='date', days=1):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news?query={encText}&display=60&sort={sort}"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    article_list = []

    if rescode == 200:
        response_body = response.read()
        data = json.loads(response_body.decode('utf-8'))

        # KST 기준 시간 설정
        KST = timezone(timedelta(hours=9))
        now = datetime.now(KST)
        cutoff_date = now - timedelta(days=days)

        def parse_pubdate(pubdate_str):
            # 문자열 → datetime 객체로 변환
            return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z").astimezone(KST)

        # 필터링
        data = [
            item for item in data['items']
            if parse_pubdate(item['pubDate']) >= cutoff_date
        ]

        # 기사 처리
        for idx, item in enumerate(data, start=1):
            title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            description = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            link = item['link']
            pubDate_dt = parse_pubdate(item['pubDate'])
            pubDate_str = pubDate_dt.strftime("%Y-%m-%d %H:%M:%S")

            article_list.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pubDate_str,
                "source": "", # To be filled by processor or advanced extraction
                "tier": 99    # Default tier
            })

    else:
        print("Error Code:" + str(rescode))

    return article_list

