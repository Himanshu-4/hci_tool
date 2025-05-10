

# class StartChildWindow(QWidget):
#     def __init__(self, title):
#         super().__init__()
#         self.setMinimumSize(200, 600)
#         layout = QVBoxLayout()

#         # Toggle boxes
#         self.toggle1 = QCheckBox("Enable Feature A")
#         self.toggle2 = QCheckBox("Enable Feature B")
#         layout.addWidget(self.toggle1)
#         layout.addWidget(self.toggle2)

#         # List with 8 items
#         self.combo_box = QComboBox()
#         for i in range(1, 9):
#             self.combo_box.addItem(f"Option {i}")
#         layout.addWidget(self.combo_box)

#         # Label display area
#         self.label_area = QLabel("Select an item to display its info here.")
#         self.label_area.setWordWrap(True)
#         layout.addWidget(self.label_area)

#         # Connect signal
#         self.combo_box.currentTextChanged.connect(lambda text: self.label_area.setText(f"Details for {text} displayed below."))

#         self.setLayout(layout)
#         # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         # self.setStyleSheet("background-color: lightblue;")  # Set background color
#         self.setWindowIconText(title)  # Set window icon text
#         self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close


#     def on_item_selected(self, current, previous):
#         if current:
#             self.label_area.setText(f"Details for {current.text()} displayed below.")
