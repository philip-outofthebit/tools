"""
Map Builder Tool

This tool provides an interactive GUI for designing and managing 2D maps. 
It includes features such as grid-based tile selection, sketching, undo/redo, 
and map import/export functionality. The tool is designed to be user-friendly 
and highly customizable for various use cases.

Author: Philip

Feel free to reach out for feedback or suggestions.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QDialog, QTextEdit, QMessageBox, QInputDialog, QShortcut, QCheckBox
)
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence, QPixmap, QBrush
from PyQt5.QtCore import Qt
import platform
from typing import Optional

VERSION = f"1.0.7 {platform.system()}"

# Define tile properties (color and description) for easier management.
TILE_PROPERTIES = {
    ' ': {"color": QColor("white"), "description": "Empty Space"},
    '#': {"color": QColor("black"), "description": "Solid Block"},
    # '+': {"color": QColor("darkGray"), "description": "Block if not entrance"},
    '@': {"color": QColor("gray"), "description": "Drop-down block"},
    'W': {"color": QColor("blue"), "description": "Block: upward passage only"},
    '!': {"color": QColor("magenta"), "description": "Block no slide"},
    '^': {"color": QColor("lightGray"), "description": "Deadly pit"},
    '~': {"color": QColor("lightBlue"), "description": "Water"},
    '&': {"color": QColor("red"), "description": "Fire"},
    '$': {"color": QColor("darkRed"), "description": "Deadly water"},
    '(': {"color": QColor("purple"), "description": "Bubble Type 1"},
    "<": {"color": QColor("lightGray"), "description": "Respawn face left"},
    ">": {"color": QColor("lightGray"), "description": "Respawn face right"},
    ".": {"color": QColor("white"), "description": "Placeholder"},
    "GO": {"color": QColor("white"), "description": "Game Object (custom)"},
}

ALWAYS_SHOW_CHARS = ['<', '>', '.']

IS_WINDOWS = platform.system() == "Windows"


def get_contrast_color(color: QColor) -> QColor:
    """
    Calculate the contrast color based on the luminance of the background color.
    """
    r, g, b = color.red(), color.green(), color.blue()
    # Calculate luminance (perceived brightness)
    luminance = (0.299 * r + 0.587 * g + 0.144 * b) / 255
    # Return white if luminance is low (dark background), wise black
    return QColor("white") if luminance < 0.5 else QColor("black")


class GridWidget(QWidget):
    def __init__(self, rows: int = 18, cols: int = 32, cell_size: int = 20, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.selected_tile = '#'
        self.is_dragging = False
        self.history = []
        self.current_drag_changes = []
        self.show_tile_letters = False  # Default: do not show tile letters

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

        # Store the original selected tile for temporary eraser functionality
        self.original_selected_tile = None

    def resizeEvent(self, event: 'QResizeEvent') -> None:
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

    def paintEvent(self, event: 'QPaintEvent') -> None:
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

                font_point_size = self.cell_size // 4 if IS_WINDOWS else self.cell_size // 2
                # Draw tile's letter if enabled. Always show '<', and '>'
                if self.show_tile_letters or char in ALWAYS_SHOW_CHARS:
                    text_color = get_contrast_color(color)
                    painter.setPen(QPen(text_color))
                    font = painter.font()
                    font.setPointSize(font_point_size)
                    painter.setFont(font)
                    painter.drawText(x, y, self.cell_size,
                                     self.cell_size, Qt.AlignCenter, char)

                # Always draw custom objects
                if char not in TILE_PROPERTIES:
                    painter.setPen(QPen(Qt.black))
                    font = painter.font()
                    font.setPointSize(font_point_size)
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

    def mousePressEvent(self, event: 'QMouseEvent') -> None:
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
                if event.button() == Qt.RightButton:
                    # Temporarily switch to Empty Space
                    self.original_selected_tile = self.selected_tile
                    self.selected_tile = ' '
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

    def mouseMoveEvent(self, event: 'QMouseEvent') -> None:
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

    def mouseReleaseEvent(self, event: 'QMouseEvent') -> None:
        if self.mode == "sketch":
            self.is_sketching = False
            self.previous_sketch_pos = None  # Reset the previous position
            self.is_erasing = False
            self.eraser_position = None  # Clear the eraser position
            self.update()
        elif self.mode == "grid":
            if event.button() == Qt.RightButton and self.original_selected_tile is not None:
                # Restore the original selected tile
                self.selected_tile = self.original_selected_tile
                self.original_selected_tile = None
            self.is_dragging = False
            if self.current_drag_changes:
                self.history.append(self.current_drag_changes)

    def add_sketch(self, pos: 'QPoint') -> None:
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

    def erase_sketch(self, pos: 'QPoint') -> None:
        painter = QPainter(self.sketch_layer)
        eraser = QBrush(Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.setBrush(eraser)
        painter.drawEllipse(pos, self.eraser_size // 2, self.eraser_size // 2)
        painter.end()
        self.update()

    def clear_sketches(self) -> None:
        self.sketch_layer.fill(Qt.transparent)
        self.update()

    def undo(self) -> None:
        if self.history:
            # Pop the last action from the history stack.
            last_action = self.history.pop()
            # Revert all changes in the last action.
            for row, col, previous_value in last_action:
                self.grid[row][col] = previous_value
            self.update()

    def export_map(self) -> str:
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

    def import_map(self, map_string: str) -> None:
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

    def clear_grid(self) -> None:
        # Save the current grid state for undo.
        current_state = [(row, col, self.grid[row][col])
                         for row in range(self.rows)
                         for col in range(self.cols)]
        self.history.append(current_state)
        # Reset the grid to whitespace.
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.update()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Map Builder")
        # Set initial size to match a 1920x1080 monitor.
        self.resize(1920, 1080)
        self.grid_widget = GridWidget()
        self.tile_buttons = {}  # Store tile buttons for dynamic styling
        self.mode_buttons = {}  # Store mode buttons for dynamic styling
        self.always_add_zero = False  # Track user preference for always adding '0'
        self.init_ui()

    def init_ui(self) -> None:
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
            tile_layout.setSpacing(3)
            tile_layout.setContentsMargins(5, 2, 5, 2)

            # Create a QLabel for the color square with the tile's letter
            color_square = QLabel(tile)
            color_square.setFixedSize(30, 30)
            color_square.setAlignment(Qt.AlignCenter)  # Center the letter
            background_color = properties["color"]
            text_color = get_contrast_color(background_color)

            color_square.setStyleSheet(
                f"background-color: {background_color.name()}; "
                f"color: {text_color.name()}; "
                "border: 1px solid black; font-weight: bold")
            tile_layout.addWidget(color_square)

            # Create the button for the tile
            btn = QPushButton(properties["description"])
            btn.setMinimumWidth(150)
            # btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, t=tile: self.select_tile(t))
            self.tile_buttons[tile] = btn  # Store the button for styling
            tile_layout.addWidget(btn)

            # Add the layout to the control panel
            container_widget = QWidget()
            container_widget.setLayout(tile_layout)
            controls_layout.addWidget(container_widget)

        # Reduce spacing and margins
        controls_layout.setSpacing(5)  # Reduce spacing between widgets
        # Reduce margins around the layout
        controls_layout.setContentsMargins(5, 5, 5, 5)

        controls_layout.addStretch(1)

        btn_toggle_letters = QPushButton("Show Tile Letters")
        btn_toggle_letters.setCheckable(True)
        btn_toggle_letters.clicked.connect(self.toggle_tile_letters)
        controls_layout.addWidget(btn_toggle_letters)
        # Add mode toggle buttons in the same row
        grid_row_layout = QHBoxLayout()
        btn_grid_mode = QPushButton("Grid Mode")
        btn_grid_mode.clicked.connect(lambda: self.set_mode("grid"))
        self.mode_buttons["grid"] = btn_grid_mode
        grid_row_layout.addWidget(btn_grid_mode, stretch=3)

        btn_clear = QPushButton("Clear Grid")
        btn_clear.clicked.connect(self.grid_widget.clear_grid)
        grid_row_layout.addWidget(btn_clear, stretch=1)
        controls_layout.addLayout(grid_row_layout)

        # Add sketch mode buttons in the same row
        sketch_row_layout = QHBoxLayout()
        btn_sketch_mode = QPushButton("Sketch Mode")
        btn_sketch_mode.clicked.connect(lambda: self.set_mode("sketch"))
        self.mode_buttons["sketch"] = btn_sketch_mode
        sketch_row_layout.addWidget(btn_sketch_mode, stretch=3)

        btn_clear_sketches = QPushButton("Clear Sketches")
        btn_clear_sketches.clicked.connect(self.grid_widget.clear_sketches)
        sketch_row_layout.addWidget(btn_clear_sketches, stretch=1)
        controls_layout.addLayout(sketch_row_layout)

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

        # Add version information label
        version_label = QLabel(f"Version {VERSION}", self)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        version_label.setFixedSize(100, 20)
        version_label.move(0, self.height() - 30)
        version_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        version_label.show()

        # Update the label position dynamically on window resize
        self.version_label = version_label
        self.resizeEvent = self.update_version_label_position

    def update_version_label_position(self, event: 'QResizeEvent') -> None:
        # Dynamically reposition the version label
        self.version_label.move(0, self.height() - 30)
        super().resizeEvent(event)

    def set_mode(self, mode: str) -> None:
        self.grid_widget.mode = mode
        self.update_mode_styles()
        self.update_tile_styles()  # Ensure tile styles are updated immediately

    def select_tile(self, tile: str) -> None:
        self.grid_widget.selected_tile = tile
        self.update_tile_styles()
        # Automatically switch to grid mode if in sketch mode
        if self.grid_widget.mode == "sketch":
            self.set_mode("grid")

    def toggle_tile_letters(self) -> None:
        # Toggle the show_title_letters attribute
        self.grid_widget.show_tile_letters = not self.grid_widget.show_tile_letters
        self.grid_widget.update()

    def update_tile_styles(self) -> None:
        if self.grid_widget.mode == "sketch":
            # Clear all tile button styles in Sketch Mode
            for btn in self.tile_buttons.values():
                btn.setStyleSheet("")
        else:
            # Highlight the selected tile in Grid Mode
            for tile, btn in self.tile_buttons.items():
                if tile == self.grid_widget.selected_tile:
                    btn.setStyleSheet(
                        "background-color: lightblue; font-weight: bold;")
                else:
                    btn.setStyleSheet("")

    def update_mode_styles(self) -> None:
        for mode, btn in self.mode_buttons.items():
            if mode == self.grid_widget.mode:
                btn.setStyleSheet(
                    "background-color: lightgreen; font-weight: bold;")
            else:
                btn.setStyleSheet("")

    def export_map(self) -> None:
        # Check if '0' should always be added to the top-left corner
        if self.always_add_zero or self.grid_widget.grid[0][0] != '0':
            if not self.always_add_zero:
                reply = QMessageBox.question(
                    self,
                    "Top-Left Corner Check",
                    "'0' is usually used for locating the background and camera.\
                    Would you like to add '0' to the top-left corner?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.grid_widget.grid[0][0] = '0'
                    self.grid_widget.update()
            else:
                self.grid_widget.grid[0][0] = '0'
                self.grid_widget.update()

        map_str = self.grid_widget.export_map()

        # Copy the map string to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(map_str)

        # Create the export dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Exported Map String")
        dlg.resize(400, 500)

        # Create the layout and text widget
        dlg_layout = QVBoxLayout()
        dlg.setLayout(dlg_layout)
        text_edit = QTextEdit()
        text_edit.setPlainText(map_str)
        text_edit.setReadOnly(True)
        dlg_layout.addWidget(text_edit)

        # Add a checkbox for always adding '0'
        checkbox = QCheckBox("Always add '0' to top-left corner")
        checkbox.setChecked(self.always_add_zero)
        checkbox.stateChanged.connect(lambda state: self.set_always_add_zero(state))
        dlg_layout.addWidget(checkbox)

        # Add a label to inform the user that the string has been copied
        copied_label = QLabel("Copied to clipboard.")
        copied_label.setStyleSheet("font-weight: bold;")
        dlg_layout.addWidget(copied_label)

        # Add a close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close)

        # Show the dialog
        dlg.exec_()

    def set_always_add_zero(self, state: int) -> None:
        self.always_add_zero = bool(state)

    def import_map(self) -> None:
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

    def handle_import(self, map_str: str, dialog: QDialog) -> None:
        try:
            self.grid_widget.import_map(map_str)
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(
                self, "Error", "Failed to import map: " + str(e))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
