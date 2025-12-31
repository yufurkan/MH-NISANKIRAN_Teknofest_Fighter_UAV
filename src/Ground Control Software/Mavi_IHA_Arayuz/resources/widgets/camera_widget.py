import cv2, time, datetime
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QGroupBox
from PyQt6.QtGui    import QPixmap, QImage, QPainter, QPen, QColor, QFont
from PyQt6.QtCore   import Qt, QTimer, QSize

VIDEO_SOURCE = ""   
FPS_TARGET   = 30
MARGIN_RATIO = 0.30            # sabit yeşil dikdörtgen kenar boşluğu (%)
TITLE_STYLE  = """
QGroupBox {
    border: 0px;                       /* kalın çerçeveyi kaldır */
    margin-top: 18px;                  /* title yüksekliği */
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 0px;
    padding: 2px 8px;
    background-color:#5DADE2;          /* Mavi bar (diğer kartlarla aynı) */
    color: white;
    font-weight: bold;
}
"""

# ================== Alt QLabel (overlay) ==================
class VideoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lock_rel = None           # (x,y,w,h) 0-1
        self.fps = 0.0

    def paintEvent(self, e):
        super().paintEvent(e)
        pm = self.pixmap()
        if not pm or pm.isNull():
            return
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- sabit yeşil dikdörtgen (kenarlardan %30 içeride) ---
        mx, my = int(w*MARGIN_RATIO), int(h*MARGIN_RATIO)
        p.setPen(QPen(QColor(0,255,0), 2))
        p.drawRect(mx, my, w-2*mx, h-2*my)

        # --- ortadaki nişangâh çizgileri ---
        p.setPen(QPen(QColor("white"), 1, Qt.PenStyle.DotLine))
        p.drawLine(w//2, 0,   w//2, h)
        p.drawLine(0,   h//2, w,   h//2)

        # --- kırmızı lock-box (varsa) ---
        if self.lock_rel:
            rx, ry, rw, rh = self.lock_rel
            p.setPen(QPen(QColor(255,0,0), 3))
            p.drawRect(int(rx*w), int(ry*h), int(rw*w), int(rh*h))

        # --- saat + FPS ---
        txt = f"{datetime.datetime.now():%H:%M:%S}   {self.fps:4.1f} fps"
        p.setFont(QFont("Monospace", 9))
        fm = p.fontMetrics()
        tw, th = fm.horizontalAdvance(txt)+8, fm.height()+4
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(0,0,0,160))
        p.drawRect(w-tw-6, 6, tw, th)
        p.setPen(QColor("white"))
        p.drawText(w-tw, 6+fm.ascent()+2, txt)
        p.end()

# ================== Ana widget ==================
class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Başlıklı gövde (mavi şerit tarzını stil dosyası çözer)
        box = QGroupBox("Kilitlenme Kamerası")
        box.setStyleSheet(TITLE_STYLE)

        self.vlabel = VideoLabel()
        self.vlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vlabel.setMinimumSize(QSize(640, 360))
        self.vlabel.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)

        box_lay = QVBoxLayout(box); box_lay.setContentsMargins(0,0,0,0)
        box_lay.addWidget(self.vlabel)

        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        root.addWidget(box)

        # OpenCV yakalama
        self.cap = cv2.VideoCapture(VIDEO_SOURCE)
        if not self.cap.isOpened():
            self.vlabel.setText("KAMERA SİNYALİ YOK"); return

        self._last = time.time()
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000/FPS_TARGET))

    # ----- dış API: lock-box konumla -----
    def set_lockbox(self, x, y, w, h):
        pm = self.vlabel.pixmap()
        if pm and not pm.isNull():
            self.vlabel.lock_rel = (x/pm.width(), y/pm.height(),
                                    w/pm.width(), h/pm.height())

    # ----- kare akışı -----
    def _tick(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        now = time.time(); dt = now-self._last; self._last = now
        self.vlabel.fps = 0.9*self.vlabel.fps + 0.1*(1/dt if dt else 0)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape
        pm = QPixmap.fromImage(QImage(frame.data, w, h, QImage.Format.Format_RGB888))
        pm = pm.scaled(self.vlabel.size(),
                       Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                       Qt.TransformationMode.SmoothTransformation)
        self.vlabel.setPixmap(pm)
        self.vlabel.update()
