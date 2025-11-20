from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QTextEdit, QGroupBox, QFormLayout, QListWidget,
    QListWidgetItem, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import sys
import ast

from core.fetcher_naver import get_naver_news
from core.fetcher_rss import get_rss_news
from core.gpt_filter import filtering
from core.db_manager import init_db, save_article, load_article, load_all_articles, delete_article
from core.pdf_generator import generate_pdf


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        self.clicked.emit()


class NewsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("뉴스 탐색 및 커스텀 프로그램")
        self.setMinimumSize(1100, 750)

        self.previous_list = []
        self.selected_articles = set()
        self.article_details = {}
        self.relevance_dict = {}

        self.keyword_input = QLineEdit()
        self.fetch_button = QPushButton("뉴스 수집 시작")

        self.result_area = QScrollArea()
        self.result_container = QVBoxLayout()

        self.selection_list = QListWidget()
        self.detail_input_box = QGroupBox("기사 추가 정보 입력")
        self.detail_form = QFormLayout()
        self.detail_title = QLabel("기사 제목을 선택하세요.")
        self.detail_link = QLabel("")
        self.detail_source = QLineEdit()
        self.detail_body = QTextEdit()
        self.save_button = QPushButton("📝 저장")

        self.tab_widget = QTabWidget()
        self.news_tab = QWidget()
        self.saved_tab = QWidget()
        self.report_tab = QWidget()

        self.saved_article_list = QListWidget()
        self.saved_article_view = QTextEdit()
        self.delete_button = QPushButton("❌ 삭제")

        self.generate_button = QPushButton("📄 PDF 리포트 생성하기")

        init_db()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("키워드 입력:"))
        layout.addWidget(self.keyword_input)
        layout.addWidget(self.fetch_button)
        self.fetch_button.clicked.connect(self.start_fetching)

        scroll_content = QWidget()
        scroll_content.setLayout(self.result_container)
        self.result_area.setWidget(scroll_content)
        self.result_area.setWidgetResizable(True)

        main_area = QHBoxLayout()
        main_area.addWidget(self.result_area)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("📝 선택된 기사 목록:"))
        self.selection_list.setFixedHeight(180)
        right_panel.addWidget(self.selection_list)
        self.selection_list.itemClicked.connect(self.selection_clicked)

        self.detail_form.addRow("제목", self.detail_title)
        self.detail_form.addRow("링크", self.detail_link)
        self.detail_form.addRow("신문사", self.detail_source)
        self.detail_form.addRow("기사 본문", self.detail_body)
        self.detail_form.addRow("", self.save_button)
        self.detail_input_box.setLayout(self.detail_form)
        right_panel.addWidget(self.detail_input_box)
        self.save_button.clicked.connect(self.save_current_article)

        main_area.addLayout(right_panel)
        layout.addLayout(main_area)
        self.news_tab.setLayout(layout)

        saved_layout = QVBoxLayout()
        saved_layout.addWidget(QLabel("📁 저장된 기사 목록:"))
        self.saved_article_list.setFixedHeight(200)
        saved_layout.addWidget(self.saved_article_list)
        self.saved_article_list.itemClicked.connect(self.display_saved_article)

        self.saved_article_view.setReadOnly(True)
        saved_layout.addWidget(QLabel("📝 기사 보기:"))
        saved_layout.addWidget(self.saved_article_view)
        self.delete_button.clicked.connect(self.delete_selected_article)
        saved_layout.addWidget(self.delete_button)
        self.saved_tab.setLayout(saved_layout)

        report_layout = QVBoxLayout()
        report_layout.addWidget(QLabel("🗞 저장된 모든 기사로 리포트를 생성합니다."))
        report_layout.addWidget(self.generate_button)
        self.generate_button.clicked.connect(self.generate_pdf_report)
        self.report_tab.setLayout(report_layout)

        self.tab_widget.addTab(self.news_tab, "📰 뉴스 수집")
        self.tab_widget.addTab(self.saved_tab, "📂 저장된 기사")
        self.tab_widget.addTab(self.report_tab, "📄 리포트 생성")
        self.load_saved_articles()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def start_fetching(self):
        keyword = self.keyword_input.text().strip()
        if not keyword:
            return

        self.previous_list.clear()
        self.selected_articles.clear()
        self.clear_results()
        self.selection_list.clear()
        self.detail_title.setText("기사 제목을 선택하세요.")
        self.detail_link.setText("")
        self.detail_source.clear()
        self.detail_body.clear()
        self.relevance_dict.clear()

        self.previous_list.extend(get_naver_news(keyword))
        self.previous_list.extend(get_rss_news(keyword))

        for idx, item in enumerate(self.previous_list, start=1):
            item.insert(0, idx)

        title_index_list = [[item[0], item[1], item[2]] for item in self.previous_list]
        filtering_list_str = filtering(keyword, title_index_list)

        try:
            filtering_list = ast.literal_eval(filtering_list_str)
        except Exception as e:
            print("❌ GPT 관련도 파싱 실패:", e)
            filtering_list = []

        for fid, rel in filtering_list:
            self.relevance_dict[fid] = rel

        relevance_order = {"최상": 0, "상": 1, "중": 2, "하": 3, "최하": 4, "미지정": 5}
        sorted_articles = sorted(self.previous_list, key=lambda x: relevance_order.get(self.relevance_dict.get(x[0], "미지정"), 5))

        for item in sorted_articles:
            self.add_article_entry(item)

    def add_article_entry(self, article):
        index, title, link, description, pub_date = article
        relevance = self.relevance_dict.get(index, "미지정")

        title_label = ClickableLabel(f"[{index}] {title} ({relevance})")
        title_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        title_label.setCursor(Qt.PointingHandCursor)
        title_label.setStyleSheet("color: black; text-decoration: none;")

        def toggle_selection():
            if index in self.selected_articles:
                self.selected_articles.remove(index)
                title_label.setStyleSheet("color: black; text-decoration: none;")
                for i in range(self.selection_list.count()):
                    if self.selection_list.item(i).text().startswith(f"[{index}]"):
                        self.selection_list.takeItem(i)
                        break
            else:
                self.selected_articles.add(index)
                self.article_details[index] = {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pub_date": pub_date,
                    "source": "",
                    "body": ""
                }
                title_label.setStyleSheet("color: red; text-decoration: none;")
                self.selection_list.addItem(f"[{index}] {title}")

        title_label.clicked.connect(toggle_selection)

        link_label = QLabel(f"<a href='{link}'>{link}</a>")
        link_label.setOpenExternalLinks(True)
        date_label = QLabel(f"📅 {pub_date}")
        date_label.setStyleSheet("color: gray; font-size: 10pt;")

        self.result_container.addWidget(title_label)
        self.result_container.addWidget(link_label)
        self.result_container.addWidget(date_label)
        self.result_container.addWidget(QLabel(""))

    def selection_clicked(self, item):
        try:
            idx = int(item.text().split("]")[0][1:])
            detail = self.article_details.get(idx)
            if detail:
                saved_data = load_article(idx)
                if saved_data:
                    detail["source"], detail["body"] = saved_data
                self.detail_title.setText(detail["title"])
                self.detail_link.setText(f"<a href='{detail['link']}'>{detail['link']}</a>")
                self.detail_link.setOpenExternalLinks(True)
                self.detail_source.setText(detail["source"])
                self.detail_body.setPlainText(detail["body"])
                self.save_button.setText("📝 저장")
        except Exception as e:
            print("❌ 선택 처리 오류:", e)

    def save_current_article(self):
        idx = self.detail_title.text()
        if not idx:
            return
        for article_id, detail in self.article_details.items():
            if detail["title"] == idx:
                detail["source"] = self.detail_source.text().strip()
                detail["body"] = self.detail_body.toPlainText().strip()
                save_article({
                    "id": article_id,
                    "title": detail["title"],
                    "link": detail["link"],
                    "pub_date": detail["pub_date"],
                    "source": detail["source"],
                    "body": detail["body"]
                })
                self.save_button.setText("✅ 저장됨")
                self.load_saved_articles()
                return
        self.save_button.setText("❌ 저장 실패")

    def load_saved_articles(self):
        self.saved_article_list.clear()
        grouped = defaultdict(list)

        for row in load_all_articles():
            index, title, link, pub_date, source, body, saved_at = row

            # ✅ 저장일 처리 로직 개선
            if saved_at and " " in saved_at:
                date = saved_at.split(" ")[0]
            elif saved_at:
                date = saved_at
            else:
                date = "미지정"

            grouped[date].append((index, title))

        for date in sorted(grouped.keys(), reverse=True):
            header_item = QListWidgetItem(f"📅 저장일: {date}")
            header_item.setFlags(Qt.ItemIsEnabled)
            self.saved_article_list.addItem(header_item)
            for idx, title in grouped[date]:
                self.saved_article_list.addItem(f"[{idx}] {title}")


    def display_saved_article(self, item):
        text = item.text()
        if not text.startswith("["):
            return
        try:
            idx = int(text.split("]")[0][1:])
            for row in load_all_articles():
                if len(row) < 7:
                    continue
                if row[0] == idx:
                    _, title, link, pub_date, source, body, _ = row
                    self.saved_article_view.setText(
                        f"제목: {title}\n날짜: {pub_date}\n링크: {link}\n\n신문사: {source}\n\n본문:\n{body}"
                    )
                    break
        except Exception as e:
            print("❌ 기사 표시 오류:", e)

    def delete_selected_article(self):
        item = self.saved_article_list.currentItem()
        if not item:
            return
        text = item.text()
        if not text.startswith("["):
            return
        idx = int(text.split("]")[0][1:])
        confirm = QMessageBox.question(self, "삭제 확인", f"기사 [{idx}]를 삭제하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            delete_article(idx)
            self.load_saved_articles()
            self.saved_article_view.clear()

    def generate_pdf_report(self):
        try:
            records = load_all_articles()
            articles = []
            for r in records:
                if len(r) < 7:
                    print("⚠️ 무시된 레코드 (필드 부족):", r)
                    continue
                articles.append({
                    "title": r[1] or "제목 없음",
                    "pub_date": r[3] or "날짜 없음",
                    "link": r[2] or "링크 없음",
                    "source": r[4] or "신문사 없음",
                    "body": r[5] or "본문 없음"
                })
            output_path = generate_pdf(articles=articles, keyword=self.keyword_input.text().strip())
            QMessageBox.information(self, "완료", f"PDF 생성 완료!\n{output_path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"PDF 생성 중 오류 발생:\n{str(e)}")

    def clear_results(self):
        while self.result_container.count():
            item = self.result_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "종료 확인",
            "정말로 프로그램을 종료하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NewsApp()
    window.show()
    sys.exit(app.exec_())
