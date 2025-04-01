import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QDialog, QTextEdit, QMessageBox, QInputDialog, QShortcut
)
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence
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
        self.cols = cols  # Editable area is 32 columns.
        self.cell_size = cell_size
        # Create grid: each row is a list of 32 characters, initialized with spaces.
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        # Default selected tile is solid block.
        self.selected_tile = '#'
        # If using the "Game Object" option, selected_tile will be set to "GO".
        self.is_dragging = False  # Track if the user is dragging the mouse.
        self.history = []  # Stack to store the history of actions for undo.
        self.current_drag_changes = []  # Track changes during a drag.

    def resizeEvent(self, event):
        # Dynamically adjust cell size based on the widget's size.
        new_width = self.width() // self.cols
        new_height = self.height() // self.rows
        self.cell_size = min(new_width, new_height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw only the editable grid (32 columns)
        for row in range(self.rows):
            for col in range(self.cols):
                char = self.grid[row][col]
                # For game objects without a defined color, just use white.
                color = TILE_PROPERTIES.get(char, {}).get(
                    "color", QColor("white"))
                x = col * self.cell_size
                y = row * self.cell_size
                painter.fillRect(x, y, self.cell_size, self.cell_size, color)
                painter.setPen(QPen(Qt.black))
                painter.drawRect(x, y, self.cell_size, self.cell_size)

                # If the tile is a game object (single character), draw the character.
                if char not in TILE_PROPERTIES:  # Game objects are not in TILE_PROPERTIES.
                    painter.setPen(QPen(Qt.black))  # Set text color to black.
                    font = painter.font()
                    font.setPointSize(self.cell_size // 2)  # Adjust font size based on cell size.
                    painter.setFont(font)
                    # Draw the character centered in the cell.
                    painter.drawText(
                        x, y, self.cell_size, self.cell_size,
                        Qt.AlignCenter, char
                    )

    def mousePressEvent(self, event):
        col = event.x() // self.cell_size
        row = event.y() // self.cell_size
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.is_dragging = True  # Start dragging.
            self.current_drag_changes = []  # Reset drag changes.
            # Save the initial state of the cell for undo.
            self.current_drag_changes.append((row, col, self.grid[row][col]))
            # If the selected tile is the generic "Game Object" option, prompt the user.
            if self.selected_tile == "GO":
                char, ok = QInputDialog.getText(
                    self, "Game Object", "Enter a single character for game object:")
                if ok and len(char) == 1:
                    self.grid[row][col] = char
                else:
                    # Do nothing if cancelled or invalid input.
                    return
            else:
                self.grid[row][col] = self.selected_tile
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            col = event.x() // self.cell_size
            row = event.y() // self.cell_size
            if 0 <= col < self.cols and 0 <= row < self.rows:
                # Only save the state if the cell is being changed.
                if self.grid[row][col] != self.selected_tile:
                    self.current_drag_changes.append(
                        (row, col, self.grid[row][col]))
                # Fill the cell while dragging.
                if self.selected_tile == "GO":
                    char, ok = QInputDialog.getText(
                        self, "Game Object", "Enter a single character for game object:")
                    if ok and len(char) == 1:
                        self.grid[row][col] = char
                else:
                    self.grid[row][col] = self.selected_tile
                self.update()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False  # Stop dragging.
        if self.current_drag_changes:
            # Push the drag changes to the history stack.
            self.history.append(self.current_drag_changes)

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
            # Create a horizontal layout for the button and color square.
            tile_layout = QHBoxLayout()

            # Create a small square to represent the tile color.
            color_square = QLabel()
            color_square.setFixedSize(20, 20)  # Set the size of the square.
            color_square.setStyleSheet(
                f"background-color: {properties['color'].name()}; border: 1px solid black;")
            tile_layout.addWidget(color_square)

            # Create the button with the tile description.
            btn = QPushButton(properties["description"])
            btn.clicked.connect(lambda checked, t=tile: self.select_tile(t))
            tile_layout.addWidget(btn)

            # Add the layout to the controls panel.
            container_widget = QWidget()
            container_widget.setLayout(tile_layout)
            controls_layout.addWidget(container_widget)

        controls_layout.addStretch(1)

        btn_export = QPushButton("Export Map")
        btn_export.clicked.connect(self.export_map)
        controls_layout.addWidget(btn_export)

        btn_import = QPushButton("Import Map")
        btn_import.clicked.connect(self.import_map)
        controls_layout.addWidget(btn_import)

        btn_undo = QPushButton("Undo")
        btn_undo.clicked.connect(self.grid_widget.undo)
        controls_layout.addWidget(btn_undo)

        btn_clear = QPushButton("Clear Grid")
        btn_clear.clicked.connect(self.grid_widget.clear_grid)
        controls_layout.addWidget(btn_clear)

        # Add a keyboard shortcut for undo (Ctrl + Z).
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.grid_widget.undo)

    def select_tile(self, tile):
        self.grid_widget.selected_tile = tile

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
