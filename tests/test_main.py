import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from keyviz.main import get_theme_color, KeyButton

app = QApplication.instance() or QApplication([])

class TestKeyVizMain(unittest.TestCase):
    def test_theme_colors(self):
        col_white = get_theme_color("white", 0.5, 0.0)
        self.assertEqual(col_white, QColor("#ffffff"))

        col_blue = get_theme_color("blue", 0.5, 0.0)
        self.assertEqual(col_blue, QColor("#60a5fa"))

        col_slate = get_theme_color("slate", 0.5, 0.0)
        self.assertEqual(col_slate, QColor("#94a3b8"))

        col_hex = get_theme_color("#123456", 0.5, 0.0)
        self.assertEqual(col_hex.name().lower(), "#123456")

    def test_key_button_geometry(self):
        btn = KeyButton(
            sc_key="w",
            sc_list=17,
            display_name="W",
            width=50,
            height=50,
            scale=1.2,
            opacity=0.9
        )
        self.assertEqual(btn.width(), 60)
        self.assertEqual(btn.height(), 60)
        self.assertEqual(btn.display_name, "W")

if __name__ == '__main__':
    unittest.main()
