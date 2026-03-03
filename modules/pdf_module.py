#增值税主表取数工具,仅提取主表数据

import re, os, pandas as pd
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

# ==================== 16 组正则配置 ====================
PATTERNS = {
    "pattern0": re.compile(
        r"税款所属期间.+?(\d{4}-\d{2}-\d{2}\D*\d{4}-\d{2}-\d{2})|自.?(\d{4}年.?\d{1,2}月.?\d{1,2}日).?至.?(\d{4}年.?\d{1,2}月.?\d{1,2}日).?"),
    "pattern1": re.compile(r"按适用税率计税销售额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern2": re.compile(r"按简易办法计税销售额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern3": re.compile(r"免、抵、退办法出口销售额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern4": re.compile(r"免税销售额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern5": re.compile(r"销项税额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern6": re.compile(r'\b进项税额\b\s+\d+\s+(\d+(?:,\d+)*\.\d+)\s*'),
    "pattern7": re.compile(r"进项税额转出\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern8": re.compile(r"期末留抵税额\s+\d+[=＝]\d+[-\－]\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern9": re.compile(r"简易计税办法计算的应纳税额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern10": re.compile(r"应纳税额合计\s+\d+=\d+\+\d+-\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern11": re.compile(r"应纳税额减征额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern12": re.compile(r"城市维护建设税本期应补（退）税额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern13": re.compile(r"教育费附加本期应补（退）费额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern14": re.compile(r"地方教育附加本期应补（退）费额\s+\d+\s+(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})"),
    "pattern15": re.compile(
        r'纳税人名称[：:]?\s*([\u4e00-\u9fa5]{2,40}?(?:公司|集团)(?:有限)?公司[\u4e00-\u9fa5]{0,15}?(?:分公司)?)'),
}

# ==================== 核心取数逻辑 ====================
def clean_company_name(name):
    if not name: return name
    stop_words = ['法定代表人姓', '注册地址', '金额单位', '纳税人识别号']
    for word in stop_words:
        if word in name: name = name.split(word)[0].strip()
    return re.sub(r'\s+', ' ', name).strip()

def extract_company_name_fallback(text):
    if not text: return None
    name_match = re.search(r'纳税人名称[^：:\n]*[：:\s]*([\u4e00-\u9fa5]{2,}公司[\u4e00-\u9fa5]*)', text)
    if name_match: return clean_company_name(name_match.group(1))
    company_match = re.search(r'([\u4e00-\u9fa5]{2,}公司[\u4e00-\u9fa5]*(?:分公司)?)', text)
    if company_match: return clean_company_name(company_match.group(1))
    return None

def sort_by_tax_period(df):
    if "税款所属期间" not in df.columns: return df
    def extract_sort_key(period_str):
        if not period_str or pd.isna(period_str): return (9999, 13)
        match = re.search(r'自(\d{4})年\s*(\d{1,2})月', str(period_str))
        if match: return (int(match.group(1)), int(match.group(2)))
        match = re.search(r'(\d{4})-(\d{2})', str(period_str))
        if match: return (int(match.group(1)), int(match.group(2)))
        return (9999, 13)
    df['_sort_key'] = df['税款所属期间'].apply(extract_sort_key)
    return df.sort_values('_sort_key').drop('_sort_key', axis=1).reset_index(drop=True)

def process_single_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        if len(reader.pages) < 2: return None
        page1_txt = reader.pages[0].extract_text() or ""
        page2_txt = reader.pages[1].extract_text() or ""
        cleaned_p1 = re.sub(r'\s+', ' ', page1_txt)
        cleaned_p2 = re.sub(r'\s+', ' ', page2_txt)

        company_name = None
        company_match = PATTERNS["pattern15"].search(cleaned_p2)
        if company_match:
            company_name = clean_company_name(company_match.group(1).strip())
        else:
            company_name = extract_company_name_fallback(cleaned_p2)

        if not company_name: return None

        matches = {}
        for key, pattern in PATTERNS.items():
            if key != "pattern15":
                m_list = pattern.findall(cleaned_p1)
                matches[key] = m_list[0] if m_list else None

        tax_period = None
        p0_match = PATTERNS["pattern0"].search(cleaned_p1)
        if p0_match:
            if p0_match.group(1):
                tax_period = p0_match.group(1)
            elif p0_match.group(2) and p0_match.group(3):
                tax_period = f"自{p0_match.group(2)}至{p0_match.group(3)}"

        return {
            "公司名称": company_name,
            "税款所属期间": tax_period,
            "按适用税率计税销售额": matches["pattern1"],
            "按简易办法计税销售额": matches["pattern2"],
            "免、抵、退办法出口销售额": matches["pattern3"],
            "免税销售额": matches["pattern4"],
            "销项税额": matches["pattern5"],
            "进项税额": matches["pattern6"],
            "进项税额转出": matches["pattern7"],
            "期末留抵税额": matches["pattern8"],
            "简易计税办法计算的应纳税额": matches["pattern9"],
            "应纳税额合计": matches["pattern10"],
            "应纳税额减征额": matches["pattern11"],
            "城市维护建设税本期应补（退）税额": matches["pattern12"],
            "教育费附加本期应补（退）费额": matches["pattern13"],
            "地方教育附加本期应补（退）费额": matches["pattern14"],
            "文件名": os.path.basename(file_path)
        }
    except Exception:
        return None

# ==================== QThread 工作器 ====================
class PDFWorker(QThread):
    log_sig = pyqtSignal(str)
    prog_sig = pyqtSignal(int)
    finish_sig = pyqtSignal(bool, str, str)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    def run(self):
        try:
            pdf_files = [os.path.join(r, f) for r, _, fs in os.walk(self.folder) for f in fs
                         if f.lower().endswith('.pdf') and "增值税" in f]
            total = len(pdf_files)
            if total == 0:
                self.finish_sig.emit(False, "未找到相关PDF文件。", "")
                return

            self.log_sig.emit(f"📂 发现 {total} 个文件，开始提取…")
            results = []
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(process_single_pdf, f): f for f in pdf_files}
                for i, future in enumerate(as_completed(futures)):
                    fname = os.path.basename(futures[future])
                    res = future.result()
                    if res:
                        results.append(res)
                        self.log_sig.emit(f"✅ [{i + 1}/{total}] 提取成功: {fname}")
                    else:
                        self.log_sig.emit(f"❌ [{i + 1}/{total}] 提取失败: {fname}")
                    self.prog_sig.emit(int((i + 1) / total * 100))

            if results:
                df = pd.DataFrame(results)
                df = sort_by_tax_period(df)
                output_path = os.path.join(self.folder, "增值税主表汇总统计表.xlsx")
                df.to_excel(output_path, index=False)
                self.finish_sig.emit(True, f"处理完成！成功提取 {len(results)} 条数据。", output_path)
            else:
                self.finish_sig.emit(False, "未能提取到任何有效数据。", "")
        except Exception as e:
            self.finish_sig.emit(False, str(e), "")

# ==================== UI 界面 ====================
class PDFPage(QWidget):
    def __init__(self):
        super().__init__()
        self.last_output_dir = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        group = QGroupBox("增值税申报表(PDF文件)主表数据提取")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("文件夹目录:"), 0, 0)
        self.dir_edit = QLineEdit()
        grid.addWidget(self.dir_edit, 0, 1)
        btn_dir = QPushButton("选择文件夹")
        btn_dir.clicked.connect(self.select_dir)
        grid.addWidget(btn_dir, 0, 2)
        grid.addWidget(QLabel("处理进度:"), 1, 0)
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(28)
        grid.addWidget(self.pbar, 1, 1, 1, 2)
        layout.addWidget(group)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("🚀 开始提取数据")
        self.run_btn.clicked.connect(self.start_task)
        self.open_dir_btn = QPushButton("📂 打开结果所在目录")
        self.open_dir_btn.setEnabled(False)
        self.open_dir_btn.clicked.connect(self.open_result_folder)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.open_dir_btn)
        layout.addLayout(btn_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def select_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path: self.dir_edit.setText(path)

    def start_task(self):
        if not self.dir_edit.text(): return
        self.run_btn.setEnabled(False)
        self.pbar.setValue(0)
        self.log_area.clear()
        self.worker = PDFWorker(self.dir_edit.text())
        self.worker.log_sig.connect(self.log_area.append)
        self.worker.prog_sig.connect(self.pbar.setValue)
        self.worker.finish_sig.connect(self.on_finish)
        self.worker.start()

    def on_finish(self, success, msg, output_path):
        self.run_btn.setEnabled(True)
        if success:
            self.last_output_dir = os.path.dirname(output_path)
            self.open_dir_btn.setEnabled(True)

            # --- 新增日志提示 ---
            self.log_area.append("-" * 30)
            self.log_area.append(f"🎉 任务处理成功！")
            self.log_area.append(f"📍 结果文件存放路径：\n{output_path}")
            self.log_area.append("-" * 30)
            # ------------------

            QMessageBox.information(self, "执行成功", msg)
        else:
            self.log_area.append(f"❌ 执行失败：{msg}")
            QMessageBox.critical(self, "执行失败", msg)

    def open_result_folder(self):
        if self.last_output_dir:
            os.startfile(self.last_output_dir)

# ==================== 插件接口 ====================
class Plugin:
    plugin_name = "增值税申报表主表取数"
    plugin_version = "1.0.0"

    def get_widget(self):
        return PDFPage()

def register_plugin():
    return Plugin()

def _test_run():
    import sys
    from PyQt6.QtWidgets import QApplication

    print("🧪 PDFPage 独立测试模式启动")

    app = QApplication(sys.argv)
    w = PDFPage()
    w.resize(900, 650)  # 可选：测试窗口大小
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    _test_run()