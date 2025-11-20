import trafilatura
from concurrent.futures import ThreadPoolExecutor
import re
from urllib.parse import urlparse

# 언론사 티어 정의
MEDIA_TIERS = {
    "1순위": ["KBS", "SBS", "MBC"],
    "2순위": ["조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "한국일보", "매일경제", "한국경제", "서울경제"],
    "3순위": ["연합뉴스", "뉴스1", "뉴시스"],
    "4순위": ["머니투데이", "아시아경제", "헬스조선", "연합뉴스TV", "한국경제TV"],
    "5순위": ["데일리메디", "메디칼타임즈", "코메디닷컴", "의학신문"],
}

# 도메인 -> 언론사명 매핑
DOMAIN_TO_PRESS = {
    "news1.kr": "뉴스1",
    "newsis.com": "뉴시스",
    "chosun.com": "조선일보",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "hankookilbo.com": "한국일보",
    "mk.co.kr": "매일경제",
    "hankyung.com": "한국경제",
    "sedaily.com": "서울경제",
    "mt.co.kr": "머니투데이",
    "asiae.co.kr": "아시아경제",
    "health.chosun.com": "헬스조선",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "wowtv.co.kr": "한국경제TV",
    "dailymedi.com": "데일리메디",
    "medicaltimes.com": "메디칼타임즈",
    "kormedi.com": "코메디닷컴",
    "bosa.co.kr": "의학신문",
    "yna.co.kr": "연합뉴스",
    "kbs.co.kr": "KBS",
    "imbc.com": "MBC",
    "sbs.co.kr": "SBS",
    "womaneconomy.co.kr": "여성경제신문",
    "etnews.com": "전자신문",
    "zdnet.co.kr": "지디넷코리아",
    "biz.chosun.com": "조선비즈",
}

def get_tier(press_name):
    for tier, media_list in MEDIA_TIERS.items():
        if any(media in press_name for media in media_list):
            return int(tier[0]) # "1순위" -> 1
    return 6 # 기타

def deduplicate(news_list):
    """제목이 100% 일치하는 중복 기사 제거"""
    seen_titles = set()
    unique_news = []
    for news in news_list:
        if news['title'] not in seen_titles:
            seen_titles.add(news['title'])
            unique_news.append(news)
    return unique_news

def fetch_content(news_item):
    """trafilatura를 사용하여 본문 및 메타데이터 추출"""
    try:
        downloaded = trafilatura.fetch_url(news_item['link'])
        if downloaded:
            result = trafilatura.extract(downloaded, output_format="json", with_metadata=True)
            if result:
                import json
                data = json.loads(result)
                news_item['full_text'] = data.get('text', '')
                
                # 1. sitename 확인
                source = data.get('sitename')
                
                # 2. author 확인 (네이버 뉴스의 경우 "언론사; 네이버" 형태)
                if not source and data.get('author'):
                    author = data.get('author')
                    if ';' in author:
                        source = author.split(';')[0].strip()
                    else:
                        # 기자가 아닌 언론사 이름일 수도 있으므로 체크
                        pass 

                news_item['source'] = source or news_item['source']
    except Exception as e:
        print(f"Error fetching {news_item['link']}: {e}")
    
    # 3. 도메인 매핑 확인 (Source가 없거나 영어인 경우)
    current_source = news_item.get('source', '')
    
    # 도메인 추출
    try:
        parsed_url = urlparse(news_item['link'])
        domain = parsed_url.netloc.replace('www.', '')
        
        # 매핑된 도메인이면 덮어쓰기 (우선순위 높음)
        # 서브도메인 처리 (예: biz.chosun.com)
        if domain in DOMAIN_TO_PRESS:
            news_item['source'] = DOMAIN_TO_PRESS[domain]
        else:
            # 매핑이 안된 경우, 기존 source가 없으면 도메인 사용
            if not current_source or current_source == "Unknown":
                news_item['source'] = domain
            # 기존 source가 있으면 유지 (trafilatura가 찾은 것)
            
    except:
        if not current_source:
            news_item['source'] = "Unknown"
            
    news_item['full_text'] = news_item.get('full_text', "")
    return news_item

def enrich_content(news_list, max_workers=5):
    """병렬로 기사 본문 및 메타데이터 수집"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 뉴스 리스트의 각 항목을 업데이트
        news_list = list(executor.map(fetch_content, news_list))
    return news_list

def sort_by_tier(news_list):
    """티어 기반 정렬 (티어 오름차순 -> 날짜 내림차순)"""
    # 먼저 티어 계산
    for news in news_list:
        # source가 비어있으면 링크나 제목에서 추측해야 할 수도 있음. 
        # 일단 enrich_content를 통해 source가 채워졌다고 가정하거나, 
        # 네이버 API 결과에는 source가 없으므로 별도 처리가 필요할 수 있음.
        # 여기서는 enrich_content가 source를 채워준다고 가정.
        # 만약 source가 여전히 비어있다면 '기타'로 분류됨.
        news['tier'] = get_tier(news.get('source', ''))

    # 정렬: 티어(오름차순) -> 날짜(내림차순)
    # 날짜는 문자열 비교로도 충분 (YYYY-MM-DD HH:MM:SS 형식)
    return sorted(news_list, key=lambda x: (x['tier'], x['pub_date']), reverse=False) 
    # 주의: 날짜는 최신순(내림차순)이어야 하는데, 티어는 오름차순(1순위가 먼저).
    # 파이썬 sort는 안정적이므로 두 번 정렬하거나 key를 조정해야 함.
    # (tier, -timestamp) 형태로 하려면 timestamp 변환 필요.
    # 간단하게:
    # 1. 날짜 내림차순 정렬
    # 2. 티어 오름차순 정렬 (안정 정렬이므로 같은 티어 내에서는 날짜 순서 유지됨)
    
    news_list.sort(key=lambda x: x['pub_date'], reverse=True) # 최신순
    news_list.sort(key=lambda x: x['tier']) # 티어순 (1 -> 6)
    
    return news_list

def tag_entities(news_list):
    """본문/요약에서 주요 직급/인물 추출하여 제목에 태깅 (이름 포함)"""
    # 예시: 홍길동 교수, 김철수 센터장
    # 이름은 보통 2~4글자 한글
    target_roles = ["교수", "센터장", "병원장", "이사장", "원장", "연구원"]
    
    # Regex patterns:
    # 1. Name + Role (e.g., 홍길동 교수)
    # 2. Role + Name (e.g., 주치의 홍길동 - less common as a standalone title but possible)
    # We focus on "Name + Role" which is most common in news.
    # Also capture "Department + Name + Role" if possible, but keep it simple first.
    
    # Pattern: (Word 2-4 chars) + Space(optional) + Role
    role_pattern = "|".join(target_roles)
    # Look for: [Name] [Role]
    regex = re.compile(fr"([가-힣]{{2,4}})\s*({role_pattern})")
    
    for news in news_list:
        content = (news.get('description', '') + " " + news.get('full_text', '')).replace('\n', ' ')
        
        found_entities = []
        matches = regex.findall(content)
        
        for name, role in matches:
            # Filter out common false positives if needed (e.g., "대학교 교수" where "대학교" is not a name)
            # But 2-4 chars usually covers names well. 
            # "우리" "이번" etc could be matched, so maybe check length or specific blocklist if needed.
            if name not in ["우리", "이번", "지난", "다음", "어떤", "해당"]:
                found_entities.append(f"{name} {role}")
        
        if found_entities:
            # 중복 제거
            entities_str = ", ".join(sorted(list(set(found_entities))))
            news['title'] = f"{news['title']} ({entities_str})"
            
    return news_list
