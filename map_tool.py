import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QDialog, QTextEdit, QMessageBox, QInputDialog, QShortcut
)
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence, QPixmap, QBrush
from PyQt5.QtCore import Qt

# Define tile properties (color and description) for easier management.
TILE_PROPERTIES = {
    ' ': {"color": QColor("white"), "description": "Empty Space ( )"},
    '#': {"color": QColor("black"), "description": "Solid Block (#)"},
    '+': {"color": QColor("darkGray"), "description": "Block if not entrance (+)"},
    '@': {"color": QColor("gray"), "description": "Drop-down block (@)"},
    'W': {"color": QColor("blue"), "description": "Block: upward passage only (W)"},
    '!': {"color": QColor("magenta"), "description": "Block no slide (!)"},
    '^': {"color": QColor("lightGray"), "description": "Deadly pit (^)"},
    '~': {"color": QColor("lightBlue"), "description": "Water (~)"},
    '&': {"color": QColor("red"), "description": "Fire (&)"},
    '(': {"color": QColor("purple"), "description": "Bubble Type 1 (()"},
    "GO": {"color": QColor("white"), "description": "Game Object (custom)"},
}


class GridWidget(QWidget):
    def __init__(self, rows=18, cols=32, cell_size=20, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.selected_tile = '#'
        self.is_dragging = False
        self.history = []
        self.current_drag_changes = []

        # Sketch-related attributes
        self.sketch_layer = QPixmap(
            self.width(), self.height())  # Layer for sketches
        self.sketch_layer.fill(Qt.transparent)  # Transparent background
        self.is_sketching = False  # Track if sketching is active
        self.is_erasing = False  # Track if erasing is active
        self.eraser_size = 50  # Diameter of the eraser
        self.previous_sketch_pos = None  # Track the previous position for sketching
        self.eraser_position = None  # Track the current position of the eraser

        # Mode attribute to switch between sketch and grid modes
        self.mode = "grid"

    def resizeEvent(self, event):
        # Dynamically adjust cell size and resize sketch layer
        new_width = self.width() // self.cols
        new_height = self.height() // self.rows
        self.cell_size = min(new_width, new_height)

        # Resize the sketch layer
        new_sketch_layer = QPixmap(self.width(), self.height())
        new_sketch_layer.fill(Qt.transparent)
        painter = QPainter(new_sketch_layer)
        painter.drawPixmap(0, 0, self.sketch_layer)
        painter.end()
        self.sketch_layer = new_sketch_layer

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw the grid
        for row in range(self.rows):
            for col in range(self.cols):
                char = self.grid[row][col]
                color = TILE_PROPERTIES.get(char, {}).get(
                    "color", QColor("white"))
                x = col * self.cell_size
                y = row * self.cell_size
                painter.fillRect(x, y, self.cell_size, self.cell_size, color)
                painter.setPen(QPen(Qt.black))
                painter.drawRect(x, y, self.cell_size, self.cell_size)

                if char not in TILE_PROPERTIES:
                    painter.setPen(QPen(Qt.black))
                    font = painter.font()
                    font.setPointSize(self.cell_size // 2)
                    painter.setFont(font)
                    painter.drawText(x, y, self.cell_size,
                                     self.cell_size, Qt.AlignCenter, char)

        # Draw the sketch layer on top of the grid
        painter.drawPixmap(0, 0, self.sketch_layer)

        # Draw the eraser circle if erasing
        if self.is_erasing and self.eraser_position:
            pen = QPen(Qt.red, 1, Qt.DashLine)  # Dashed red circle
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            radius = self.eraser_size // 2
            painter.drawEllipse(self.eraser_position, radius, radius)

    def mousePressEvent(self, event):
        if self.mode == "sketch":
            if event.button() == Qt.LeftButton:
                self.is_sketching = True
                self.previous_sketch_pos = event.pos()  # Set the initial position
                self.add_sketch(event.pos())
            elif event.button() == Qt.RightButton:
                self.is_erasing = True
                self.erase_sketch(event.pos())
        elif self.mode == "grid":
            col = event.x() // self.cell_size
            row = event.y() // self.cell_size
            if 0 <= col < self.cols and 0 <= row < self.rows:
                self.is_dragging = True
                self.current_drag_changes = []
                self.current_drag_changes.append(
                    (row, col, self.grid[row][col]))
                if self.selected_tile == "GO":
                    char, ok = QInputDialog.getText(
                        self, "Game Object", "Enter a single character for game object:")
                    if ok and len(char) == 1:
                        self.grid[row][col] = char
                    else:
                        return
                else:
                    self.grid[row][col] = self.selected_tile
                self.update()

    def mouseMoveEvent(self, event):
        if self.mode == "sketch":
            if self.is_sketching:
                self.add_sketch(event.pos())
            elif self.is_erasing:
                self.eraser_position = event.pos()  # Update eraser position
                self.erase_sketch(event.pos())
                self.update()
        elif self.mode == "grid" and self.is_dragging:
            col = event.x() // self.cell_size
            row = event.y() // self.cell_size
            if 0 <= col < self.cols and 0 <= row < self.rows:
                if self.grid[row][col] != self.selected_tile:
                    self.current_drag_changes.append(
                        (row, col, self.grid[row][col]))
                if self.selected_tile == "GO":
                    char, ok = QInputDialog.getText(
                        self, "Game Object", "Enter a single character for game object:")
                    if ok and len(char) == 1:
                        self.grid[row][col] = char
                else:
                    self.grid[row][col] = self.selected_tile
                self.update()

    def mouseReleaseEvent(self, event):
        if self.mode == "sketch":
            self.is_sketching = False
            self.previous_sketch_pos = None  # Reset the previous position
            self.is_erasing = False
            self.eraser_position = None  # Clear the eraser position
            self.update()
        elif self.mode == "grid":
            self.is_dragging = False
            if self.current_drag_changes:
                self.history.append(self.current_drag_changes)

    def add_sketch(self, pos):
        painter = QPainter(self.sketch_layer)
        pen = QPen(Qt.red, 2)  # Red pen for sketches
        painter.setPen(pen)
        if self.previous_sketch_pos:
            # Draw a line from the previous position to the current position
            painter.drawLine(self.previous_sketch_pos, pos)
        else:
            # Draw a single point if there's no previous position
            painter.drawPoint(pos)
        painter.end()
        self.previous_sketch_pos = pos  # Update the previous position
        self.update()

    def erase_sketch(self, pos):
        painter = QPainter(self.sketch_layer)
        eraser = QBrush(Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.setBrush(eraser)
        painter.drawEllipse(pos, self.eraser_size // 2, self.eraser_size // 2)
        painter.end()
        self.update()

    def clear_sketches(self):
        self.sketch_layer.fill(Qt.transparent)
        self.update()

    def undo(self):
        if self.history:
            # Pop the last action from the history stack.
            last_action = self.history.pop()
            # Revert all changes in the last action.
            for row, col, previous_value in last_action:
                self.grid[row][col] = previous_value
            self.update()

    def export_map(self):
        # Build a string where each row is 32 characters from the grid,
        # followed by a '*' as the 33rd character.
        lines = []
        for row in self.grid:
            line = "".join(row) + "*"  # Append '*' at the end of the row.
            lines.append(line)
        result = "\"\\\n"
        for line in lines:
            result += line + "\\\n"
        result += "\";"
        return result

    def import_map(self, map_string):
        # Expected format:
        # "\
        # [32 editable chars plus '*']\
        # [32 editable chars plus '*']\
        # ...\
        # ";
        lines = map_string.strip().splitlines()
        # Remove header line if present.
        if lines and lines[0].startswith("\"\\"):
            lines = lines[1:]
        # Remove the last line if it ends with "\";"
        if lines and lines[-1].endswith("\";"):
            lines = lines[:-1]
        new_grid = []
        for line in lines:
            # Remove trailing backslash if present.
            if line.endswith("\\"):
                line = line[:-1]
            # Each valid line should have at least 33 characters.
            if len(line) < self.cols + 1:
                line = line.ljust(self.cols, ' ') + "*"
            else:
                line = line[:self.cols + 1]
            # Validate that the 33rd character is '*'
            if line[self.cols] != '*':
                raise ValueError("Invalid row format: missing '*' at the end.")
            # Only keep the first 32 characters for the editable grid.
            new_grid.append(list(line[:self.cols]))
        # Adjust the number of rows.
        if len(new_grid) < self.rows:
            for _ in range(self.rows - len(new_grid)):
                new_grid.append([' ' for _ in range(self.cols)])
        elif len(new_grid) > self.rows:
            new_grid = new_grid[:self.rows]
        self.grid = new_grid
        self.update()

    def clear_grid(self):
        # Save the current grid state for undo.
        current_state = [(row, col, self.grid[row][col])
                         for row in range(self.rows)
                         for col in range(self.cols)]
        self.history.append(current_state)
        # Reset the grid to whitespace.
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Builder")
        # Set initial size to match a 1920x1080 monitor.
        self.resize(1920, 1080)
        self.grid_widget = GridWidget()
        self.tile_buttons = {}  # Store tile buttons for dynamic styling
        self.mode_buttons = {}  # Store mode buttons for dynamic styling
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Add the grid widget on the left with stretch.
        main_layout.addWidget(self.grid_widget, stretch=3)

        # Controls panel on the right.
        controls_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout, stretch=1)

        label = QLabel("Select Tile:")
        controls_layout.addWidget(label)

        # Create a button for each defined tile type.
        for tile, properties in TILE_PROPERTIES.items():
            tile_layout = QHBoxLayout()
            color_square = QLabel()
            color_square.setFixedSize(20, 20)
            color_square.setStyleSheet(
                f"background-color: {properties['color'].name()}; border: 1px solid black;")
            tile_layout.addWidget(color_square)
            btn = QPushButton(properties["description"])
            btn.clicked.connect(lambda checked, t=tile: self.select_tile(t))
            self.tile_buttons[tile] = btn  # Store the button for styling
            tile_layout.addWidget(btn)
            container_widget = QWidget()
            container_widget.setLayout(tile_layout)
            controls_layout.addWidget(container_widget)

        controls_layout.addStretch(1)

        # Add mode toggle buttons
        btn_grid_mode = QPushButton("Grid Mode")
        btn_grid_mode.clicked.connect(lambda: self.set_mode("grid"))
        self.mode_buttons["grid"] = btn_grid_mode  # Store the button for styling
        controls_layout.addWidget(btn_grid_mode)

        btn_clear = QPushButton("Clear Grid")
        btn_clear.clicked.connect(self.grid_widget.clear_grid)
        controls_layout.addWidget(btn_clear)

        btn_sketch_mode = QPushButton("Sketch Mode")
        btn_sketch_mode.clicked.connect(lambda: self.set_mode("sketch"))
        self.mode_buttons["sketch"] = btn_sketch_mode  # Store the button for styling
        controls_layout.addWidget(btn_sketch_mode)

        btn_clear_sketches = QPushButton("Clear Sketches")
        btn_clear_sketches.clicked.connect(self.grid_widget.clear_sketches)
        controls_layout.addWidget(btn_clear_sketches)

        btn_undo = QPushButton("Undo")
        btn_undo.clicked.connect(self.grid_widget.undo)
        controls_layout.addWidget(btn_undo)

        btn_import = QPushButton("Import Map")
        btn_import.clicked.connect(self.import_map)
        controls_layout.addWidget(btn_import)

        btn_export = QPushButton("Export Map")
        btn_export.clicked.connect(self.export_map)
        controls_layout.addWidget(btn_export)

        # Add a keyboard shortcut for undo (Ctrl + Z).
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.grid_widget.undo)

        # Set initial styles
        self.update_tile_styles()
        self.update_mode_styles()

    def set_mode(self, mode):
        self.grid_widget.mode = mode
        self.update_mode_styles()

    def select_tile(self, tile):
        self.grid_widget.selected_tile = tile
        self.update_tile_styles()

    def update_tile_styles(self):
        for tile, btn in self.tile_buttons.items():
            if tile == self.grid_widget.selected_tile:
                btn.setStyleSheet("background-color: lightblue; font-weight: bold;")
            else:
                btn.setStyleSheet("")

    def update_mode_styles(self):
        for mode, btn in self.mode_buttons.items():
            if mode == self.grid_widget.mode:
                btn.setStyleSheet("background-color: lightgreen; font-weight: bold;")
            else:
                btn.setStyleSheet("")

    def export_map(self):
        map_str = self.grid_widget.export_map()
        dlg = QDialog(self)
        dlg.setWindowTitle("Exported Map String")
        dlg_layout = QVBoxLayout()
        dlg.setLayout(dlg_layout)
        text_edit = QTextEdit()
        text_edit.setPlainText(map_str)
        dlg_layout.addWidget(text_edit)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close)
        dlg.exec_()

    def import_map(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Import Map String")
        dlg_layout = QVBoxLayout()
        dlg.setLayout(dlg_layout)
        text_edit = QTextEdit()
        dlg_layout.addWidget(text_edit)
        btn_import = QPushButton("Import")
        btn_import.clicked.connect(
            lambda: self.handle_import(text_edit.toPlainText(), dlg))
        dlg_layout.addWidget(btn_import)
        dlg.exec_()

    def handle_import(self, map_str, dialog):
        try:
            self.grid_widget.import_map(map_str)
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(
                self, "Error", "Failed to import map: " + str(e))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
