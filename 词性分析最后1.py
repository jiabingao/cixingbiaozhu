import sys
import spacy
import csv
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QSplitter, QFrame, QStyleFactory, QProgressBar, QDialog, QTabWidget
)
from PyQt5.QtGui import QTextCharFormat, QColor, QSyntaxHighlighter, QFont, QPalette
from PyQt5.QtCore import Qt


class PhraseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phrases = []
        self.categories = []

        # 为每种分类类型设置不同的高亮颜色
        self.category_colors = {
            'Attributive adjectives + Noun (AN)': QColor("#FFE4E1"),
            'Adjectives + adjectives + Noun (AAN)': QColor("#E0FFFF"),
            'Noun + Noun (NN)': QColor("#F0FFF0"),
            'Noun + Noun + Noun (NNN)': QColor("#FFF0F5"),
            'Adjectives + Noun + Noun (ANN)': QColor("#F0F8FF"),
            'Possessive nouns + Noun (PnN)': QColor("#FAFAD2"),
            'Participles + Noun (PN)': QColor("#E6E6FA"),
            'Compounds + Noun (CN)': QColor("#F5F5DC"),
            'Adverb + Adjective/Participle + Noun (aA/PN)': QColor("#FFE4B5"),
            'Of phrase as noun post-modifiers (PrepOF)': QColor("#F0FFFF"),
            'Other prepositional phrases': QColor("#FFF5EE"),
            'Appositive noun phrase (NAn)': QColor("#F5F5F5")
        }

    def set_phrases(self, phrases, categories):
        self.phrases = phrases
        self.categories = categories
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.phrases:
            return

        for phrase, category in zip(self.phrases, self.categories):
            format = QTextCharFormat()
            color = self.category_colors.get(category, QColor("#FFFFFF"))
            format.setBackground(color)

            # 查找短语并高亮
            index = text.lower().find(phrase.lower())
            while index >= 0:
                self.setFormat(index, len(phrase), format)
                index = text.lower().find(phrase.lower(), index + len(phrase))


class PhraseAnalyzer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def get_word_details(self, token):
        """获取单词的详细信息"""
        pos_map = {
            'ADJ': '形容词',
            'NOUN': '名词',
            'VERB': '动词',
            'ADV': '副词',
            'ADP': '介词',
            'DET': '限定词',
            'PRON': '代词',
            'NUM': '数词',
            'PART': '词缀',
            'PUNCT': '标点',
            'SYM': '符号'
        }

        dep_map = {
            'amod': '形容词修饰语',
            'nsubj': '主语',
            'dobj': '宾语',
            'pobj': '介词宾语',
            'compound': '复合词',
            'det': '限定词',
            'prep': '介词',
            'poss': '所有格',
            'case': '格标记',
            'cc': '连词',
            'conj': '并列'
        }

        pos = pos_map.get(token.pos_, token.pos_)
        dep = dep_map.get(token.dep_, token.dep_)

        return f"{token.text}({pos}, {dep})"

    def analyze_phrase(self, chunk):
        """分析短语结构"""
        tokens = list(chunk)
        word_details = [self.get_word_details(token) for token in tokens]
        structure = ' + '.join(word_details)

        # 获取基本分类和判断依据
        category, reason = self.classify_phrase(chunk)

        return {
            'phrase': chunk.text,
            'structure': structure,
            'category': category,
            'reason': reason
        }

    def classify_phrase(self, chunk):
        """根据语法特征分类短语"""
        tokens = [(token.text, token.pos_, token.dep_) for token in chunk]
        text = chunk.text.lower()

        # 生成词序分析
        word_details = [self.get_word_details(token) for token in chunk]
        details = f"词序分析: {' + '.join(word_details)}"

        # Pre-modifiers 分类
        if len(tokens) == 2 and tokens[0][1] == "ADJ" and tokens[1][1] == "NOUN":
            return ("Attributive adjectives + Noun (AN)",
                    f"{details}\n判断依据: 形容词(修饰语) + 名词(中心语)的基本结构")

        if (len(tokens) == 3 and
                tokens[0][1] == "ADJ" and
                tokens[1][1] == "ADJ" and
                tokens[2][1] == "NOUN"):
            return ("Adjectives + adjectives + Noun (AAN)",
                    f"{details}\n判断依据: 双形容词(修饰语) + 名词(中心语)的结构")

        if len(tokens) == 2 and all(token[1] == "NOUN" for token in tokens):
            return ("Noun + Noun (NN)",
                    f"{details}\n判断依据: 名词(修饰语) + 名词(中心语)的复合结构")

        if (len(tokens) == 3 and
                all(token[1] == "NOUN" for token in tokens)):
            return ("Noun + Noun + Noun (NNN)",
                    f"{details}\n判断依据: 三个名词构成的复合结构")

        if (len(tokens) == 3 and
                tokens[0][1] == "ADJ" and
                tokens[1][1] == "NOUN" and
                tokens[2][1] == "NOUN"):
            return ("Adjectives + Noun + Noun (ANN)",
                    f"{details}\n判断依据: 形容词(修饰语) + 双名词复合结构")

        if any(token[2] == "poss" for token in tokens):
            return ("Possessive nouns + Noun (PnN)",
                    f"{details}\n判断依据: 包含所有格标记的名词修饰结构")

        if any(token[1] == "VERB" and token[2] == "amod" for token in tokens):
            return ("Participles + Noun (PN)",
                    f"{details}\n判断依据: 分词(作形容词用) + 名词的结构")

        if any(token[2] == "compound" for token in tokens):
            return ("Compounds + Noun (CN)",
                    f"{details}\n判断依据: 复合词结构")

        if (len(tokens) == 3 and
                tokens[0][1] == "ADV" and
                (tokens[1][1] == "ADJ" or tokens[1][1] == "VERB") and
                tokens[2][1] == "NOUN"):
            return ("Adverb + Adjective/Participle + Noun (aA/PN)",
                    f"{details}\n判断依据: 副词 + 形容词/分词 + 名词的结构")

        # Post-modifiers 分类
        if " of " in text:
            return ("Of phrase as noun post-modifiers (PrepOF)",
                    f"{details}\n判断依据: 包含'of'介词短语的后置修饰结构")

        prepositions = {"to", "in", "at", "by", "with", "for", "from", "on", "about"}
        if any(f" {prep} " in text for prep in prepositions):
            return ("Other prepositional phrases",
                    f"{details}\n判断依据: 包含其他介词的后置修饰结构")

        if (text.startswith("a ") or
                text.startswith("an ") or
                text.startswith("the ")):
            return ("Appositive noun phrase (NAn)",
                    f"{details}\n判断依据: 同位语名词短语结构")

        return ("Other", f"{details}\n判断依据: 不符合上述任何分类模式的其他结构")


class PhraseExtractorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = PhraseAnalyzer()
        self.highlighter = None
        self.extracted_phrases = []
        self.extracted_categories = []
        self.initUI()
        self.setup_style()

    def setup_style(self):
        """设置应用程序样式"""
        self.setStyle(QStyleFactory.create('Fusion'))
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(70, 70, 70))
        self.setPalette(palette)

    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("鲨家帮-复杂名词短语分析工具 V1.0 技术总监 敖丙")
        self.setGeometry(100, 100, 1600, 1000)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 创建顶部标题
        title_label = QLabel("复杂名词短语分析工具")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #2C3E50;
                padding: 10px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)

        # 上半部分（输入区域）
        top_widget = self.create_input_section()
        splitter.addWidget(top_widget)

        # 下半部分（结果区域）
        bottom_widget = self.create_result_section()
        splitter.addWidget(bottom_widget)

        layout.addWidget(splitter)

    # def create_input_section(self):
    #     """创建输入区域"""
    #     widget = QWidget()
    #     layout = QVBoxLayout(widget)
    #
    #     # 输入区标题
    #     input_title = QLabel("文本输入")
    #     input_title.setStyleSheet("""
    #         QLabel {
    #             font-size: 18px;
    #             color: #34495E;
    #             padding: 5px;
    #             font-weight: bold;
    #         }
    #     """)
    #     layout.addWidget(input_title)
    #
    #     # 文本输入框
    #     self.text_input = QTextEdit()
    #     self.text_input.setStyleSheet("""
    #         QTextEdit {
    #             border: 2px solid #BDC3C7;
    #             border-radius: 5px;
    #             padding: 10px;
    #             background-color: white;
    #             font-size: 14px;
    #         }
    #     """)
    #     layout.addWidget(self.text_input)
    #
    #     # 按钮区域
    #     button_widget = QWidget()
    #     button_layout = QHBoxLayout(button_widget)
    #
    #     buttons = [
    #         ("导入文件", self.load_file, "#3498DB"),
    #         ("分析短语", self.analyze_text, "#2ECC71"),
    #         ("高亮显示", self.highlight_phrases, "#E74C3C"),
    #         ("清除高亮", self.clear_highlights, "#95A5A6"),
    #         ("清空内容", self.clear_text, "#95A5A6"),
    #         ("导出结果", self.export_results, "#9B59B6")
    #         # ("系统帮助", self.show_help(), "#9B59B6")
    #
    #     ]
    #
    #     for text, slot, color in buttons:
    #         btn = QPushButton(text)
    #         btn.setStyleSheet(f"""
    #             QPushButton {{
    #                 background-color: {color};
    #                 color: white;
    #                 border-radius: 5px;
    #                 padding: 8px 15px;
    #                 min-width: 100px;
    #                 font-weight: bold;
    #             }}
    #             QPushButton:hover {{
    #                 background-color: {color}DD;
    #             }}
    #         """)
    #         btn.clicked.connect(slot)
    #         button_layout.addWidget(btn)
    #
    #     layout.addWidget(button_widget)
    #     return widget
    def create_input_section(self):
        """创建输入区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 输入区标题
        input_title = QLabel("文本输入")
        input_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #34495E;
                padding: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(input_title)

        # 文本输入框
        self.text_input = QTextEdit()
        self.text_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #BDC3C7;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.text_input)

        # 按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)

        buttons = [
            ("导入文件", self.load_file, "#3498DB"),
            ("分析短语", self.analyze_text, "#2ECC71"),
            ("高亮显示", self.highlight_phrases, "#E74C3C"),
            ("清除高亮", self.clear_highlights, "#95A5A6"),
            ("清空内容", self.clear_text, "#95A5A6"),
            ("导出结果", self.export_results, "#9B59B6"),
            ("使用帮助", self.show_help, "#F39C12")  # 添加帮助按钮
        ]

        for text, slot, color in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border-radius: 5px;
                    padding: 8px 15px;
                    min-width: 100px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {color}DD;
                }}
            """)
            btn.clicked.connect(slot)  # 直接连接到方法
            button_layout.addWidget(btn)

        layout.addWidget(button_widget)
        return widget
    def create_result_section(self):
        """创建结果显示区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 结果区标题
        result_title = QLabel("分析结果")
        result_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #34495E;
                padding: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(result_title)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["短语", "结构分析", "分类", "判断依据"])
        self.result_table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #BDC3C7;
                border-radius: 5px;
                background-color: white;
                gridline-color: #ECF0F1;
            }
            QHeaderView::section {
                background-color: #34495E;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

        # 设置列宽
        self.result_table.setColumnWidth(0, 300)  # 短语
        self.result_table.setColumnWidth(1, 400)  # 结构分析
        self.result_table.setColumnWidth(2, 300)  # 分类
        self.result_table.setColumnWidth(3, 400)  # 判断依据

        layout.addWidget(self.result_table)
        return widget

    def load_file(self):
        """加载文本文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "", "文本文件 (*.txt);;所有文件 (*)", options=options
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    self.text_input.setPlainText(content)
                QMessageBox.information(self, "完成", f"文件已成功加载：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件时出错：{e}")

    def analyze_text(self):
        """分析文本"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入或加载文本！")
            return

        try:
            # 清除现有的高亮和结果
            self.clear_highlights()
            self.result_table.setRowCount(0)
            self.extracted_phrases = []
            self.extracted_categories = []

            # 使用spaCy进行分析
            doc = self.analyzer.nlp(text)

            # 分析每个名词短语
            row = 0
            for chunk in doc.noun_chunks:
                analysis = self.analyzer.analyze_phrase(chunk)

                self.extracted_phrases.append(analysis['phrase'])
                self.extracted_categories.append(analysis['category'])

                # 添加到表格
                self.result_table.insertRow(row)
                self.result_table.setItem(row, 0, QTableWidgetItem(analysis['phrase']))
                self.result_table.setItem(row, 1, QTableWidgetItem(analysis['structure']))
                self.result_table.setItem(row, 2, QTableWidgetItem(analysis['category']))
                self.result_table.setItem(row, 3, QTableWidgetItem(analysis['reason']))

                row += 1

            QMessageBox.information(self, "完成", f"分析完成，共找到 {row} 个名词短语！")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析文本时出错：{e}")

    def highlight_phrases(self):
        """高亮显示短语"""
        if not self.extracted_phrases:
            QMessageBox.warning(self, "警告", "请先分析文本！")
            return

        # 创建新的高亮器
        self.highlighter = PhraseHighlighter(self.text_input.document())
        self.highlighter.set_phrases(self.extracted_phrases, self.extracted_categories)

        QMessageBox.information(self, "完成", "短语已在文本中高亮显示！")

    def clear_highlights(self):
        """清除高亮"""
        if self.highlighter:
            self.highlighter.setDocument(None)
            self.highlighter = None

    def show_help(self):
        """显示帮助对话框"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("使用帮助")
        help_dialog.setFixedSize(800, 600)

        layout = QVBoxLayout(help_dialog)

        # 创建选项卡部件
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #BDC3C7;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #ECF0F1;
                padding: 8px 15px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #3498DB;
                color: white;
            }
        """)

        # 1. 颜色说明选项卡
        color_widget = QWidget()
        color_layout = QVBoxLayout(color_widget)

        color_table = QTableWidget()
        color_table.setColumnCount(3)
        color_table.setHorizontalHeaderLabels(["分类", "颜色示例", "说明"])
        color_table.horizontalHeader().setStretchLastSection(True)

        color_mappings = [
            ("Attributive adjectives + Noun (AN)", "#FFE4E1", "形容词+名词结构\n例如: beautiful car"),
            ("Adjectives + adjectives + Noun (AAN)", "#E0FFFF", "双形容词+名词结构\n例如: big red house"),
            ("Noun + Noun (NN)", "#F0FFF0", "名词+名词复合结构\n例如: computer screen"),
            ("Noun + Noun + Noun (NNN)", "#FFF0F5", "三名词复合结构\n例如: world cup final"),
            ("Adjectives + Noun + Noun (ANN)", "#F0F8FF", "形容词+双名词结构\n例如: digital camera lens"),
            ("Possessive nouns + Noun (PnN)", "#FAFAD2", "所有格名词+名词结构\n例如: John's book"),
            ("Participles + Noun (PN)", "#E6E6FA", "分词+名词结构\n例如: running water"),
            ("Compounds + Noun (CN)", "#F5F5DC", "复合词+名词结构\n例如: high-speed train"),
            (
            "Adverb + Adjective/Participle + Noun (aA/PN)", "#FFE4B5", "副词+形容词/分词+名词结构\n例如: very hot day"),
            ("Of phrase as noun post-modifiers (PrepOF)", "#F0FFFF", "of介词短语后置修饰\n例如: book of poems"),
            ("Other prepositional phrases", "#FFF5EE", "其他介词短语修饰\n例如: man in black"),
            ("Appositive noun phrase (NAn)", "#F5F5F5", "同位语名词短语\n例如: my friend John")
        ]

        color_table.setRowCount(len(color_mappings))
        for i, (category, color, desc) in enumerate(color_mappings):
            color_table.setItem(i, 0, QTableWidgetItem(category))

            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(color))
            color_table.setItem(i, 1, color_item)

            color_table.setItem(i, 2, QTableWidgetItem(desc))

        color_table.setColumnWidth(0, 300)
        color_table.setColumnWidth(1, 100)
        color_layout.addWidget(color_table)

        # 2. 使用说明选项卡
        usage_widget = QWidget()
        usage_layout = QVBoxLayout(usage_widget)

        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setStyleSheet("QTextEdit { background-color: white; }")
        usage_text.setHtml("""
            <h3>使用说明</h3>
            <p><b>1. 文本输入：</b></p>
            <ul>
                <li>直接在输入框中输入英文文本</li>
                <li>或使用"导入文件"按钮导入txt文本文件</li>
            </ul>

            <p><b>2. 分析操作：</b></p>
            <ul>
                <li>点击"分析短语"按钮进行短语识别和分类</li>
                <li>点击"高亮显示"可在原文中标记所有短语</li>
                <li>点击"清除高亮"可取消文本中的高亮显示</li>
            </ul>

            <p><b>3. 结果查看：</b></p>
            <ul>
                <li>在下方表格中查看详细的分析结果</li>
                <li>包含短语、结构分析、分类和判断依据</li>
                <li>可以使用"导出结果"保存分析结果到CSV文件</li>
            </ul>

            <p><b>4. 注意事项：</b></p>
            <ul>
                <li>输入文本需要是规范的英文文本</li>
                <li>建议每次处理的文本量不要过大</li>
                <li>可以随时清空内容重新开始分析</li>
            </ul>
        """)
        usage_layout.addWidget(usage_text)

        # 3. 关于选项卡
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)

        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setStyleSheet("QTextEdit { background-color: white; }")
        about_text.setHtml("""
            <h3>关于本工具</h3>
            <p>复杂名词短语分析工具是一个用于分析英语文本中名词短语结构的工具。</p>

            <p><b>主要功能：</b></p>
            <ul>
                <li>自动识别文本中的名词短语</li>
                <li>分析短语的内部结构和组成成分</li>
                <li>根据语法特征进行分类标注</li>
                <li>提供详细的分析依据说明</li>
                <li>支持结果导出和可视化显示</li>
            </ul>

            <p><b>技术支持：</b></p>
            <ul>
               <li>鲨鱼专属的小工具</li>
                <li>新功能需求可使用文档形式与工程师敖丙联系</li>
               
               
            </ul>
        """)
        about_layout.addWidget(about_text)

        # 添加选项卡
        tabs.addTab(color_widget, "颜色说明")
        tabs.addTab(usage_widget, "使用说明")
        tabs.addTab(about_widget, "关于")

        layout.addWidget(tabs)

        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                min-width: 100px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        close_btn.clicked.connect(help_dialog.close)

        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        help_dialog.exec_()
    def clear_text(self):
        """清空文本和结果"""
        self.text_input.clear()
        self.result_table.setRowCount(0)
        self.clear_highlights()
        self.extracted_phrases = []
        self.extracted_categories = []

    def export_results(self):
        """导出分析结果"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有可导出的结果！")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "CSV文件 (*.csv);;所有文件 (*)", options=options
        )

        if file_path:
            try:
                with open(file_path, mode="w", newline="", encoding="utf-8-sig") as file:
                    writer = csv.writer(file)
                    # 写入表头
                    headers = ["短语", "结构分析", "分类", "判断依据"]
                    writer.writerow(headers)

                    # 写入数据
                    for row in range(self.result_table.rowCount()):
                        row_data = []
                        for col in range(self.result_table.columnCount()):
                            item = self.result_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)

                QMessageBox.information(self, "完成", f"结果已成功导出到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出结果时出错：{e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))

    # 设置全局字体
    font = QFont('Microsoft YaHei', 10)
    app.setFont(font)

    main_window = PhraseExtractorApp()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()