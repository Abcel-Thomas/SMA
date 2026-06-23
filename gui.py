import sys
import os
import datetime

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QTextEdit, QSplitter, QHeaderView,
    QDialog, QLabel, QGridLayout, QCheckBox
)
# pyrefly: ignore [missing-import]
from PyQt6.QtCore import Qt

# 🔥 BACKEND
from core.preview import generate_preview
from core.scanner import scan_files
from core.worker import RenameWorker
from core.security import generate_report, calculate_suspicion


class DashboardDialog(QDialog):
    def __init__(self, folder_path, metrics, type_distribution, risky_files=None, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.metrics = metrics
        self.type_distribution = type_distribution
        self.risky_files = risky_files or []
        self.setWindowTitle("📊 Security Analysis Dashboard")
        self.resize(800, 600)
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 🎯 SUMMARY CARDS
        cards_layout = QHBoxLayout()
        total_card = self.create_card("Total Files Scanned", str(self.metrics.get("total", 0)), "#1e293b", "#00f5ff")
        safe_card = self.create_card("Safe Files", str(self.metrics.get("Safe", 0)), "#1e293b", "#22c55e")
        suspicious_count = self.metrics.get("Low", 0) + self.metrics.get("Medium", 0) + self.metrics.get("High", 0) + self.metrics.get("Critical", 0)
        suspicious_card = self.create_card("Suspicious/Dangerous", str(suspicious_count), "#1e293b", "#ef4444")

        cards_layout.addWidget(total_card)
        cards_layout.addWidget(safe_card)
        cards_layout.addWidget(suspicious_card)
        
        layout.addLayout(cards_layout)

        # 📊 CHART
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.plot_chart()

        # 📥 EXPORT BUTTON
        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("📥 Export PDF Report")
        self.btn_export.clicked.connect(self.export_pdf)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_export)
        
        layout.addLayout(btn_layout)

    def create_card(self, title, value, bg_color, text_color):
        card = QWidget()
        card_layout = QVBoxLayout(card)
        
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"color: white; font-size: 14px; font-weight: bold;")
        
        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setStyleSheet(f"color: {text_color}; font-size: 32px; font-weight: bold;")
        
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(val_lbl)
        card.setStyleSheet(f"background-color: {bg_color}; border-radius: 10px; padding: 10px;")
        
        return card

    def plot_chart(self):
        ax = self.fig.add_subplot(111)
        ax.clear()
        
        labels = ['Safe', 'Low', 'Medium', 'High', 'Critical']
        sizes = [self.metrics.get(l, 0) for l in labels]
        colors = ['#22c55e', '#eab308', '#f97316', '#ef4444', '#7f1d1d']
        
        # Filter out zero values for better pie chart
        filtered_labels = [l for i, l in enumerate(labels) if sizes[i] > 0]
        filtered_sizes = [s for s in sizes if s > 0]
        filtered_colors = [c for i, c in enumerate(colors) if sizes[i] > 0]
        
        if not filtered_sizes:
            ax.text(0.5, 0.5, "No Data to Display", horizontalalignment='center', verticalalignment='center', color='white')
            ax.axis('off')
        else:
            # pyrefly: ignore [bad-unpacking]
            wedges, texts, autotexts = ax.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors, autopct='%1.1f%%', startangle=90, textprops=dict(color="w"))
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            
        self.fig.patch.set_facecolor('#020617')
        self.canvas.draw()

    def export_pdf(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "", "PDF Files (*.pdf)")
        if not save_path:
            return
            
        try:
            # Save chart temporarily
            chart_path = "temp_chart.png"
            self.fig.savefig(chart_path, facecolor='#020617')
            
            from core.report_generator import PDFReportGenerator
            generator = PDFReportGenerator(save_path)
            generator.generate_report(self.folder_path, self.metrics, self.type_distribution, self.risky_files, chart_path)
            
            # Clean up temp image
            if os.path.exists(chart_path):
                os.remove(chart_path)
                
            QMessageBox.information(self, "Success", f"Report saved successfully to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QPushButton {
                background-color: #0ea5e9;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #38bdf8;
            }
        """)


class SmartRenameUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("⚡ SmartRename AI PRO")
        self.resize(1200, 800)

        self.current_folder = None
        self.worker = None

        self.init_ui()
        self.apply_styles()

    # =========================
    # 🧱 UI SETUP
    # =========================
    def init_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # MAIN HORIZONTAL LAYOUT (Sidebar + Content)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =========================
        # ⬅️ SIDEBAR
        # =========================
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(80)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 30, 10, 30)
        sidebar_layout.setSpacing(20)

        # Sidebar icons (using text as placeholders for icons)
        for icon in ["🏠", "📁", "📊", "⚙️"]:
            btn = QPushButton(icon)
            btn.setObjectName("sidebarBtn")
            btn.setFixedSize(50, 50)
            sidebar_layout.addWidget(btn)
        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)

        # =========================
        # 🖥️ RIGHT CONTENT AREA
        # =========================
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # 🔘 TOP TOOLBAR
        toolbar = QWidget()
        toolbar.setObjectName("glassPanel")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)

        self.btn_browse = QPushButton("📂 Browse")
        self.btn_preview = QPushButton("👀 Preview")
        self.btn_run = QPushButton("🚀 Run")
        self.btn_stop = QPushButton("🛑 Stop")
        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_duplicates = QPushButton("🔍 Find Duplicates")
        
        self.chk_deep_mode = QCheckBox("🧠 Deep Mode")
        self.chk_deep_mode.setChecked(True)

        # Hybrid Mode Toggle
        from core.mode_manager import get_current_mode
        self.current_mode = get_current_mode()
        self.btn_mode_toggle = QPushButton()
        self.btn_mode_toggle.setToolTip("Offline: fully private, slower.\nOnline: faster, uses cloud APIs with only summarized data sent.")
        self._update_mode_button_appearance()
        self.btn_mode_toggle.clicked.connect(self.toggle_mode)

        for btn in [self.btn_browse, self.btn_preview, self.btn_run, self.btn_stop, self.btn_dashboard, self.btn_duplicates, self.btn_mode_toggle, self.chk_deep_mode]:
            if isinstance(btn, QPushButton):
                btn.setObjectName("actionBtn")
            toolbar_layout.addWidget(btn)

        self.btn_browse.clicked.connect(self.open_folder)
        self.btn_preview.clicked.connect(self.preview_files)
        self.btn_run.clicked.connect(self.run_rename)
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_dashboard.clicked.connect(self.open_dashboard)
        self.btn_duplicates.clicked.connect(self.run_duplicate_scan)

        content_layout.addWidget(toolbar)

        # 📂 MIDDLE SPLITTER (Tree + Table + AI Analysis)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")

        # Tree Container
        tree_container = QWidget()
        tree_container.setObjectName("glassPanel")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Folders")
        self.tree.itemClicked.connect(self.on_folder_click)
        tree_layout.addWidget(self.tree)

        # Table Container
        table_container = QWidget()
        table_container.setObjectName("glassPanel")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(10, 10, 10, 10)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["File", "Size", "Type", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.itemClicked.connect(self.on_file_click)
        table_layout.addWidget(self.table)

        # AI Analysis Panel
        self.analysis_panel = QWidget()
        self.analysis_panel.setObjectName("glassPanel")
        analysis_layout = QVBoxLayout(self.analysis_panel)
        analysis_layout.setContentsMargins(15, 15, 15, 15)
        analysis_layout.setSpacing(10)

        title_lbl = QLabel("🧠 AI Analysis")
        title_lbl.setStyleSheet("color: #00f5ff; font-size: 16px; font-weight: bold;")
        analysis_layout.addWidget(title_lbl)

        self.lbl_file_name = QLabel("Select a file to analyze")
        self.lbl_file_name.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self.lbl_file_name.setWordWrap(True)
        analysis_layout.addWidget(self.lbl_file_name)

        self.lbl_file_details = QLabel("-- | --")
        self.lbl_file_details.setStyleSheet("color: #94a3b8; font-size: 12px;")
        analysis_layout.addWidget(self.lbl_file_details)

        # Progress Ring Placeholder
        self.lbl_risk_score = QLabel("Score: --")
        self.lbl_risk_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_risk_score.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background-color: rgba(255,255,255,10); border-radius: 40px; min-height: 80px; min-width: 80px; margin: 10px;")
        analysis_layout.addWidget(self.lbl_risk_score)

        self.lbl_risk_level = QLabel("Status: Unknown")
        self.lbl_risk_level.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_risk_level.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold;")
        analysis_layout.addWidget(self.lbl_risk_level)

        remarks_lbl = QLabel("AI Remarks:")
        remarks_lbl.setStyleSheet("color: #00f5ff; font-weight: bold; margin-top: 10px;")
        analysis_layout.addWidget(remarks_lbl)

        self.txt_remarks = QTextEdit()
        self.txt_remarks.setReadOnly(True)
        self.txt_remarks.setStyleSheet("background: transparent; color: #e2e8f0; font-size: 12px; border: none;")
        analysis_layout.addWidget(self.txt_remarks)

        splitter.addWidget(tree_container)
        splitter.addWidget(table_container)
        splitter.addWidget(self.analysis_panel)
        splitter.setSizes([250, 550, 300])

        content_layout.addWidget(splitter, stretch=2)

        # 🧠 BOTTOM AI DASHBOARD
        dashboard_bottom = QWidget()
        dashboard_bottom.setObjectName("glassPanel")
        dash_layout = QHBoxLayout(dashboard_bottom)
        dash_layout.setContentsMargins(15, 15, 15, 15)
        dash_layout.setSpacing(15)

        # Log Section
        log_section = QVBoxLayout()
        log_label = QLabel("⚡ Activity Log")
        log_label.setStyleSheet("color: #00f5ff; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        log_section.addWidget(log_label)
        log_section.addWidget(self.log_box)

        # Insights Section
        insights_section = QVBoxLayout()
        insights_label = QLabel("🧠 AI Insights")
        insights_label.setStyleSheet("color: #00f5ff; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        
        self.insight_text = QLabel("Drag & Drop Zone Active\nNeural Network: Ready\nDeep Mode: Enabled")
        self.insight_text.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent; border: none;")
        self.insight_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        upload_zone = QLabel("📥 Drop Files Here")
        upload_zone.setObjectName("uploadZone")
        upload_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)

        insights_section.addWidget(insights_label)
        insights_section.addWidget(self.insight_text)
        insights_section.addWidget(upload_zone)

        dash_layout.addLayout(log_section, stretch=3)
        dash_layout.addLayout(insights_section, stretch=1)

        content_layout.addWidget(dashboard_bottom, stretch=1)

        main_layout.addWidget(content_widget)

    # =========================
    # 🧠 LOG
    # =========================
    def log(self, msg):
        self.log_box.append(msg)

    # =========================
    # ⚡ HYBRID MODE
    # =========================
    def toggle_mode(self):
        from core.mode_manager import set_mode
        if self.current_mode == "offline":
            self.current_mode = "online"
        else:
            self.current_mode = "offline"
            
        set_mode(self.current_mode)
        self._update_mode_button_appearance()
        self.log(f"⚡ Mode switched to: {self.current_mode.upper()}")

    def _update_mode_button_appearance(self):
        if self.current_mode == "offline":
            self.btn_mode_toggle.setText("🔒 Offline Mode")
            self.btn_mode_toggle.setStyleSheet("color: #94a3b8;")
        else:
            self.btn_mode_toggle.setText("⚡ Online Mode")
            self.btn_mode_toggle.setStyleSheet("color: #fbbf24;")

    # =========================
    # 📂 OPEN FOLDER
    # =========================
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")

        if folder:
            self.current_folder = folder
            self.log(f"📂 Selected: {folder}")

            self.load_tree(folder)
            self.load_files(folder)
            
            # Start duplicate check automatically
            self.run_duplicate_scan()

    # =========================
    # 🌳 TREE
    # =========================
    def load_tree(self, path):
        self.tree.clear()

        root = QTreeWidgetItem(self.tree, [os.path.basename(path)])
        root.setData(0, Qt.ItemDataRole.UserRole, path)

        self.add_subfolders(root, path)
        self.tree.expandAll()

    def add_subfolders(self, parent, path):
        try:
            for item in os.listdir(path):
                full = os.path.join(path, item)

                if os.path.isdir(full):
                    child = QTreeWidgetItem(parent, [item])
                    child.setData(0, Qt.ItemDataRole.UserRole, full)

                    self.add_subfolders(child, full)
        except Exception:
            pass

    # =========================
    # 📄 LOAD FILES INTO TABLE
    # =========================
    def load_files(self, folder):
        self.table.setRowCount(0)

        for file in os.listdir(folder):
            full = os.path.join(folder, file)

            if os.path.isfile(full):
                row = self.table.rowCount()
                self.table.insertRow(row)

                # 📄 Name
                file_name = file

                # 📦 Size
                size_kb = os.path.getsize(full) / 1024

                # 🏷 Type
                ext = os.path.splitext(file)[1]

                # 🕒 Date
                timestamp = os.path.getmtime(full)
                date = datetime.datetime.fromtimestamp(timestamp)
                date_str = date.strftime("%Y-%m-%d %H:%M:%S")

                # 🧱 Insert
                name_item = QTableWidgetItem(file_name)
                name_item.setData(Qt.ItemDataRole.UserRole, full)
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, QTableWidgetItem(f"{size_kb:.2f} KB"))
                self.table.setItem(row, 2, QTableWidgetItem(ext))
                self.table.setItem(row, 3, QTableWidgetItem(date_str))

    def on_folder_click(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)

        if path:
            self.load_files(path)

    def on_file_click(self, item):
        row = item.row()
        name_item = self.table.item(row, 0)
        size_item = self.table.item(row, 1)
        type_item = self.table.item(row, 2)
        if name_item:
            full_path = name_item.data(Qt.ItemDataRole.UserRole)
            if full_path:
                file_name = name_item.text()
                file_size = size_item.text() if size_item else "--"
                file_type = type_item.text() if type_item else "--"

                self.lbl_file_name.setText(file_name)
                self.lbl_file_details.setText(f"{file_size} | {file_type}")
                self.lbl_risk_score.setText("...")
                self.lbl_risk_level.setText("Analyzing...")
                self.lbl_risk_level.setStyleSheet("color: #eab308; font-size: 14px; font-weight: bold;")
                self.txt_remarks.setText("AI is analyzing this file...\nEvaluating contents and checking against neural heuristics.")

                self.show_file_report(full_path)

    def show_file_report(self, file_path):
        self.log(f"📄 Generating report for {os.path.basename(file_path)}...")
        
        from core.worker import FileReportWorker
        self.report_worker = FileReportWorker(file_path)
        self.report_worker.log_signal.connect(self.log)
        self.report_worker.done_signal.connect(self.on_file_report_done)
        self.report_worker.start()

    def on_file_report_done(self, report_text, status):
        # Update the AI Analysis Panel directly, no popups
        if status == "Suspicious":
            self.lbl_risk_score.setText("⚠️")
            self.lbl_risk_level.setText("DANGEROUS")
            self.lbl_risk_level.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
            self.lbl_risk_score.setStyleSheet("color: #ef4444; font-size: 32px; font-weight: bold; background-color: rgba(239,68,68,20); border-radius: 40px; min-height: 80px; min-width: 80px; margin: 10px;")
        else:
            self.lbl_risk_score.setText("✓")
            self.lbl_risk_level.setText("SAFE")
            self.lbl_risk_level.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
            self.lbl_risk_score.setStyleSheet("color: #22c55e; font-size: 32px; font-weight: bold; background-color: rgba(34,197,94,20); border-radius: 40px; min-height: 80px; min-width: 80px; margin: 10px;")
            
        self.txt_remarks.setText(report_text)

    # =========================
    # 👀 PREVIEW
    # =========================
    def preview_files(self):
        if not self.current_folder:
            QMessageBox.warning(self, "Error", "Select folder first")
            return

        files = scan_files(self.current_folder)
        is_deep = self.chk_deep_mode.isChecked()
        
        self.log("📋 Preview started...\n")
        self.btn_preview.setEnabled(False)
        
        from core.worker import PreviewWorker
        self.preview_worker = PreviewWorker(files, deep_mode=is_deep)
        self.preview_worker.log_signal.connect(self.log)
        self.preview_worker.done_signal.connect(self.on_preview_done)
        self.preview_worker.start()

    def on_preview_done(self, preview_data):
        self.btn_preview.setEnabled(True)
        self.log(f"\nTotal: {len(preview_data)} files previewed.")

    # =========================
    # 🚀 RUN
    # =========================
    def run_rename(self):
        if not self.current_folder:
            QMessageBox.warning(self, "Error", "Select folder first")
            return

        files = scan_files(self.current_folder)

        is_deep = self.chk_deep_mode.isChecked()
        self.worker = RenameWorker(files, deep_mode=is_deep)

        self.worker.log_signal.connect(self.log)
        self.worker.done_signal.connect(lambda: self.log("🎉 Done!"))

        self.worker.start()

    # =========================
    # 🔍 DUPLICATE SCANNER
    # =========================
    def run_duplicate_scan(self):
        if not self.current_folder:
            QMessageBox.warning(self, "Error", "Select folder first")
            return

        files = scan_files(self.current_folder)
        if not files:
            return

        self.log("🔍 Scanning for duplicate files...")
        self.btn_duplicates.setEnabled(False)

        from core.worker import DuplicateScannerWorker
        self.duplicate_worker = DuplicateScannerWorker(files)
        self.duplicate_worker.log_signal.connect(self.log)
        self.duplicate_worker.done_signal.connect(self.on_duplicates_found)
        self.duplicate_worker.start()

    def on_duplicates_found(self, duplicates):
        self.btn_duplicates.setEnabled(True)
        if not duplicates:
            self.log("✅ No duplicates found.")
            return

        self.log(f"⚠️ Found {len(duplicates)} duplicate files.")
        
        # Ask user for deletion
        reply = QMessageBox.question(
            self, 
            "Duplicate Files Found",
            f"Found {len(duplicates)} duplicate files in the folder.\n\nDo you want to delete them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for dup in duplicates:
                try:
                    os.remove(dup)
                    deleted_count += 1
                except Exception as e:
                    self.log(f"❌ Failed to delete {os.path.basename(dup)}: {e}")
            
            self.log(f"🗑️ Deleted {deleted_count} duplicate files.")
            self.load_files(self.current_folder) # Refresh table
        else:
            self.log("ℹ️ Duplicates were kept.")

    # =========================
    # 🛑 STOP
    # =========================
    def stop_process(self):
        if self.worker:
            self.worker.stop()
            self.log("🛑 Run stop requested...")
        if hasattr(self, 'preview_worker') and self.preview_worker:
            self.preview_worker.stop()
            self.log("🛑 Preview stop requested...")
        if hasattr(self, 'dashboard_worker') and self.dashboard_worker:
            self.dashboard_worker.stop()
            self.log("🛑 Dashboard analysis stop requested...")
        if hasattr(self, 'report_worker') and self.report_worker:
            self.report_worker.terminate()
            self.log("🛑 Report generation stop requested...")
        if hasattr(self, 'duplicate_worker') and self.duplicate_worker:
            self.duplicate_worker.stop()
            self.log("🛑 Duplicate scan stop requested...")

    # =========================
    # 📊 DASHBOARD
    # =========================
    def open_dashboard(self):
        if not self.current_folder:
            QMessageBox.warning(self, "Error", "Select a folder first to analyze.")
            return

        self.log("📊 Starting folder analysis for dashboard...")
        files = scan_files(self.current_folder)
        
        if not files:
            QMessageBox.warning(self, "Warning", "No files found in the selected folder.")
            return
            
        self.btn_dashboard.setEnabled(False)
        self.log("📊 Analyzing files in background...")

        from core.worker import DashboardWorker
        self.dashboard_worker = DashboardWorker(files)
        self.dashboard_worker.log_signal.connect(self.log)
        self.dashboard_worker.done_signal.connect(self.on_dashboard_done)
        self.dashboard_worker.start()

    def on_dashboard_done(self, metrics, type_distribution, risky_files):
        self.btn_dashboard.setEnabled(True)
        self.log(f"📊 Analysis complete: {metrics}")
        
        # Open Dashboard Dialog
        dialog = DashboardDialog(self.current_folder, metrics, type_distribution, risky_files, parent=self)
        dialog.exec()

    # =========================
    # 🎨 STYLE
    # =========================
    def apply_styles(self):
        # Apply modern font
        font = self.font()
        font.setFamily("Segoe UI")
        self.setFont(font)

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #020024, stop:0.5 #090979, stop:1 #00d4ff);
            }

            #centralWidget {
                background-color: qradialgradient(cx:0.5, cy:0.5, radius: 1, fx:0.5, fy:0.5, stop:0 rgba(20, 20, 50, 200), stop:1 rgba(5, 5, 20, 255));
            }

            #sidebar {
                background-color: rgba(0, 0, 0, 100);
                border-right: 1px solid rgba(255, 255, 255, 30);
            }

            #sidebarBtn {
                background-color: rgba(255, 255, 255, 10);
                border-radius: 15px;
                color: white;
                font-size: 20px;
                border: 1px solid rgba(255, 255, 255, 20);
            }
            #sidebarBtn:hover {
                background-color: rgba(0, 245, 255, 50);
                border: 1px solid rgba(0, 245, 255, 100);
            }

            #glassPanel {
                background-color: rgba(15, 23, 42, 180);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 20);
            }

            #actionBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #06b6d4);
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 50);
            }
            #actionBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #22d3ee);
                border: 1px solid white;
            }

            #uploadZone {
                background-color: rgba(0, 245, 255, 10);
                border: 2px dashed rgba(0, 245, 255, 150);
                border-radius: 15px;
                color: #00f5ff;
                font-weight: bold;
            }

            QTreeWidget, QTableWidget, QTextEdit {
                background-color: transparent;
                border: none;
                color: #e2e8f0;
                font-size: 13px;
            }
            QTreeWidget::item:selected, QTableWidget::item:selected {
                background-color: rgba(0, 245, 255, 50);
                color: white;
            }

            QHeaderView::section {
                background-color: rgba(255, 255, 255, 10);
                color: #00f5ff;
                padding: 5px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 20);
                font-weight: bold;
            }

            QCheckBox {
                color: white;
                font-weight: bold;
                background: transparent;
            }
            
            QLabel {
                background: transparent;
            }
            
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 50);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)


# =========================
# 🚀 ENTRY POINT
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartRenameUI()
    window.show()
    sys.exit(app.exec())