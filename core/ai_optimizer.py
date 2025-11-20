import json
from openai import OpenAI

def optimize_news_openai(news_list, api_key):
    """
    OpenAI API를 사용하여 뉴스 리스트를 최적화합니다.
    1. 중복 제거 (의미적 중복)
    2. 언론사 이름 보정 (URL -> 한글명)
    """
    if not news_list:
        return []

    client = OpenAI(api_key=api_key)

    # 프롬프트 구성을 위한 데이터 준비 (ID 부여)
    news_data_str = ""
    for i, news in enumerate(news_list):
        news_data_str += f"ID:{i} | Source:{news.get('source')} | Title:{news.get('title')} | Link:{news.get('link')}\n"

    prompt = f"""
    You are a helpful assistant that optimizes a list of news articles.
    
    Task:
    1. Identify duplicates. If multiple articles cover the exact same topic with very similar titles, mark them as duplicates. Keep the one with the most recognizable Source name.
    2. Correct the 'Source' field. If the Source looks like a URL (e.g., 'weekly.hankooki.com') or is missing, convert it to the proper Korean press name (e.g., '주간한국'). If it's already correct, keep it.
    
    Input Data:
    {news_data_str}
    
    Output Format:
    Return ONLY a JSON list of objects. Each object must have:
    - "id": (integer) The ID from the input.
    - "is_duplicate": (boolean) True if it should be removed.
    - "corrected_source": (string) The corrected Korean press name.
    
    Example Output:
    [
        {{"id": 0, "is_duplicate": false, "corrected_source": "조선일보"}},
        {{"id": 1, "is_duplicate": true, "corrected_source": "매일경제"}}
    ]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data processing assistant. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # result_json이 {"items": [...]} 형태일 수도 있고 바로 리스트일 수도 있음.
        # gpt-4o json_object 모드는 보통 root object를 요구하므로 {"results": [...]} 형태로 유도하거나 파싱 확인 필요.
        # 여기서는 유연하게 처리.
        
        if isinstance(result_json, dict):
            # 키가 하나라면 그 값을 사용 (예: {"articles": [...]})
            values = list(result_json.values())
            if values and isinstance(values[0], list):
                optimization_results = values[0]
            else:
                # 실패 시 원본 반환
                print("Error: Unexpected JSON structure")
                return news_list
        elif isinstance(result_json, list):
            optimization_results = result_json
        else:
            return news_list

        # 결과 적용
        optimized_list = []
        result_map = {item['id']: item for item in optimization_results}
        
        for i, news in enumerate(news_list):
            res = result_map.get(i)
            if res:
                if res.get('is_duplicate'):
                    continue
                
                # 소스 업데이트
                if res.get('corrected_source'):
                    news['source'] = res['corrected_source']
            
            optimized_list.append(news)
            
        return optimized_list

    except Exception as e:
        print(f"AI Optimization Error: {e}")
        return news_list

def optimize_news_vertex(news_list, json_content):
    """
    Google Vertex AI (Gemini)를 사용하여 뉴스 리스트를 최적화합니다.
    Service Account JSON을 사용하여 인증합니다.
    """
    if not news_list:
        return []

    try:
        from google.oauth2 import service_account
        import vertexai
        from vertexai.generative_models import GenerativeModel
        import json
        import tempfile
        import os

        # JSON 내용을 임시 파일로 저장 (google.oauth2가 파일 경로를 선호하는 경우가 많음, 
        # 혹은 from_service_account_info 사용 가능)
        
        # 문자열이면 JSON 파싱
        if isinstance(json_content, str):
            credentials_info = json.loads(json_content)
        else:
            credentials_info = json_content # 이미 dict라고 가정 (st.file_uploader에서 json.load 함)

        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        project_id = credentials_info.get("project_id")
        
        vertexai.init(project=project_id, location="us-central1", credentials=credentials)
        
        model = GenerativeModel("gemini-pro")

        # 프롬프트 구성
        news_data_str = ""
        for i, news in enumerate(news_list):
            news_data_str += f"ID:{i} | Source:{news.get('source')} | Title:{news.get('title')} | Link:{news.get('link')}\n"

        prompt = f"""
        You are a helpful assistant that optimizes a list of news articles.
        
        Task:
        1. Identify duplicates. If multiple articles cover the exact same topic with very similar titles, mark them as duplicates. Keep the one with the most recognizable Source name.
        2. Correct the 'Source' field. If the Source looks like a URL (e.g., 'weekly.hankooki.com') or is missing, convert it to the proper Korean press name (e.g., '주간한국'). If it's already correct, keep it.
        
        Input Data:
        {news_data_str}
        
        Output Format:
        Return ONLY a JSON list of objects. Each object must have:
        - "id": (integer) The ID from the input.
        - "is_duplicate": (boolean) True if it should be removed.
        - "corrected_source": (string) The corrected Korean press name.
        
        Example Output:
        [
            {{"id": 0, "is_duplicate": false, "corrected_source": "조선일보"}},
            {{"id": 1, "is_duplicate": true, "corrected_source": "매일경제"}}
        ]
        """
        
        response = model.generate_content(prompt)
        result_text = response.text
        
        # Markdown code block 제거 (```json ... ```)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
            
        result_json = json.loads(result_text)
        
        # 결과 적용 (OpenAI 로직과 동일)
        if isinstance(result_json, dict):
            values = list(result_json.values())
            if values and isinstance(values[0], list):
                optimization_results = values[0]
            else:
                return news_list
        elif isinstance(result_json, list):
            optimization_results = result_json
        else:
            return news_list

        optimized_list = []
        result_map = {item['id']: item for item in optimization_results}
        
        for i, news in enumerate(news_list):
            res = result_map.get(i)
            if res:
                if res.get('is_duplicate'):
                    continue
                if res.get('corrected_source'):
                    news['source'] = res['corrected_source']
            
            optimized_list.append(news)
            
        return optimized_list

    except Exception as e:
        print(f"Vertex AI Optimization Error: {e}")
        return news_list
