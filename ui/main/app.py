import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMdiArea, QMdiSubWindow, QLabel, QWidget, QVBoxLayout
)


class ChildWindow(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        label = QLabel(f"This is the {title} window.")
        layout.addWidget(label)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt5 MDI App")
        self.setGeometry(100, 100, 800, 600)

        # MDI Area
        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Menu Bar
        self.menu_bar = self.menuBar()

        # Menus
        self.create_menu("File", ["New", "Open", "Save"])
        self.create_menu("Edit", ["Undo", "Redo", "Cut", "Copy", "Paste"])
        self.create_menu("View", ["Zoom In", "Zoom Out"])
        self.create_menu("Transport", ["Start", "Stop"])
        self.create_menu("Window", ["Cascade", "Tile"])
        self.create_menu("Help", ["About", "Documentation"])

    def create_menu(self, menu_name, actions):
        menu = self.menu_bar.addMenu(menu_name)
        for action_name in actions:
            action = QAction(action_name, self)
            action.triggered.connect(lambda checked, name=action_name: self.open_child_window(name))
            menu.addAction(action)

    def open_child_window(self, title):
        sub = QMdiSubWindow()
        sub.setWidget(ChildWindow(title))
        sub.setWindowTitle(title)
        self.mdi_area.addSubWindow(sub)
        sub.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())