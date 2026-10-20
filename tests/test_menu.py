import unittest
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from keyviz.menu import DynamicStackedWidget, WindowButton, SettingsMenu

app = QApplication.instance() or QApplication([])

class TestKeyVizMenu(unittest.TestCase):
    def test_dynamic_stacked_widget(self):
        stack = DynamicStackedWidget()
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        l1.addWidget(QLabel("Label 1"))

        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        for i in range(10):
            l2.addWidget(QLabel(f"Line {i}"))

        stack.addWidget(p1)
        stack.addWidget(p2)

        stack.setCurrentIndex(0)
        self.assertEqual(stack.sizeHint(), p1.sizeHint())

        stack.setCurrentIndex(1)
        self.assertEqual(stack.sizeHint(), p2.sizeHint())

    def test_window_button(self):
        min_btn = WindowButton("min")
        close_btn = WindowButton("close")
        self.assertEqual(min_btn.width(), 28)
        self.assertEqual(min_btn.height(), 22)
        self.assertEqual(close_btn.width(), 28)
        self.assertEqual(close_btn.height(), 22)

if __name__ == '__main__':
    unittest.main()
