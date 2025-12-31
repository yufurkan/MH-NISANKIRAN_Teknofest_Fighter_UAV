# resources/widgets/indicators_widget.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel
)
from PyQt6.QtGui    import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore   import Qt, QRectF, pyqtSlot, QPointF


# ==================================================================== #
# Gösterge (yalnız daire + değer)                                      #
# ==================================================================== #
class GaugeWidget(QWidget):
    """Dairesel gösterge yalnızca sayısal değeri çizer;
    başlık ve birim ayrı QLabel olarak dışarıdan verilir."""

    def __init__(self, max_value: float, parent: QWidget | None = None):
        super().__init__(parent)
        self.max_value = max_value
        self.current_value = 0.0
        self.setMinimumSize(120, 120)

    # --------------------- public API ---------------------------------
    def set_value(self, value: float | None):
        self.current_value = value if value is not None else 0.0
        self.update()

    # --------------------- paint --------------------------------------
    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        pen_width = 12
        rect = QRectF(0, 0, side, side)
        rect.moveCenter(QPointF(self.rect().center()))
        arc_rect = rect.adjusted(pen_width / 2, pen_width / 2,
                                 -pen_width / 2, -pen_width / 2)

        # Arka plan
        painter.setPen(QPen(QColor("#E0E0E0"), pen_width))
        painter.drawArc(arc_rect, 135 * 16, -270 * 16)

        # Değer yayı (turuncu)
        ratio = max(0.0, min(self.current_value / self.max_value, 1.0))
        span  = -270 * ratio
        grad = QLinearGradient(arc_rect.topLeft(), arc_rect.bottomRight())
        grad.setColorAt(0.0, QColor("#FFB74D"))
        grad.setColorAt(1.0, QColor("#F57C00"))
        painter.setPen(QPen(grad, pen_width))
        painter.drawArc(arc_rect, 135 * 16, int(span * 16))

        # Değer metni
        painter.setPen(QColor("#2C3E50"))
        painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        text = f"{self.current_value:.1f}" if self.max_value <= 50 else f"{self.current_value:.0f}"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


# ==================================================================== #
# Dört göstergeli konteyner                                            #
# ==================================================================== #
class IndicatorsWidget(QWidget):
    """Dört Gauge + başlık & birim etiketleri."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        main_v = QVBoxLayout(self)
        grp    = QGroupBox("Göstergeler")
        main_v.addWidget(grp)

        h = QHBoxLayout(grp)

        # Yardımcı fonksiyon: Gauge + etiketleri aynı kolonda tut
        def build_column(title: str, unit: str, max_val: float):
            col = QVBoxLayout()
            lbl_title = QLabel(title); lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g = GaugeWidget(max_val)
            lbl_unit  = QLabel(unit);  lbl_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Etiketlerde stil dosyası uygulanacak; font-size/QSS’den kontrol edilebilir
            col.addWidget(lbl_title)
            col.addWidget(g, 1)           # gauge esnek
            col.addWidget(lbl_unit)
            return col, g, lbl_title, lbl_unit

        col_hiz, self.gauge_hiz, self.lbl_hiz_t, self.lbl_hiz_u = build_column("HIZ",        "m/s",  50)
        col_alt, self.gauge_alt, self.lbl_alt_t, self.lbl_alt_u = build_column("YÜKSEKLİK",  "m",   300)
        col_head,self.gauge_head,self.lbl_head_t,self.lbl_head_u= build_column("PUSULA",     "°",   360)
        col_bat, self.gauge_bat, self.lbl_bat_t, self.lbl_bat_u = build_column("BATARYA",    "%",   100)

        for c in (col_hiz, col_alt, col_head, col_bat):
            h.addLayout(c)

    # -------------------- dinamik başlık/birim ------------------------
    def set_title(self, gauge: str, text: str):
        getattr(self, f"lbl_{gauge}_t").setText(text)

    def set_unit(self, gauge: str, text: str):
        getattr(self, f"lbl_{gauge}_u").setText(text)

    # -------------------- telemetri güncelle --------------------------
    @pyqtSlot(dict)
    def update_data(self, data: dict):
        if "groundspeed"        in data: self.gauge_hiz.set_value(data["groundspeed"])
        if "alt"                in data: self.gauge_alt.set_value(data["alt"])
        if "heading"            in data: self.gauge_head.set_value(data["heading"])
        if "battery_percentage" in data: self.gauge_bat.set_value(data["battery_percentage"]*100)
