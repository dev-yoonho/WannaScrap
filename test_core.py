import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import fetcher_naver, processor
import time

def test_logic():
    print("1. Testing Naver Fetcher (Sort='sim', Days=3)...")
    # Test with a simple keyword and sort param
    news = fetcher_naver.get_naver_news("인공지능", sort='sim', days=3)
    print(f"   Fetched {len(news)} items.")
    if not news:
        print("   ❌ No news fetched. Check API keys or network.")
        return

    print("\n2. Testing Deduplication...")
    # Artificially add a duplicate
    news.append(news[0].copy())
    deduped = processor.deduplicate(news)
    print(f"   Original: {len(news)}, Deduplicated: {len(deduped)}")
    if len(deduped) != len(news) - 1:
        print("   ❌ Deduplication failed.")
    else:
        print("   ✅ Deduplication working.")

    print("\n3. Testing Enrichment (Trafilatura & Source Fallback)...")
    # Test only top 3 to save time
    sample = deduped[:3]
    enriched = processor.enrich_content(sample)
    for item in enriched:
        print(f"   - [{item.get('source', 'Unknown')}] {item['title'][:30]}...")
        print(f"     Full text length: {len(item.get('full_text', ''))}")
        if item.get('source') and item.get('source') != "Unknown":
             print("     ✅ Source extracted.")
        else:
             print("     ⚠️ Source might be missing or Unknown.")
    
    print("\n4. Testing Tier Sorting...")
    # Mock some data for sorting test
    mock_news = [
        {"title": "C", "pub_date": "2023-01-01 10:00:00", "source": "Unknown", "tier": 6},
        {"title": "A", "pub_date": "2023-01-01 12:00:00", "source": "KBS", "tier": 1},
        {"title": "B", "pub_date": "2023-01-01 11:00:00", "source": "조선일보", "tier": 2},
    ]
    sorted_news = processor.sort_by_tier(mock_news)
    print("   Sorted Order (Should be KBS -> 조선일보 -> Unknown):")
    for item in sorted_news:
        print(f"   - {item['source']} ({item['tier']}) - {item['pub_date']}")
    
    if sorted_news[0]['source'] == "KBS" and sorted_news[1]['source'] == "조선일보":
        print("   ✅ Sorting working.")
    else:
        print("   ❌ Sorting failed.")

    print("\n5. Testing Entity Tagging (Name + Role)...")
    mock_entity_news = [
        {"title": "Test News", "description": "이 연구는 홍길동 교수가 주도했다.", "full_text": "", "link": "http://test.com"}
    ]
    tagged_news = processor.tag_entities(mock_entity_news)
    print(f"   Tagged Title: {tagged_news[0]['title']}")
    if "홍길동 교수" in tagged_news[0]['title']:
        print("   ✅ Entity Tagging working.")
    else:
        print("   ❌ Entity Tagging failed.")

if __name__ == "__main__":
    test_logic()
