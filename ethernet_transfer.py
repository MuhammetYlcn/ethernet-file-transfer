import sys
import socket
import os
import time
import shutil
import zipfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QProgressBar, 
                             QStackedWidget, QFrame, QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

PORT = 5005
BUFFER_SIZE = 1024 * 1024  # 1MB

class TransferThread(QThread):
    progress_updated = pyqtSignal(int, float, float, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, mode, ip=None, path=None, save_path=None):
        super().__init__()
        self.mode = mode
        self.ip = ip
        self.path = path
        self.save_path = save_path
        self.is_running = True

class SenderThread(TransferThread):
    def run(self):
        server = None
        client_socket = None
        temp_zip = None
        try:
            target_path = self.path
            # Eğer klasörse zipleyelim
            if os.path.isdir(target_path):
                self.finished.emit("Klasör sıkıştırılıyor...")
                temp_zip = target_path + ".zip"
                shutil.make_archive(target_path, 'zip', target_path)
                target_path = temp_zip
            
            filesize = os.path.getsize(target_path)
            filename = os.path.basename(target_path)

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', PORT))
            server.listen(1)
            
            self.finished.emit("Bağlantı bekleniyor...")
            client_socket, _ = server.accept()
            
            # Metadata: dosyaadı|boyut
            client_socket.send(f"{filename}|{filesize}".encode())
            if client_socket.recv(1024).decode() != "OK": return

            start_time = time.time()
            bytes_sent = 0
            with open(target_path, "rb") as f:
                while bytes_sent < filesize and self.is_running:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk: break
                    client_socket.sendall(chunk)
                    bytes_sent += len(chunk)
                    self.emit_progress(bytes_sent, filesize, start_time)

            self.finished.emit("Gönderim tamamlandı!")
        except Exception as e:
            self.error.emit(f"Hata: {e}")
        finally:
            if client_socket: client_socket.close()
            if server: server.close()
            if temp_zip and os.path.exists(temp_zip): os.remove(temp_zip)

    def emit_progress(self, done, total, start):
        elapsed = time.time() - start
        speed = done / elapsed if elapsed > 0 else 0
        percent = int((done / total) * 100)
        eta = (total - done) / speed if speed > 0 else 0
        self.progress_updated.emit(percent, done, speed, time.strftime("%H:%M:%S", time.gmtime(eta)))

class ReceiverThread(TransferThread):
    def run(self):
        client = None
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.ip, PORT))
            
            metadata = client.recv(1024).decode()
            filename, filesize = metadata.split("|")
            filesize = int(filesize)
            client.send("OK".encode())
            
            full_save_path = os.path.join(self.save_path, filename)
            
            start_time = time.time()
            bytes_received = 0
            with open(full_save_path, "wb") as f:
                while bytes_received < filesize and self.is_running:
                    chunk = client.recv(BUFFER_SIZE)
                    if not chunk: break
                    f.write(chunk)
                    bytes_received += len(chunk)
                    self.emit_progress(bytes_received, filesize, start_time)

            # Zip açma işlemi
            if filename.endswith(".zip"):
                self.finished.emit("Dosyalar çıkarılıyor...")
                with zipfile.ZipFile(full_save_path, 'r') as zip_ref:
                    zip_ref.extractall(self.save_path)
                os.remove(full_save_path)

            self.finished.emit(f"Tamamlandı: {self.save_path}")
        except Exception as e:
            self.error.emit(f"Bağlantı Hatası: {e}")
        finally:
            if client: client.close()

    def emit_progress(self, done, total, start):
        elapsed = time.time() - start
        speed = done / elapsed if elapsed > 0 else 0
        percent = int((done / total) * 100)
        eta = (total - done) / speed if speed > 0 else 0
        self.progress_updated.emit(percent, done, speed, time.strftime("%H:%M:%S", time.gmtime(eta)))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ethernet Transfer Pro")
        self.setMinimumSize(500, 400)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.stack = QStackedWidget()
        
        # Ana Sayfa
        home = QWidget()
        h_lay = QVBoxLayout(home)
        btn_s = QPushButton("DOSYA/KLASÖR GÖNDER")
        btn_r = QPushButton("DOSYA AL")
        btn_s.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_r.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        h_lay.addWidget(btn_s); h_lay.addWidget(btn_r)
        
        # Gönder Sayfası
        send_pg = QWidget()
        s_lay = QVBoxLayout(send_pg)
        self.lbl_path = QLabel("Seçim Yapılmadı")
        btn_file = QPushButton("Dosya Seç")
        btn_dir = QPushButton("Klasör Seç")
        btn_start_s = QPushButton("Transferi Başlat")
        btn_file.clicked.connect(self.select_file)
        btn_dir.clicked.connect(self.select_dir)
        btn_start_s.clicked.connect(self.start_sending)
        s_lay.addWidget(QLabel(f"IP Adresiniz: {self.get_ip()}"))
        s_lay.addWidget(self.lbl_path); s_lay.addWidget(btn_file); s_lay.addWidget(btn_dir); s_lay.addWidget(btn_start_s)

        # Al Sayfası
        recv_pg = QWidget()
        r_lay = QVBoxLayout(recv_pg)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Göndericinin IP Adresi")
        btn_start_r = QPushButton("Alımı Başlat ve Kayıt Yeri Seç")
        btn_start_r.clicked.connect(self.start_receiving)
        r_lay.addWidget(self.ip_input); r_lay.addWidget(btn_start_r)

        # Progress Sayfası
        self.prog_pg = QWidget()
        p_lay = QVBoxLayout(self.prog_pg)
        self.status = QLabel("Bekliyor...")
        self.bar = QProgressBar()
        self.stats = QLabel("")
        p_lay.addWidget(self.status); p_lay.addWidget(self.bar); p_lay.addWidget(self.stats)

        self.stack.addWidget(home); self.stack.addWidget(send_pg); self.stack.addWidget(recv_pg); self.stack.addWidget(self.prog_pg)
        layout.addWidget(self.stack)

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 1))
            return s.getsockname()[0]
        except: return "127.0.0.1"

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç")
        if path: self.path = path; self.lbl_path.setText(path)

    def select_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if path: self.path = path; self.lbl_path.setText(path)

    def start_sending(self):
        if hasattr(self, 'path'):
            self.stack.setCurrentIndex(3)
            self.thread = SenderThread("send", path=self.path)
            self.thread.progress_updated.connect(self.update_ui)
            self.thread.finished.connect(self.status.setText)
            self.thread.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
            self.thread.start()

    def start_receiving(self):
        ip = self.ip_input.text()
        save_dir = QFileDialog.getExistingDirectory(self, "Dosyayı Nereye Kaydedelim?")
        if ip and save_dir:
            self.stack.setCurrentIndex(3)
            self.thread = ReceiverThread("recv", ip=ip, save_path=save_dir)
            self.thread.progress_updated.connect(self.update_ui)
            self.thread.finished.connect(self.status.setText)
            self.thread.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
            self.thread.start()

    def update_ui(self, p, done, speed, eta):
        self.bar.setValue(p)
        self.stats.setText(f"Hız: {speed/(1024**2):.2f} MB/s | Kalan: {eta}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())