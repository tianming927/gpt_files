import sys
import json
import os
import paramiko
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# --- 远程服务器配置 ---
# 请根据你的华为云实际信息修改
SERVER_IP = "113.45.76.90"
SERVER_USER = "root"
SERVER_PWD = "HAIer19930927"  # 建议正式使用时通过加密存储
#这里需要修改成username文件夹下的json路径:"/www/wwwroot/113.45.76.90_8001/username/users.json"
REMOTE_PATH = "/www/wwwroot/113.45.76.90_8001/username/users.json"


class AdminTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("中翰裕众 - 账号权限管理后台")
        self.resize(800, 600)
        self.local_file = "users.json"
        self.data = self.load_local_data()
        self.init_ui()

    def load_local_data(self):
        """加载本地配置，如果不存在则创建模板"""
        if os.path.exists(self.local_file):
            with open(self.local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"staff": {}, "client": {}}

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 顶部操作区
        top_bar = QHBoxLayout()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["staff", "client"])
        self.add_btn = QPushButton("添加新用户")
        self.add_btn.clicked.connect(self.add_user_dialog)
        self.sync_btn = QPushButton("🚀 一键同步到服务器")
        self.sync_btn.setStyleSheet("background-color: #e67e22; color: white;")
        self.sync_btn.clicked.connect(self.sync_to_server)

        top_bar.addWidget(QLabel("类型:"))
        top_bar.addWidget(self.role_combo)
        top_bar.addStretch()
        top_bar.addWidget(self.add_btn)
        top_bar.addWidget(self.sync_btn)
        layout.addLayout(top_bar)

        # 用户列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["类型", "账号", "昵称", "权限", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for role in ["staff", "client"]:
            for u, info in self.data[role].items():
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(role))
                self.table.setItem(row, 1, QTableWidgetItem(u))
                self.table.setItem(row, 2, QTableWidgetItem(info['nickname']))
                self.table.setItem(row, 3, QTableWidgetItem(", ".join(info['access'])))

                del_btn = QPushButton("删除")
                del_btn.setStyleSheet("background-color: #e74c3c;")
                del_btn.clicked.connect(lambda _, r=role, user=u: self.delete_user(r, user))
                self.table.setCellWidget(row, 4, del_btn)

    def add_user_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加/修改用户")
        d_layout = QFormLayout(dialog)

        role = self.role_combo.currentText()
        u_input = QLineEdit()
        p_input = QLineEdit()
        n_input = QLineEdit()

        # 权限勾选框
        auth_group = QGroupBox("模块权限分配")
        auth_layout = QVBoxLayout(auth_group)
        # 这里填入你 modules 文件夹下实际的文件名（不带.py）
        modules = ["tax_module", "pdf_module", "rd_module","all"]
        checks = {}
        for m in modules:
            cb = QCheckBox(m)
            checks[m] = cb
            auth_layout.addWidget(cb)

        d_layout.addRow("账号:", u_input)
        d_layout.addRow("密码:", p_input)
        d_layout.addRow("昵称:", n_input)
        d_layout.addRow(auth_group)

        btn = QPushButton("保存")
        btn.clicked.connect(dialog.accept)
        d_layout.addRow(btn)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_auth = [m for m, cb in checks.items() if cb.isChecked()]
            self.data[role][u_input.text()] = {
                "password": p_input.text(),
                "nickname": n_input.text(),
                "access": selected_auth
            }
            self.save_local()
            self.refresh_table()

    def delete_user(self, role, user):
        if user in self.data[role]:
            del self.data[role][user]
            self.save_local()
            self.refresh_table()

    def save_local(self):
        with open(self.local_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def sync_to_server(self):
        try:
            # 1. 先保存本地
            self.save_local()

            # 2. SFTP 传输
            transport = paramiko.Transport((SERVER_IP, 22))
            transport.connect(username=SERVER_USER, password=SERVER_PWD)
            sftp = paramiko.SFTPClient.from_transport(transport)

            sftp.put(self.local_file, REMOTE_PATH)

            sftp.close()
            transport.close()
            QMessageBox.information(self, "成功", "数据已同步至华为云服务器！")
        except Exception as e:
            QMessageBox.critical(self, "同步失败", f"错误详情: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminTool()
    window.show()
    sys.exit(app.exec())