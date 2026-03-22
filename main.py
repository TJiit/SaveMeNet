import sys 
import os
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog,
    QMessageBox, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QDialog, QLineEdit  
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt
from QCustomQMainWindow import Ui_CustomMainWindow
from backend_logic import piiDetection, randomAnonymize, realisticAnonymize, restore_original_text
import pytesseract
from PIL import Image
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) #file path issue occured. Added later for error handling.
USERS_FILE = os.path.join(BASE_DIR, "users.json")
SESSION_FILE = os.path.join(BASE_DIR, "user_session.json")

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class RegisteredUserDialog(QDialog):
    def __init__(self):
        super().__init__()
        from PyQt5 import uic
        uic.loadUi("dialogRegisterdUser.ui", self)

        for widget in self.findChildren(QWidget):
            widget.setStyleSheet("color: white;")

        for line_edit in self.findChildren(QLineEdit):  #placeholder colour changed to accomdate background
        
            line_edit.setStyleSheet("""
                color: white;                    
                background-color: #333333;      
                selection-color: white;
                qlineedit::placeholder {          
                color: white;
            }
        """)

        if hasattr(self, "submit"):
            self.submit.clicked.connect(self.login_registered_user)

        self.logged_in_user = None

    def login_registered_user(self):
        username = self.userName.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Incomplete Data", "Please enter both username and password.")
            return

        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w") as f:
                json.dump({"users": []}, f)

        try:
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
                if "users" not in data:
                    data["users"] = []
        except:
            data = {"users": []}

        for user in data.get("users", []):
            if user.get("username", "").strip() == username and \
               user.get("password", "").strip() == password:

                self.logged_in_user = {
                    "username": username,
                    "email": user.get("email", "")
                }

                with open(SESSION_FILE, "w") as f:
                    json.dump(self.logged_in_user, f)

                QMessageBox.information(self, "Welcome", f"Welcome back, {username}!")
                self.accept()
                return

        QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        from PyQt5 import uic
        uic.loadUi("dialogLogin.ui", self)

        for widget in self.findChildren(QWidget):
            widget.setStyleSheet("color: white;")

        for line_edit in self.findChildren(QLineEdit):
            line_edit.setStyleSheet("""
                color: white;                    
                background-color: #333333;       
                selection-background-color: #555555;
                selection-color: white;
            """)

        if hasattr(self, "submit"):
            self.submit.clicked.connect(self.new_user_submit)
        if hasattr(self, "submit_2"):
            self.submit_2.clicked.connect(self.registered_user_click)

        self.logged_in_user = None

    def new_user_submit(self):
        username = self.userName.text().strip()
        password = self.password.text().strip()
        email = self.email.text().strip()

        if not username or not password or not email:
            QMessageBox.warning(self, "Incomplete Data", "Please fill all fields")
            return

        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r") as f:
                    data = json.load(f)
                    if "users" not in data:
                        data["users"] = []
            except:
                data = {"users": []}
        else:
            data = {"users": []}

        for user in data["users"]:
            if user.get("username", "").strip() == username:
                QMessageBox.warning(self, "Duplicate", "Username already exists")
                return

        data["users"].append({
            "username": username,
            "password": password,
            "email": email
        })

        with open(USERS_FILE, "w") as f:
            json.dump(data, f, indent=4)

        self.logged_in_user = {"username": username, "email": email}

        with open(SESSION_FILE, "w") as f:
            json.dump(self.logged_in_user, f)

        QMessageBox.information(self, "Welcome", f"Welcome, {username}!")
        self.accept()

    def registered_user_click(self):
        reg_dialog = RegisteredUserDialog()
        if reg_dialog.exec_() == QDialog.Accepted:
            self.logged_in_user = reg_dialog.logged_in_user
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self, user=None):
        super().__init__()
        self.user = user

        self.ui = Ui_CustomMainWindow()
        self.ui.setupUi(self)

        if hasattr(self.ui, "userButton"):
            self.ui.userButton.clicked.connect(self.open_user_page)
        if hasattr(self.ui, "loginButton"):
            self.ui.loginButton.clicked.connect(self.logout_user)

        self.update_counter("calNumber1")

        self.history_file = os.path.join(BASE_DIR, "document_history.json")
        self.history = []
        self.load_history()
        self.history_table = None

        self.filePath = None
        self.text_Original = ""
        self.currentText = ""
        self.piiDetection = []
        self.fileLoad = False

        self.viewer = QWebEngineView(self.ui.scrollAreaWidgetContents)
        if self.ui.scrollAreaWidgetContents.layout() is None:
            self.ui.scrollAreaWidgetContents.setLayout(QVBoxLayout())
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.viewer)

        self.buttons = [
            self.ui.homebutton,
            self.ui.anonymizebutton,
            self.ui.reportbutton,
            self.ui.settingsbutton,
            self.ui.restorebutton,
            self.ui.aboutbutton
        ]

        self.default = "background-color:transparent; color:white; border:none;"
        self.active = (
            "background-color:#ADD8E6;"
            "border-left:3px solid #6082B6;"
            "font-weight:bold; color:#0000FF;"
        )

        for b in self.buttons:
            b.setStyleSheet(self.default)

        self.activateButton(self.ui.homebutton)

        self.ui.homebutton.clicked.connect(lambda: self.menuOption("home"))
        self.ui.anonymizebutton.clicked.connect(lambda: self.menuOption("anonymize"))
        self.ui.restorebutton.clicked.connect(lambda: self.menuOption("restore"))
        self.ui.reportbutton.clicked.connect(lambda: self.menuOption("report"))
        self.ui.settingsbutton.clicked.connect(lambda: self.menuOption("settings"))
        self.ui.aboutbutton.clicked.connect(lambda: self.menuOption("about"))
        if hasattr(self.ui, "activityBar"):
            self.ui.activityBar.clicked.connect(lambda: self.menuOption("activity"))

        self.ui.uploadbutton.clicked.connect(self.uploadFile)
        if hasattr(self.ui, "uploadnewbutton"):
            self.ui.uploadnewbutton.clicked.connect(self.newFile)
        if hasattr(self.ui, "downloadbutton"):
            self.ui.downloadbutton.clicked.connect(self.download)
        if hasattr(self.ui, "scanbutton"):
            self.ui.scanbutton.clicked.connect(self.scan)
        if hasattr(self.ui, "randommask"):
            self.ui.randommask.clicked.connect(lambda: self.anonymization("random"))
        if hasattr(self.ui, "realisticmask"):
            self.ui.realisticmask.clicked.connect(lambda: self.anonymization("realistic"))
        if hasattr(self.ui, "restorebutton_2"):
            self.ui.restorebutton_2.clicked.connect(self.restore_file)

        if self.user and hasattr(self.ui, "lblUserName"):
            self.ui.lblUserName.setText(self.user.get("username", ""))

        self.ui.stackedWidget.setCurrentIndex(0)
        self.show()

    def open_user_page(self):
        if hasattr(self.ui, "stackedWidget") and hasattr(self.ui, "userPage"):
            self.ui.stackedWidget.setCurrentWidget(self.ui.userPage)

        if self.user and hasattr(self.ui, "lblUserName"):
            self.ui.lblUserName.setText(self.user.get("username", ""))

    def logout_user(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        QMessageBox.information(self, "Logged Out", "You have been logged out.")
        self.close()
        sys.exit()

    def update_counter(self, counter_name, increment=False):
        counter_file = os.path.join(BASE_DIR, "counters.json")
        if os.path.exists(counter_file):
            try:
                with open(counter_file, "r") as f:
                    data = json.load(f)
            except:
                data = {}
        else:
            data = {}

        for key in ["calNumber1", "calNumber2", "calNumber3", "calNumber4"]:
            if key not in data:
                data[key] = 0

        if increment or counter_name == "calNumber1":
            data[counter_name] += 1

        with open(counter_file, "w") as f:
            json.dump(data, f, indent=4)

        if hasattr(self.ui, counter_name):
            getattr(self.ui, counter_name).setText(str(data[counter_name]))

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_history(self):
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=4)

    def setup_history_table(self):
        if self.history_table is None:
            self.history_table = QTableWidget()
            self.history_table.setColumnCount(4)
            self.history_table.setHorizontalHeaderLabels(
                ["Document Name", "Upload", "Scan", "Anonymize / Restore"]
            )
            self.history_table.horizontalHeader().setStretchLastSection(True)
            self.history_table.setStyleSheet(
                "QTableWidget {background-color: black; color: white; gridline-color: black;}"
                "QHeaderView::section {background-color: black; color: white; border: none;}"
            )
            self.history_table.verticalHeader().setVisible(False)
            self.history_table.setShowGrid(True)
            layout = QVBoxLayout()
            layout.addWidget(self.history_table)
            self.ui.scrollAreaWidgetContents_3.setLayout(layout)

    def set_table_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = item.font()
        font.setPointSize(10)
        item.setFont(font)
        item.setForeground(Qt.white)
        self.history_table.setItem(row, col, item)

    def update_history_ui(self, filename=None, task=None, task_info=None):
        self.setup_history_table()
        row_index = None
        if filename:
            for row in range(self.history_table.rowCount()):
                if self.history_table.item(row, 0).text() == filename:
                    row_index = row
                    break
        if row_index is None:
            self.history_table.insertRow(0)
            row_index = 0
            self.set_table_item(row_index, 0, filename)
            self.set_table_item(row_index, 1, "Yes" if task == "Upload" else "")
            self.set_table_item(row_index, 2, task_info if task == "Scan" else "")
            self.set_table_item(row_index, 3, task_info if task in ["Anonymize","Restore"] else "")
        else:
            if task == "Upload":
                self.set_table_item(row_index, 1, "Yes")
            elif task == "Scan":
                self.set_table_item(row_index, 2, task_info)
            elif task in ["Anonymize","Restore"]:
                self.set_table_item(row_index, 3, task_info)
        self.save_history()

    def menuOption(self, option):
        if option == "home":
            self.activateButton(self.ui.homebutton)
            if self.fileLoad:
                self.ui.stackedWidget.setCurrentIndex(1)
                self.preview()
            else:
                self.ui.stackedWidget.setCurrentIndex(0)
        elif option == "anonymize":
            self.activateButton(self.ui.anonymizebutton)
            self.ui.stackedWidget.setCurrentIndex(self.ui.stackedWidget.indexOf(self.ui.pageScan))
        elif option == "restore":
            self.activateButton(self.ui.restorebutton)
            self.ui.stackedWidget.setCurrentIndex(self.ui.stackedWidget.indexOf(self.ui.pageRestore))
            self.setup_history_table()
        elif option == "report":
            self.activateButton(self.ui.reportbutton)
            self.ui.stackedWidget.setCurrentIndex(2)
        elif option == "settings":
            self.activateButton(self.ui.settingsbutton)
        elif option == "about":
            self.activateButton(self.ui.aboutbutton)
            self.ui.stackedWidget.setCurrentIndex(6)
        elif option == "activity":
            self.ui.stackedWidget.setCurrentIndex(self.ui.stackedWidget.indexOf(self.ui.pageActivity))

    def activateButton(self, selectedButton):
        for mainButtons in self.buttons:
            mainButtons.setStyleSheet(self.active if mainButtons == selectedButton else self.default)

    def uploadFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Documents (*.pdf *.txt);;All Files (*)")
        if not path:
            return
        self.filePath = path
        self.text_Original = ""
        self.currentText = ""
        self.piiDetection = []
        self.fileLoad = True
        if path.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as f:
                self.text_Original = f.read()
        else:
            try:
                doc = fitz.open(path)
                pages = []
                for page in doc:
                    text = page.get_text("text")
                    if not text.strip():
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        text = pytesseract.image_to_string(img)
                    pages.append(text)
                self.text_Original = "\n\n".join(pages)
                doc.close()
            except Exception as e:
                QMessageBox.critical(self, "Error!!", f"PDF failed: {str(e)}")
                self.fileLoad = False
                return
        self.currentText = self.text_Original
        self.ui.stackedWidget.setCurrentIndex(1)
        self.preview()
        self.update_counter("calNumber2", increment=True)
        self.update_history_ui(filename=os.path.basename(path), task="Upload")

    def newFile(self):
        self.filePath = None
        self.text_Original = ""
        self.currentText = ""
        self.piiDetection = []
        self.fileLoad = False
        self.ui.stackedWidget.setCurrentIndex(0)

    def preview(self):
        if not self.fileLoad:
            return
        html = self.highlight_pii(self.currentText, self.piiDetection) if self.piiDetection else f"<pre>{self.currentText}</pre>"
        self.viewer.setHtml(html)

    def highlight_pii(self, text, pii_list):
        result = ""
        last = 0
        for pii in sorted(pii_list, key=lambda x: x["start"]):
            result += text[last:pii["start"]]
            color = "#90EE90" if pii.get("anonymized") else "#FFB3B3"
            result += f"<mark style='background:{color};'>{text[pii['start']:pii['end']]}</mark>"
            last = pii["end"]
        result += text[last:]
        return f"<pre>{result}</pre>"

    def scan(self):
        if not self.fileLoad:
            QMessageBox.warning(self, "No File found.", "Upload a document.")
            return
        self.piiDetection = piiDetection(self.currentText)
        QMessageBox.information(self, "Scan Completed", f"{len(self.piiDetection)} PII detected")
        self.update_history_ui(filename=os.path.basename(self.filePath), task="Scan", task_info=f"{len(self.piiDetection)} PII")
        self.preview()

    def anonymization(self, mode):
        if not self.piiDetection:
            QMessageBox.warning(self, "PII not found", "Please scan the document.")
            return
        if mode == "random":
            self.currentText, self.piiDetection = randomAnonymize(self.currentText, self.piiDetection)
        else:
            self.currentText, self.piiDetection = realisticAnonymize(self.currentText, self.piiDetection)
        QMessageBox.information(self, "Done", f"Anonymization has been completed ({mode})")
        self.update_history_ui(filename=os.path.basename(self.filePath), task="Anonymize", task_info=mode)
        self.preview()
        self.update_counter("calNumber3", increment=True)

    def download(self):
        if not self.fileLoad:
            QMessageBox.warning(self, "No File", "Cannot be downloaded.")
            return
        base = os.path.basename(self.filePath)
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", f"processed_{base}", "PDF Files (*.pdf);;Text Files (*.txt)")
        if not save_path:
            return
        try:
            if save_path.lower().endswith(".txt"):
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.currentText)
            else:
                doc = fitz.open()
                pages = self.currentText.split("\n\n")
                for page_text in pages:
                    page = doc.new_page()
                    page.insert_text((50, 50), page_text, fontsize=11)
                doc.save(save_path)
                doc.close()

            mapping_file = save_path.replace(".pdf", "_mapping.json")
            with open(mapping_file, "w") as f:
                json.dump(self.piiDetection, f, indent=4)
            QMessageBox.information(self, "Saved", "File downloaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def restore_file(self):
        if not self.fileLoad:
            QMessageBox.warning(self, "No File", "Upload a file.")
            return
        mapping_file, _ = QFileDialog.getOpenFileName(self, "Select Mapping JSON", "", "JSON Files (*.json)")
        if not mapping_file:
            return
        restored_text = restore_original_text(self.currentText, self.piiDetection, mapping_file)
        self.currentText = restored_text
        QMessageBox.information(self, "Restored", "Document restored with original PII.")
        self.update_history_ui(filename=os.path.basename(self.filePath), task="Restore", task_info="Restored")
        self.preview()
        self.update_counter("calNumber4", increment=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    user_session = None
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                user_session = json.load(f)
        except:
            user_session = None

    if user_session:
        window = MainWindow(user=user_session)
    else:
        login = LoginDialog()
        if login.exec_() == QDialog.Accepted:
            window = MainWindow(user=login.logged_in_user)
        else:
            sys.exit()

    sys.exit(app.exec_())
