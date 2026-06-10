import datetime
import requests
import os
import sys
import traceback
from PyQt6.QtGui import QTextDocument, QPdfWriter
from PyQt6.QtWidgets import QApplication

def generate_pdf_report(report_period="daily", filename_prefix="VisionGuard_Security_Report"):
    print(f"⏳ Starting {report_period.upper()} PDF Generation...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(base_dir, "reports")
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    try:
        resp_struct = requests.get("http://127.0.0.1:8000/api/structured_logs", timeout=5)
        struct_logs = resp_struct.json() if resp_struct.status_code == 200 else []
    except Exception as e:
        struct_logs = []

    now = datetime.datetime.now()
    filtered_logs = []
    
    for log in struct_logs:
        start_time_str = log.get("start_time")
        if not start_time_str: continue 
            
        try:
            log_date = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            time_diff_seconds = (now - log_date).total_seconds()
            days_diff = (now - log_date).days
            
            if report_period.lower() == "hourly" and time_diff_seconds <= 3600:
                filtered_logs.append(log)
            elif report_period.lower() == "daily" and days_diff <= 1:
                filtered_logs.append(log)
            elif report_period.lower() == "weekly" and days_diff <= 7:
                filtered_logs.append(log)
            elif report_period.lower() == "monthly" and days_diff <= 30:
                filtered_logs.append(log)
            elif report_period.lower() == "all":
                filtered_logs.append(log)
        except ValueError:
            continue

    try:
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(reports_dir, f"{filename_prefix}_{report_period.upper()}_{timestamp}.pdf")
        writer = QPdfWriter(filename)
        
        html = f"""
        <h1 align="center" style="color:#2c3e50;">VisionGuard Security Report ({report_period.capitalize()})</h1>
        <p align="center" style="color:#555;"><b>Generated on:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        """
        
        # دالة بسيطة لطباعة القوائم بنفس الشكل تماماً
        def generate_html_section(title, category_key, logs, border_color, bg_color, title_color):
            section_html = f"<h2 style='color:{title_color};'>{title}</h2>"
            category_logs = [log for log in logs if log.get("category") == category_key]
            
            if not category_logs:
                section_html += "<p style='color:#777;'>No activity recorded during this period.</p>"
            else:
                for log in category_logs:
                    section_html += f"""
                    <table width="100%" style="background-color:{bg_color}; margin-bottom:10px; border:1px solid {border_color};"><tr><td style="padding:10px;">
                        <b style="color:{title_color};">Identifier:</b> {log.get('identifier')} | <b>Duration:</b> {log.get('duration')}<br>
                        <font color="#444"><b>Start:</b> {log.get('start_time')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>End:</b> {log.get('end_time')}</font>
                    </td></tr></table>
                    """
            return section_html

        html += generate_html_section("1. Authorized Personnel", "AUTHORIZED", filtered_logs, "#a3e4d7", "#eafaf1", "#27ae60")
        html += generate_html_section("2. Unauthorized Access", "UNAUTHORIZED", filtered_logs, "#f5cba7", "#fef5e7", "#e67e22")
        html += generate_html_section("3. Threat Detections (Weapons)", "THREAT", filtered_logs, "#f5b7b1", "#fdedec", "#c0392b")
        html += generate_html_section("4. After-Hours Activity", "AFTER_HOURS", filtered_logs, "#d7bde2", "#f4ecf7", "#8e44ad")

        doc = QTextDocument()
        doc.setHtml(html)
        doc.print(writer)
        
        print(f"✅ SUCCESS: {report_period.capitalize()} PDF Generated Successfully!")
        return True

    except Exception as e:
        print(" CRITICAL ERROR in generating PDF:")
        traceback.print_exc()
        return False