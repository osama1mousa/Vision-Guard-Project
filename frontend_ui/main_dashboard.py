import sys
import os
import datetime
import requests
import traceback
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, 
                             QStackedWidget, QScrollArea, QComboBox, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap

from styles import *
from network_workers import ZMQReceiver, APIWorker, SERVER_IP
from report_generator import generate_pdf_report

class VisionGuardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pulse_phase = 0.0
        self.current_log_filter = "ALL"
        self.cached_logs = []

        self.setWindowTitle("VisionGuard AI — Enterprise Security Dashboard (1080p HD)")
        self.resize(1400, 800)
        self.setMinimumSize(1100, 650)
        
        self.setStyleSheet(MAIN_STYLESHEET)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.create_sidebar()
        
        self.pages_stack = QStackedWidget()
        self.main_layout.addWidget(self.pages_stack, 1)

        self.create_dashboard_page()
        self.create_event_logs_page()
        self.create_reports_page()

        self.switch_page("DASHBOARD")

        self.video_receiver = ZMQReceiver()
        self.video_receiver.frame_ready.connect(self.update_video_feed)
        self.video_receiver.connection_lost.connect(self.show_no_signal)
        self.video_receiver.start()

        self.api_worker = APIWorker()
        self.api_worker.logs_ready.connect(self.populate_ui_logs)
        self.api_worker.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_and_clock)
        self.timer.start(500)

    def switch_page(self, page_name):
        for name, btn in self.nav_buttons.items():
            btn.setObjectName("nav_active" if name == page_name else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if page_name == "DASHBOARD": self.pages_stack.setCurrentWidget(self.page_dashboard)
        elif page_name == "EVENT LOGS": self.pages_stack.setCurrentWidget(self.page_logs)
        elif page_name == "REPORTS": self.pages_stack.setCurrentWidget(self.page_reports)

    def set_log_filter(self, filter_type):
        self.current_log_filter = filter_type
        for f, btn in self.filter_buttons.items():
            btn.setObjectName("filter_active" if f == filter_type else "filter_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        temp_logs = self.cached_logs
        self.cached_logs = []
        self.populate_ui_logs(temp_logs)

    def take_manual_snapshot(self):
        pixmap = self.video_label.pixmap()
        if pixmap:
            image = pixmap.toImage()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            image.save(buffer, "JPG")
            img_bytes = buffer.data().data()
            
            def send_snap():
                try: requests.post(f"http://{SERVER_IP}:8000/api/snapshot", files={"file": ("snapshot.jpg", img_bytes, "image/jpeg")})
                except: pass
            
            threading.Thread(target=send_snap, daemon=True).start()
            
            self.snap_btn.setText("SNAPSHOT SAVED")
            self.snap_btn.setStyleSheet(f"background-color: {BG_CARD}; color: {ACCENT_GREEN}; font-weight: bold; border-radius: 6px; border: 1px solid {ACCENT_GREEN}; padding: 6px 12px;")
            QTimer.singleShot(2000, lambda: self.snap_btn.setText("CAPTURE FRAME"))
            QTimer.singleShot(2000, lambda: self.snap_btn.setStyleSheet(f"background-color: {BG_CARD_HOVER}; color: {ACCENT_CYAN}; font-weight: bold; border-radius: 6px; border: 1px solid {ACCENT_CYAN}; padding: 6px 12px;"))

    def export_pdf_report(self):
        self.pdf_btn.setText("GENERATING...") 
        QApplication.processEvents()

        selected_period = self.report_combo.currentText().lower()
        success = generate_pdf_report(report_period=selected_period) 
        
        if success:
            self.pdf_btn.setText("EXPORT COMPLETE")
            self.pdf_btn.setStyleSheet(f"background-color: {BG_CARD}; color: {ACCENT_GREEN}; font-weight: bold; padding: 8px 15px; border-radius: 6px; border: 1px solid {ACCENT_GREEN};")
        else:
            self.pdf_btn.setText("EXPORT FAILED!")
            self.pdf_btn.setStyleSheet(f"background-color: {BG_CARD}; color: {ACCENT_RED}; font-weight: bold; padding: 8px 15px; border-radius: 6px; border: 1px solid {ACCENT_RED};")
            
        QTimer.singleShot(3000, self.reset_pdf_btn)

    def reset_pdf_btn(self):
        self.pdf_btn.setText("EXPORT PDF REPORT")
        self.pdf_btn.setStyleSheet(f"background-color: {ACCENT_CYAN}; color: black; font-weight: bold; padding: 8px 15px; border-radius: 6px;")

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(15, 25, 15, 20)

        logo_lay = QHBoxLayout()
        icon = QLabel("◈")
        icon.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 32px; font-weight: bold;")
        title = QLabel("VISIONGUARD")
        title.setStyleSheet("font-size: 18px; font-weight: bold; letter-spacing: 1px;")
        logo_lay.addWidget(icon)
        logo_lay.addWidget(title, 1)
        lay.addLayout(logo_lay)

        lay.addSpacing(30)
        nav_lbl = QLabel("NAVIGATION")
        nav_lbl.setObjectName("text_dim")
        nav_lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
        lay.addWidget(nav_lbl)

        menus = [("DASHBOARD", "DASHBOARD"), ("EVENT LOGS", "EVENT LOGS"), ("REPORTS", "REPORTS")]
        self.nav_buttons = {}
        for text, key in menus:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, k=key: self.switch_page(k))
            lay.addWidget(btn)
            self.nav_buttons[key] = btn

        lay.addStretch()
        self.main_layout.addWidget(sidebar)

    def create_scroll_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        return scroll, layout

    def create_dashboard_page(self):
        self.page_dashboard = QWidget()
        self.pages_stack.addWidget(self.page_dashboard)
        lay = QHBoxLayout(self.page_dashboard)
        lay.setContentsMargins(15, 15, 0, 0)

        main_content = QWidget()
        mlay = QVBoxLayout(main_content)
        mlay.setContentsMargins(0, 0, 15, 15)

        top_bar = QHBoxLayout()
        status_fr = QFrame()
        status_fr.setObjectName("card")
        slay = QHBoxLayout(status_fr)
        slay.setContentsMargins(15, 5, 15, 5)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 14px;")
        self.status_lbl = QLabel("SYSTEM ACTIVE — ALL FEEDS ONLINE")
        self.status_lbl.setStyleSheet(f"color: {ACCENT_GREEN}; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        slay.addWidget(self.status_dot)
        slay.addWidget(self.status_lbl)
        top_bar.addWidget(status_fr)
        top_bar.addStretch()

        clock_fr = QFrame()
        clock_fr.setObjectName("card")
        clay = QHBoxLayout(clock_fr)
        clay.setContentsMargins(15, 5, 15, 5)
        self.time_lbl = QLabel("00:00:00")
        self.time_lbl.setStyleSheet("font-family: Consolas, Courier; font-size: 18px; font-weight: bold; letter-spacing: 2px;")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clay.addWidget(self.time_lbl)
        top_bar.addWidget(clock_fr)
        mlay.addLayout(top_bar)

        vid_fr = QFrame(objectName="card")
        vlay = QVBoxLayout(vid_fr)
        vh = QHBoxLayout()
        vh.addWidget(QLabel("◉  LIVE 1080p FEED — EXTERNAL HD CAM", styleSheet="font-weight: bold; letter-spacing: 0.5px;"))
        vh.addStretch()
        
        self.snap_btn = QPushButton("CAPTURE FRAME")
        self.snap_btn.setStyleSheet(f"background-color: {BG_CARD_HOVER}; color: {ACCENT_CYAN}; font-weight: bold; border-radius: 6px; border: 1px solid {ACCENT_CYAN}; padding: 6px 12px;")
        self.snap_btn.clicked.connect(self.take_manual_snapshot)
        vh.addWidget(self.snap_btn)
        
        self.rec_dot = QLabel("  ● REC")
        self.rec_dot.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold; font-size: 11px;")
        vh.addWidget(self.rec_dot)
        vlay.addLayout(vh)

        self.video_label = QLabel("INITIALIZING 1080p AI ENGINE...")
        self.video_label.setStyleSheet("background-color: #000; border-radius: 6px; font-weight: bold; color: #333;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        mlay.addWidget(vid_fr, 1)
        vlay.addWidget(self.video_label) 
        vlay.addStretch() 

        lay.addWidget(main_content, 1)

        right_panel = QFrame(objectName="panel")
        right_panel.setFixedWidth(320)
        rlay = QVBoxLayout(right_panel)
        rlay.setContentsMargins(15, 20, 15, 20)

        rlay.addWidget(QLabel("TRUSTED PERSONNEL", objectName="text_dim", styleSheet="font-weight: bold;"))
        personnel = [("Nourullah", ACCENT_GREEN), ("Osama", ACCENT_CYAN), ("Vael", ACCENT_CYAN), ("Mohamad", ACCENT_AMBER)]
        
        for name, color in personnel:
            p = QFrame(objectName="card")
            pl = QHBoxLayout(p)
            pl.setContentsMargins(10, 5, 10, 5)
            
            av = QLabel()
            av.setFixedSize(30, 30)
            
            img_path = None
            folder_path = f"faces/{name}"
            if os.path.exists(folder_path):
                for file_name in os.listdir(folder_path):
                    if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                        img_path = f"{folder_path}/{file_name}".replace('\\', '/')
                        break
            
            if img_path:
                av.setStyleSheet(f"border-image: url('{img_path}') 0 0 0 0 stretch stretch; border-radius: 15px;")
            else:
                av.setText(name[0])
                av.setAlignment(Qt.AlignmentFlag.AlignCenter)
                av.setStyleSheet(f"background-color: {color}; color: #000; font-weight: bold; border-radius: 15px;")
                
            pl.addWidget(av)
            pl.addWidget(QLabel(f"<b>{name}</b>"))
            pl.addStretch()
            pl.addWidget(QLabel("●", styleSheet=f"color: {ACCENT_GREEN};"))
            rlay.addWidget(p)

        rlay.addSpacing(15)
        rlay.addWidget(QLabel("LIVE EVENT LOG", objectName="text_dim", styleSheet="font-weight: bold;"))
        
        self.dash_log_scroll, self.dash_log_layout = self.create_scroll_area()
        rlay.addWidget(self.dash_log_scroll, 1)

        lay.addWidget(right_panel)

    def create_event_logs_page(self):
        self.page_logs = QFrame(objectName="panel")
        self.pages_stack.addWidget(self.page_logs)
        lay = QVBoxLayout(self.page_logs)
        lay.setContentsMargins(30, 30, 30, 30)

        lay.addWidget(QLabel("EVENT LOGS", styleSheet="font-size: 24px; font-weight: bold; letter-spacing: 1px;"))
        lay.addWidget(QLabel("Real-time dynamic feed from the VisionGuard Database.", objectName="text_sec"))
        
        flay = QHBoxLayout()
        self.filter_buttons = {}
        for f in ["ALL", "THREAT", "ACCESS"]:
            btn = QPushButton(f)
            btn.setObjectName("filter_btn")
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda checked, f_type=f: self.set_log_filter(f_type))
            flay.addWidget(btn)
            self.filter_buttons[f] = btn
            
        flay.addStretch()
        lay.addLayout(flay)

        table_fr = QFrame(objectName="card")
        tlay = QVBoxLayout(table_fr)
        
        hlay = QHBoxLayout()
        hlay.addWidget(QLabel("#", styleSheet="font-weight:bold;", objectName="text_dim"), 1)
        hlay.addWidget(QLabel("TIMESTAMP", styleSheet="font-weight:bold;", objectName="text_dim"), 3)
        hlay.addWidget(QLabel("EVENT DETAILS", styleSheet="font-weight:bold;", objectName="text_dim"), 5)
        hlay.addWidget(QLabel("STATUS", styleSheet="font-weight:bold;", objectName="text_dim", alignment=Qt.AlignmentFlag.AlignRight), 2)
        tlay.addLayout(hlay)
        
        line = QFrame(styleSheet=f"background-color: {BORDER_DIM};")
        line.setFixedHeight(1)
        tlay.addWidget(line)

        self.full_log_scroll, self.full_log_layout = self.create_scroll_area()
        tlay.addWidget(self.full_log_scroll, 1)
        lay.addWidget(table_fr, 1)

    def create_reports_page(self):
        self.page_reports = QFrame(objectName="panel")
        self.pages_stack.addWidget(self.page_reports)
        lay = QVBoxLayout(self.page_reports)
        lay.setContentsMargins(30, 30, 30, 30)

        header_lay = QHBoxLayout()
        title_lay = QVBoxLayout()
        title_lay.addWidget(QLabel("INCIDENT REPORTS", styleSheet="font-size: 24px; font-weight: bold; letter-spacing: 1px;"))
        title_lay.addWidget(QLabel("Select a timeframe and generate an official PDF report.", objectName="text_sec"))
        header_lay.addLayout(title_lay)
        header_lay.addStretch()

        self.report_combo = QComboBox()
        self.report_combo.addItems(["Hourly", "Daily", "Weekly", "Monthly"])
        self.report_combo.setFixedWidth(150)
        header_lay.addWidget(self.report_combo)
        
        self.pdf_btn = QPushButton("EXPORT PDF REPORT")
        self.pdf_btn.setStyleSheet(f"background-color: {ACCENT_CYAN}; color: black; font-weight: bold; padding: 8px 15px; border-radius: 6px;")
        self.pdf_btn.clicked.connect(self.export_pdf_report)
        header_lay.addWidget(self.pdf_btn)

        lay.addLayout(header_lay)
        lay.addSpacing(15)

        table_fr = QFrame(objectName="card")
        tlay = QVBoxLayout(table_fr)
        self.reports_scroll, self.reports_layout = self.create_scroll_area()
        tlay.addWidget(self.reports_scroll, 1)
        lay.addWidget(table_fr, 1)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

    def populate_ui_logs(self, recent_logs):
        valid_logs = []
        for log in recent_logs:
            valid_logs.append(log)

        if valid_logs == self.cached_logs:
            return

        self.cached_logs = valid_logs
        
        try:
            self.clear_layout(self.dash_log_layout)
            self.clear_layout(self.full_log_layout)
            self.clear_layout(self.reports_layout)

            full_log_counter = 1

            for index, (event, status, timestamp) in enumerate(self.cached_logs):
                if status == "VERIFIED": color, badge_bg, icon = ACCENT_GREEN, "#0A2E1F", "VERIFIED"
                elif status == "THREAT": color, badge_bg, icon = ACCENT_RED, "#2E0A14", "THREAT"
                elif status == "UNAUTH": color, badge_bg, icon = ACCENT_AMBER, "#2E250A", "UNAUTH"
                elif status == "SNAPSHOT": color, badge_bg, icon = ACCENT_GREEN, "#0A2E1F", "SNAP"
                else: color, badge_bg, icon = ACCENT_CYAN, "#0A1F2E", "INFO"

                if index < 10:
                    dcard = QFrame(objectName="card")
                    dlay = QHBoxLayout(dcard)
                    dlay.setContentsMargins(0, 5, 10, 5)
                    strip = QFrame(styleSheet=f"background-color: {color}; border-radius: 2px;")
                    strip.setFixedSize(4, 40)
                    dlay.addWidget(strip)
                    dlay.addWidget(QLabel(f"<b>{event}</b><br><span style='color:{TEXT_SECONDARY}; font-size:10px;'>{timestamp}</span>"), 1)
                    badge = QLabel(icon)
                    badge.setStyleSheet(f"background-color: {badge_bg}; color: {color}; font-size: 9px; font-weight: bold; padding: 3px 8px; border-radius: 5px;")
                    dlay.addWidget(badge)
                    self.dash_log_layout.addWidget(dcard)

                if status != "INFO":
                    show_log = False
                    if self.current_log_filter == "ALL":
                        show_log = True
                    elif self.current_log_filter == "ACCESS" and status in ["VERIFIED", "UNAUTH"]:
                        show_log = True
                    elif self.current_log_filter == status:
                        show_log = True

                    if show_log:
                        row = QFrame()
                        rlay = QHBoxLayout(row)
                        rlay.addWidget(QLabel(str(full_log_counter), objectName="text_sec"), 1)
                        rlay.addWidget(QLabel(timestamp), 3)
                        rlay.addWidget(QLabel(f"<b>{event}</b>"), 5)
                        b = QLabel(icon)
                        b.setStyleSheet(f"color: {color}; border: 1px solid {color}; padding: 4px 10px; border-radius: 6px; font-weight:bold; font-size:10px;")
                        b.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        rlay.addWidget(b, 2, Qt.AlignmentFlag.AlignRight)
                        self.full_log_layout.addWidget(row)
                        line = QFrame(styleSheet=f"background-color: {BORDER_DIM};")
                        line.setFixedHeight(1)
                        self.full_log_layout.addWidget(line)
                        full_log_counter += 1

                rrow = QFrame()
                rrlay = QHBoxLayout(rrow)
                dt_parts = timestamp.split(" ")
                if len(dt_parts) == 2:
                    rrlay.addWidget(QLabel(f"<span style='color:{TEXT_SECONDARY}; font-size:11px;'>{dt_parts[0]}</span><br><span>{dt_parts[1]}</span>"), 2)
                rrlay.addWidget(QLabel(f"<b>{event}</b>"), 6)
                rb = QLabel(icon)
                rb.setStyleSheet(f"color: {color}; border: 1px solid {color}; padding: 4px 10px; border-radius: 6px; font-weight:bold; font-size:10px;")
                rrlay.addWidget(rb, 2, Qt.AlignmentFlag.AlignRight)
                self.reports_layout.addWidget(rrow)
                line = QFrame(styleSheet=f"background-color: {BORDER_DIM};")
                line.setFixedHeight(1)
                self.reports_layout.addWidget(line)
        except Exception as e:
            print(f"UI Population Error: {e}")

    def animate_and_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_lbl.setText(now)
        
        self.pulse_phase += 1
        if self.pulse_phase % 2 == 0:
            self.rec_dot.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold; font-size: 11px;")
            self.status_dot.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 14px;")
        else:
            self.rec_dot.setStyleSheet(f"color: {BG_DARK}; font-weight: bold; font-size: 11px;")
            self.status_dot.setStyleSheet(f"color: #007A4E; font-size: 14px;")

    def update_video_feed(self, qt_image):
        self.status_lbl.setText("SYSTEM ACTIVE — EXTERNAL HD FEED ONLINE")
        self.status_lbl.setStyleSheet(f"color: {ACCENT_GREEN}; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        try:
            target_width = self.video_label.width()
            target_height = int(target_width * (9 / 16))
            
            self.video_label.setFixedHeight(target_height)
            
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                target_width, 
                target_height, 
                Qt.AspectRatioMode.IgnoreAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
        except: pass

    def show_no_signal(self):
        self.status_lbl.setText("WARNING — CONNECTION LOST")
        self.status_lbl.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")

    def closeEvent(self, event):
        self.video_receiver.stop()
        self.api_worker.terminate()
        event.accept()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = VisionGuardApp()
        window.show()
        sys.exit(app.exec())
    except Exception:
        print("CRITICAL UI ERROR:")
        traceback.print_exc()