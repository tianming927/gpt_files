# -*- coding: utf-8 -*-
import os
import sys
import traceback
import importlib.util
from typing import Dict, Optional, List
import requests
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QStackedWidget,
    QMessageBox,
    QFrame,
    QDialog,
    QLineEdit,
    QRadioButton,
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve

# ============================================================
# Login Dialog (保持不变)
# ============================================================
LOGIN_STYLE = """
QDialog { background-color: #ffffff; border-radius: 10px; }
QLabel#TitleLabel { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
QLineEdit { padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px; }
QPushButton#LoginBtn { background-color: #3498db; color: white; padding: 10px; font-size: 14px; border-radius:5px; }
QRadioButton { spacing: 8px; font-size: 13px; }
"""


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录 - 中翰裕众")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet(LOGIN_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        title = QLabel("欢迎登录中翰裕众财务工具平台")
        title.setObjectName("TitleLabel")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        role_layout = QHBoxLayout()
        self.radio_staff = QRadioButton("员工登录")
        self.radio_client = QRadioButton("客户登录")
        self.radio_staff.setChecked(True)
        role_layout.addWidget(self.radio_staff)
        role_layout.addWidget(self.radio_client)
        layout.addLayout(role_layout)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("请输入账号")
        layout.addWidget(self.user_input)

        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("请输入密码")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pwd_input)

        self.login_btn = QPushButton("立即登录")
        self.login_btn.setObjectName("LoginBtn")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        self.exit_btn = QPushButton("退出程序")
        self.exit_btn.setStyleSheet("background: transparent; color: #909399; border: none;")
        self.exit_btn.clicked.connect(self.reject)
        layout.addWidget(self.exit_btn)

        self.user_info = None

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.pwd_input.text().strip()
        role = "staff" if self.radio_staff.isChecked() else "client"

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入账号和密码")
            return

        try:
            self.login_btn.setEnabled(False)
            self.login_btn.setText("验证中...")
            QApplication.processEvents()

            login_url = "http://113.45.76.90:8001/login"
            payload = {"username": username, "password": password, "role": role}

            response = requests.post(login_url, json=payload, timeout=8)
            result = response.json()

            if response.status_code == 200 and result.get("status") == "success":
                self.user_info = result.get("user_data")
                self.accept()
            else:
                error_msg = result.get("message", "账号或密码错误")
                QMessageBox.critical(self, "登录失败", error_msg)
        except Exception:
            QMessageBox.critical(self, "网络错误", "无法连接验证服务器，请检查网络设置。")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("立即登录")


# ============================================================
# Plugin Interface Contract
# ============================================================
class PluginInterface:
    plugin_name: str = "Unnamed Plugin"
    plugin_icon: Optional[str] = None
    # 增加一个属性，用于记录模块标识符（对应权限名）
    module_id: str = ""

    def get_widget(self) -> QWidget:
        raise NotImplementedError


# ============================================================
# Enterprise Plugin Manager
# ============================================================
class PluginManager:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, PluginInterface] = {}
        self.modules = {}

    def load_all(self):
        if not os.path.exists(self.plugin_dir):
            return

        files = os.listdir(self.plugin_dir)
        module_files = [f for f in files if f.endswith("_module.py")]

        for filename in module_files:
            self._safe_load(filename)

    def _safe_load(self, filename: str):
        try:
            module_name = filename[:-3]  # 例如 'tax_module'
            file_path = os.path.join(self.plugin_dir, filename)

            if module_name in self.modules:
                return

            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.modules[module_name] = module

            if hasattr(module, "register_plugin"):
                plugin = module.register_plugin()
                if plugin:
                    # 将模块文件名设为标识符，方便权限比对
                    plugin.module_id = module_name
                    self.plugins[plugin.plugin_name] = plugin
        except Exception:
            traceback.print_exc()

    def get_plugins(self):
        return self.plugins


# ============================================================
# Sidebar Button (保持不变)
# ============================================================
class SidebarButton(QPushButton):
    def __init__(self, text: str, icon_path: Optional[str] = None):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setCheckable(True)
        style = """
            QPushButton {
                border: none;
                text-align: left;
                padding-left: 10px;
                font-size: 14px;
                background: transparent;
            }
            QPushButton:hover {
                background: #f0f3f7;
            }
            QPushButton:checked {
                background: #e6f0ff;
                border-left: 4px solid #3b82f6;
                font-weight: bold;
            }
        """
        self.setStyleSheet(style)
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))


# ============================================================
# Main Window - 增加权限过滤逻辑
# ============================================================
class MainWindow(QWidget):
    def __init__(self, user_info: Optional[dict] = None):
        super().__init__()
        self.user_info = user_info if user_info else {}
        self.nickname = self.user_info.get("nickname", "用户")
        # 从登录数据中获取 access 列表（权限名列表）
        self.user_permissions = self.user_info.get("access", [])

        self.setWindowTitle(f"中翰裕众财税工具平台 - 欢迎 {self.nickname}")
        self.resize(1200, 750)

        # 插件管理器
        self.plugin_manager = PluginManager("modules")
        self.plugin_manager.load_all()

        # UI 构建
        self._build_ui()
        self._show_welcome_animation()
        self._load_plugins_to_ui()

        # 时间更新
        self._update_time()
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.top_frame = QFrame()
        self.top_frame.setFixedHeight(70)
        self.top_frame.setStyleSheet("background:#f5f5f5; color:#333333;")
        self.top_layout = QHBoxLayout(self.top_frame)
        self.top_layout.setContentsMargins(20, 0, 20, 0)

        self.welcome_label = QLabel("")
        self.welcome_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.top_layout.addWidget(self.welcome_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.time_label = QLabel()
        self.time_label.setFont(QFont("Microsoft YaHei", 12))
        self.top_layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.root_layout.addWidget(self.top_frame)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background:#ffffff;border-right:1px solid #e5e7eb;")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel("⚡ 功能菜单")
        title.setStyleSheet("font-size:16px;font-weight:bold;padding:16px;")
        self.sidebar_layout.addWidget(title)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:#f7f9fc;")

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.stack)
        self.root_layout.addLayout(content_layout)

        self.sidebar_buttons = []

    def _show_welcome_animation(self):
        self.full_text = f"尊敬的 {self.nickname}, 欢迎使用中翰裕众财税工具平台！"
        self.current_index = 0
        self.welcome_timer = QTimer(self)
        self.welcome_timer.timeout.connect(self._type_welcome)
        self.welcome_timer.start(100)

    def _type_welcome(self):
        if self.current_index <= len(self.full_text):
            self.welcome_label.setText(self.full_text[:self.current_index])
            self.current_index += 1
        else:
            self.welcome_timer.stop()
            self._fade_out_welcome()

    def _fade_out_welcome(self):
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self.opacity_effect = QGraphicsOpacityEffect(self.welcome_label)
        self.welcome_label.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(2000)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.finished.connect(self.welcome_label.hide)
        self.fade_anim.start()

    def _update_time(self):
        now = datetime.now()
        self.time_label.setText(now.strftime("%Y-%m-%d %H:%M:%S"))

    # 修改后的插件渲染方法，增加权限比对
    def _load_plugins_to_ui(self):
        all_plugins = self.plugin_manager.get_plugins()
        if not all_plugins:
            return

        visible_count = 0
        for name, plugin in all_plugins.items():
            try:
                # 权限比对核心逻辑 [cite: 2026-02-26]
                # 如果用户权限列表不包含 'all' 且 不包含 该模块ID，则跳过
                if "all" not in self.user_permissions:
                    if plugin.module_id not in self.user_permissions:
                        continue

                # 获取插件 Widget 并加入堆栈
                widget = plugin.get_widget()
                self.stack.addWidget(widget)

                # 侧边栏按钮逻辑
                btn = SidebarButton(name, getattr(plugin, "plugin_icon", None))
                btn.clicked.connect(lambda _, i=visible_count: self._switch(i))
                self.sidebar_layout.addWidget(btn)
                self.sidebar_buttons.append(btn)

                visible_count += 1

            except Exception:
                traceback.print_exc()

        if visible_count > 0:
            self.stack.setCurrentIndex(0)
            self.sidebar_buttons[0].setChecked(True)
        else:
            # 如果没有权限访问任何插件
            no_access = QLabel("您当前没有访问任何功能的权限，请联系管理员。")
            no_access.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stack.addWidget(no_access)

    def _switch(self, index: int):
        self.stack.setCurrentIndex(index)
        for b in self.sidebar_buttons:
            b.setChecked(False)
        if index < len(self.sidebar_buttons):
            self.sidebar_buttons[index].setChecked(True)

        new_widget = self.stack.currentWidget()
        anim = QPropertyAnimation(new_widget, b"windowOpacity")
        new_widget.setWindowOpacity(0)
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { font-family: 'Microsoft YaHei'; }")

    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        window = MainWindow(login_dialog.user_info)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)