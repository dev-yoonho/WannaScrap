# gpt_filter.py
from openai import OpenAI

# 전역 변수로 API 키 저장
api_key = None

def set_api_key(key):
    global api_key
    api_key = key

def filtering(keyword, news_list):
    if not api_key:
        raise ValueError("API 키가 설정되지 않았습니다. 먼저 set_api_key(key)를 호출하세요.")

    client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content":
                """
                너는 입력된 뉴스 기사 리스트가 특정 키워드 또는 기업과 관련 있는지를 판단하는 AI 조수야.
                관련도는 최상, 상, 중, 하, 최하 중 하나로 판단하고 리스트만 출력해.
                예시: [[1, "상"], [2, "하"], [3, "중"]]
                """
             },
            {"role": "user", "content":
                f"""
                키워드: {keyword}

                뉴스 목록:
                {news_list}

                출력은 반드시 한 줄 리스트로만 해:
                [[1, "상"], [2, "하"], [3, "중"], [4, "최상"], [5, "최하"]]
                """
             }
        ]
    )
    return completion.choices[0].message.content
