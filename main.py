# main.py
from PyQt5.QtWidgets import QApplication, QInputDialog
from ui.main_window import NewsApp
from core import gpt_filter, fetcher_rss
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # API 키 입력 받기
    key, ok = QInputDialog.getText(None, "OpenAI API Key 입력", "GPT API Key를 입력하세요:")
    if ok and key:
        gpt_filter.set_api_key(key)
        fetcher_rss.set_api_key(key)
    else:
        print("❌ API 키가 입력되지 않았습니다.")
        sys.exit(1)

    window = NewsApp()
    window.show()
    sys.exit(app.exec_())
