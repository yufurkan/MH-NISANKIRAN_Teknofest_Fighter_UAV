import requests
import json
import time
import random
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

class SunucuHaberlesme(QObject):
    # Arayüze veri gönderecek sinyaller
    giris_durumu = pyqtSignal(bool, str)
    telemetri_cevabi_geldi = pyqtSignal(dict)
    qr_koordinati_geldi = pyqtSignal(dict)
    hss_koordinatlari_geldi = pyqtSignal(list)
    sunucu_mesaji = pyqtSignal(str)
    # Kendi telemetrimizi de arayüze göndermek için bir sinyal
    yeni_telemetri_paketi = pyqtSignal(dict)

    def __init__(self, takim_kadi, takim_sifre):
        super().__init__()
        self.base_url = "http://127.0.0.25:5000" # Dokümandaki adres
        self.kadi = takim_kadi
        self.sifre = takim_sifre
        self.session = requests.Session()
        self.telemetry_gonderme_aktif = False
        self.telemetry_thread = QThread()
        self.moveToThread(self.telemetry_thread)
        self.telemetry_thread.started.connect(self.telemetri_gonderme_dongusu)
        print("Sunucu Haberleşme Yöneticisi oluşturuldu.")

    def baslat(self):
        """Tüm işlemleri başlatan ana metod."""
        self.giris_yap()

    def giris_yap(self):
        try:
            print("Sunucuya giriş yapılıyor...")
            adres = f"{self.base_url}/api/giris"
            veri = {"kadi": self.kadi, "sifre": self.sifre}
            response = self.session.post(adres, json=veri, timeout=3)
            if response.status_code == 200:
                takim_no = response.json().get('takim_numarasi', 'N/A')
                mesaj = f"Giriş Başarılı. Takım No: {takim_no}"
                self.giris_durumu.emit(True, mesaj)
                self.telemetry_gonderme_aktif = True
                if not self.telemetry_thread.isRunning():
                    self.telemetry_thread.start()
            else:
                mesaj = f"Giriş Başarısız: {response.status_code} - {response.text}"
                self.giris_durumu.emit(False, mesaj)
            print(mesaj)
        except requests.exceptions.RequestException as e:
            mesaj = f"Sunucuya Bağlanılamadı: {e}"
            self.giris_durumu.emit(False, mesaj)
            print(mesaj)

    def telemetri_gonderme_dongusu(self):
        """Saniyede 1 Hz ile sunucuya telemetri gönderir."""
        while self.telemetry_gonderme_aktif:
            # ÖNEMLİ: Bu kısım, Pixhawk'tan gelen gerçek MAVLink verisiyle doldurulmalıdır.
            ornek_telemetri = {
                "takim_numarasi": 1, 
                "iha_enlem": 41.508775 + random.uniform(-0.001, 0.001), 
                "iha_boylam": 36.118335 + random.uniform(-0.001, 0.001),
                "iha_irtifa": 100 + random.uniform(-5, 5), 
                "iha_dikilme": 5, 
                "iha_yonelme": 45 + random.uniform(-10, 10), 
                "iha_yatis": 2,
                "iha_hiz": 25 + random.uniform(-2, 2), 
                "iha_batarya": 98, 
                "iha_otonom": 1, 
                "iha_kilitlenme": 0,
                "hedef_merkez_X": 0, "hedef_merkez_Y": 0, 
                "hedef_genislik": 0, "hedef_yukseklik": 0,
                "gps_saati": {"saat": int(time.strftime("%H")), "dakika": int(time.strftime("%M")), 
                              "saniye": int(time.strftime("%S")), "milisaniye": int(time.time() * 1000) % 1000}
            }
            # Kendi arayüzümüzü güncellemek için de sinyal yayalım
            self.yeni_telemetri_paketi.emit(ornek_telemetri)
            
            self.telemetri_gonder(ornek_telemetri)
            QThread.msleep(1000)

    def telemetri_gonder(self, telemetri_verisi):
        if not self.telemetry_gonderme_aktif: return
        try:
            adres = f"{self.base_url}/api/telemetri_gonder"
            response = self.session.post(adres, json=telemetri_verisi, timeout=2)
            if response.status_code == 200:
                self.telemetri_cevabi_geldi.emit(response.json())
        except requests.exceptions.RequestException:
            self.sunucu_mesaji.emit("Telemetri Gönderilemedi")

    @pyqtSlot()
    def qr_koordinati_al(self):
        self._get_istegi("/api/qr_koordinati", self.qr_koordinati_geldi, "QR Koordinatı")

    @pyqtSlot()
    def hss_koordinatlari_al(self):
        self._get_istegi("/api/hss_koordinatlari", self.hss_koordinatlari_geldi, "HSS Koordinatları", "hss_koordinat_bilgileri", [])
    
    def _get_istegi(self, endpoint, sinyal, ad, veri_anahtari=None, varsayilan=None):
        try:
            adres = f"{self.base_url}{endpoint}"
            response = self.session.get(adres, timeout=3)
            if response.status_code == 200:
                veri = response.json()
                data_to_emit = veri.get(veri_anahtari, varsayilan) if veri_anahtari else veri
                sinyal.emit(data_to_emit)
                self.sunucu_mesaji.emit(f"{ad} Alındı.")
            else:
                self.sunucu_mesaji.emit(f"{ad} Hatası: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.sunucu_mesaji.emit(f"{ad} Alınamadı: {e}")
            
    def durdur(self):
        self.telemetry_gonderme_aktif = False
        if self.telemetry_thread.isRunning():
            self.telemetry_thread.quit()
            self.telemetry_thread.wait()