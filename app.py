import streamlit as st
import pandas as pd
from core import fetcher_naver, processor, ai_optimizer
import time

# 1. Page Config (Must be first)
st.set_page_config(page_title="나는 스크랩이 하고 싶다", layout="wide")

# 2. Sidebar: Settings
with st.sidebar:
    st.header("⚙️ 설정")
    
    with st.expander("Naver API 설정", expanded=True):
        naver_client_id = st.text_input("Client ID", value="JdKosGRYkm1y2cDwiUrl", type="password")
        naver_client_secret = st.text_input("Client Secret", value="7B4eLHFpQv", type="password")
        
        if st.button("API 키 저장"):
            fetcher_naver.set_api_keys(naver_client_id, naver_client_secret)
            st.success("API 키가 설정되었습니다!")
            
    st.divider()
    
    # 검색 기간 설정
    search_days = st.slider("검색 기간 (일)", min_value=1, max_value=7, value=1, help="최근 N일간의 뉴스를 검색합니다.")
    
    st.markdown("### ℹ️ About")
    st.markdown("뉴스 스크랩 및 보고서 자동화 도구입니다.")

# 3. Helper Functions
def process_news(keyword_sort_map, mode="business", days=1):
    all_news = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_keywords = len(keyword_sort_map)
    
    for i, (keyword, sort_option) in enumerate(keyword_sort_map.items()):
        status_text.text(f"🔍 '{keyword}' 검색 중... ({sort_option}) ({i+1}/{total_keywords})")
        news = fetcher_naver.get_naver_news(keyword, sort=sort_option, days=days)
        all_news.extend(news)
        progress_bar.progress((i + 1) / total_keywords)
        
    status_text.text("🧹 데이터 정제 및 중복 제거 중...")
    unique_news = processor.deduplicate(all_news)
    
    status_text.text("🌐 본문 분석 및 메타데이터 추출 중 (Trafilatura)...")
    enriched_news = processor.enrich_content(unique_news)
    
    status_text.text("📊 언론사 티어 정렬 중...")
    sorted_news = processor.sort_by_tier(enriched_news)
    
    if mode == "business":
        status_text.text("🏷️ 핵심 인물 태깅 중...")
        final_news = processor.tag_entities(sorted_news)
    else:
        final_news = sorted_news
        
    progress_bar.empty()
    status_text.empty()
    
    return final_news

def generate_report_text(categorized_news):
    report = ""
    for category, news_list in categorized_news.items():
        if not news_list:
            continue
        report += f"[{category}]\n"
        for news in news_list:
            source = news.get('source') or "알수없음"
            # 제목에 이미 태깅이 되어있음 (processor.tag_entities)
            title = news['title']
            link = news['link']
            report += f"({source}) {title}\n"
            report += f"{link}\n"
        report += "\n"
    return report

# 4. Main UI
st.title("📰 나는 스크랩이 하고 싶다")

tab1, tab2 = st.tabs(["🏢 업무 모드", "👤 개인 모드"])

# --- Tab 1: Business Mode ---
with tab1:
    st.header("🏢 업무용 뉴스 모니터링")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        main_org = st.text_input("본원 (Main Organization)", value="강북삼성병원")
    with col2:
        industry = st.text_input("의료 (Industry)", value="병원, 의료, 전공의, PA간호사")
    with col3:
        affiliates = st.text_input("관계사 (Affiliates)", value="삼성전자, 삼성바이오")
        
    if st.button("🚀 스크랩 시작", key="btn_biz"):
        categorized_results = {}
        
        with st.spinner("뉴스 수집 및 분석 중입니다..."):
            # 1. 본원 (Main Org) - 최신순
            if main_org:
                st.info(f"🏢 [본원] '{main_org}' 처리 중...")
                categorized_results["본원"] = process_news({main_org: 'date'}, mode="business", days=search_days)
            
            # 2. 의료 (Industry) - 관련도순
            if industry:
                st.info(f"🏥 [의료] 카테고리 처리 중...")
                ind_map = {k.strip(): 'sim' for k in industry.split(',')}
                categorized_results["의료"] = process_news(ind_map, mode="business", days=search_days)
                
            # 3. 관계사 (Affiliates) - 관련도순
            if affiliates:
                st.info(f"🤝 [관계사] 카테고리 처리 중...")
                aff_map = {k.strip(): 'sim' for k in affiliates.split(',')}
                categorized_results["관계사"] = process_news(aff_map, mode="business", days=search_days)
        
        if categorized_results:
            st.session_state['biz_results'] = categorized_results
            st.success("모든 작업이 완료되었습니다!")
        else:
            st.warning("검색 결과가 없습니다.")

    # 결과 표시 및 AI 최적화 (Session State 사용)
    if 'biz_results' in st.session_state:
        categorized_results = st.session_state['biz_results']
        
        # AI 최적화 섹션
        st.divider()
        st.subheader("✨ AI 결과 최적화")
        
        with st.expander("AI 설정 및 실행", expanded=True):
            st.info("""
            **AI 최적화 기능이란?**
            - **중복 제거**: 내용이 유사한 기사를 AI가 판단하여 중복을 제거합니다.
            - **언론사명 보정**: 'weekly.hankooki.com' 같은 URL 형태의 출처를 '주간한국' 같은 한글 언론사명으로 변환합니다.
            """)
            
            ai_provider = st.radio("AI 모델 선택", ["OpenAI (GPT-4o)", "Google Vertex AI (Gemini)"])
            
            ai_api_key = None
            vertex_json = None
            
            if ai_provider == "OpenAI (GPT-4o)":
                ai_api_key = st.text_input("OpenAI API Key", type="password", help="sk-...")
            else:
                uploaded_file = st.file_uploader("Google Service Account JSON 업로드", type="json")
                if uploaded_file:
                    import json
                    vertex_json = json.load(uploaded_file)
            
            if st.button("최적화 시작"):
                if ai_provider == "OpenAI (GPT-4o)" and not ai_api_key:
                    st.error("OpenAI API Key를 입력해주세요.")
                elif ai_provider == "Google Vertex AI (Gemini)" and not vertex_json:
                    st.error("Service Account JSON 파일을 업로드해주세요.")
                else:
                    with st.spinner("AI가 뉴스를 분석하고 있습니다... (중복 제거 및 언론사명 보정)"):
                        optimized_results = {}
                        for cat, news_list in categorized_results.items():
                            if ai_provider == "OpenAI (GPT-4o)":
                                optimized_results[cat] = ai_optimizer.optimize_news_openai(news_list, ai_api_key)
                            else:
                                optimized_results[cat] = ai_optimizer.optimize_news_vertex(news_list, vertex_json)
                        
                        st.session_state['biz_results'] = optimized_results
                        st.success("최적화 완료! 결과가 업데이트되었습니다.")
                        st.rerun()

        # 결과 표시
        report_text = generate_report_text(categorized_results)
        st.text_area("📋 보고용 텍스트 (복사해서 사용하세요)", value=report_text, height=500)
        
        # 상세 리스트 표시
        res_tabs = st.tabs(list(categorized_results.keys()))
        for idx, (cat, news_list) in enumerate(categorized_results.items()):
            with res_tabs[idx]:
                for news in news_list:
                    with st.expander(f"[{news.get('source', '기타')}] {news['title']}"):
                        st.markdown(f"**링크:** {news['link']}")
                        st.markdown(f"**일시:** {news['pub_date']}")
                        st.markdown(f"**요약:** {news['description']}")
                        if news.get('full_text'):
                            st.caption(news['full_text'][:200] + "...")

# --- Tab 2: Personal Mode ---
with tab2:
    st.header("👤 개인용 뉴스 검색")
    
    search_query = st.text_input("검색어 입력", placeholder="예: 인공지능, 반도체")
    
    if st.button("🔍 검색", key="btn_personal"):
        if search_query:
            with st.spinner("뉴스 검색 중..."):
                results = process_news({search_query: 'sim'}, mode="personal", days=search_days)
                
            if results:
                st.success(f"총 {len(results)}건의 뉴스가 검색되었습니다.")
                
                report_text = generate_report_text({"검색 결과": results})
                st.text_area("📋 텍스트 복사", value=report_text, height=200)
                
                for news in results:
                    st.markdown(f"### [{news.get('source', '기타')}] [{news['title']}]({news['link']})")
                    st.caption(f"{news['pub_date']} | {news['description']}")
                    st.divider()
        else:
            st.warning("검색어를 입력해주세요.")
