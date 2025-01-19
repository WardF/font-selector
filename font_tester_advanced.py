import sys
import random
from collections import Counter
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QProgressBar,
    QInputDialog,
    QFileDialog,
    QWidget,
    QLineEdit,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
)
from PyQt5.QtGui import QFontDatabase, QFont, QIntValidator
from PyQt5.QtCore import Qt, QEvent


def filter_english_fonts(fonts):
    """Filter the font list to include only English-compatible fonts."""
    return [f for f in fonts if not f.startswith("@") and all(ord(c) < 128 for c in f)]


def filter_fonts_by_string(fonts, filter_string):
    """Filter the font list to include only fonts whose names contain the given string (case-insensitive)."""
    filter_string = filter_string.lower()
    return [f for f in fonts if filter_string in f.lower()]


class FontSelectionDialog(QDialog):
    """Custom dialog to accept font filter and number of fonts."""
    def __init__(self, total_fonts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Font Tester Options")

        self.filter_text = QLineEdit(self)
        self.font_count = QLineEdit(self)
        self.font_count.setValidator(QIntValidator(2, total_fonts))  # Only accept valid integer values

        # Get screen DPI to scale the fonts based on the screen size
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()

        # Set the font size to scale with DPI for labels
        font = QFont()
        scaled_font_size = int(10 + dpi // 96)  # Scale font size based on DPI (default DPI is 96)
        font.setPointSize(scaled_font_size)

        # Apply the font to the UI components (labels and instructions)
        self.filter_text.setFont(font)
        self.font_count.setFont(font)

        # Create layout for the dialog
        layout = QFormLayout(self)
        layout.addRow("Filter by font name (leave blank for all):", self.filter_text)
        layout.addRow(f"Number of fonts to compare (2-{total_fonts}):", self.font_count)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

    def get_values(self):
        """Return user inputs: filter text and font count."""
        return self.filter_text.text().strip(), self.font_count.text().strip()


class FontTesterApp(QMainWindow):
    def __init__(self, fonts):
        super().__init__()

        # Initialize settings and data
        self.default_font_size = 16
        self.current_round_fonts = fonts
        self.round_winners = []
        self.current_pair_index = 0
        self.round_number = 1
        self.total_rounds = self.calculate_total_rounds(len(fonts))
        self.comparison_history = []
        self.winner_counts = Counter()
        self.selection_enabled = True  # Control for enabling/disabling interactions

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Font Tester Advanced")
        self.setGeometry(100, 100, 1600, 1200)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Font comparison area
        self.font_layout = QHBoxLayout()
        self.main_layout.addLayout(self.font_layout)

        # Left font display
        self.left_panel = QVBoxLayout()
        self.left_font_label = QLabel("")
        self.left_font_label.setAlignment(Qt.AlignCenter)
        self.left_text = QTextEdit()
        self.left_text.setReadOnly(True)
        self.left_panel.addWidget(self.left_font_label)
        self.left_panel.addWidget(self.left_text)
        self.font_layout.addLayout(self.left_panel)

        # Right font display
        self.right_panel = QVBoxLayout()
        self.right_font_label = QLabel("")
        self.right_font_label.setAlignment(Qt.AlignCenter)
        self.right_text = QTextEdit()
        self.right_text.setReadOnly(True)
        self.right_panel.addWidget(self.right_font_label)
        self.right_panel.addWidget(self.right_text)
        self.font_layout.addLayout(self.right_panel)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.left_button = QPushButton("Left Font")
        self.left_button.clicked.connect(self.select_left)
        self.right_button = QPushButton("Right Font")
        self.right_button.clicked.connect(self.select_right)
        self.button_layout.addWidget(self.left_button)
        self.button_layout.addWidget(self.right_button)
        self.main_layout.addLayout(self.button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Increase the font size of the status label
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()

        # Set the font size to scale with DPI for labels
        scaled_font_size = int(10 + dpi // 96)  # Scale font size based on DPI (default DPI is 96)


        status_font = self.status_label.font()
        status_font.setPointSize(scaled_font_size)  # Set the desired font size
        self.status_label.setFont(status_font)
        
        self.main_layout.addWidget(self.status_label)

        # Enable key press events for the entire window
        self.central_widget.setFocusPolicy(Qt.StrongFocus)
        self.central_widget.installEventFilter(self)

        # Start comparison
        self.update_fonts()

    def calculate_total_rounds(self, num_fonts):
        """Calculate the number of rounds required for elimination."""
        rounds = 0
        while num_fonts > 1:
            num_fonts = (num_fonts + 1) // 2
            rounds += 1
        return rounds

    def update_fonts(self):
        """Display the current pair of fonts for comparison."""
        pairs = list(zip(self.current_round_fonts[::2], self.current_round_fonts[1::2]))

        if self.current_pair_index < len(pairs):
            left_font, right_font = pairs[self.current_pair_index]
            self.populate_text(self.left_text, self.left_font_label, left_font)
            self.populate_text(self.right_text, self.right_font_label, right_font)

            # Update status
            self.status_label.setText(
                f"Round {self.round_number} of {self.total_rounds} — Pair {self.current_pair_index + 1} of {len(pairs)}"
            )
            progress = int(
                (self.current_pair_index + len(self.round_winners))
                / len(self.current_round_fonts)
                * 100
            )
            self.progress_bar.setValue(progress)
        else:
            self.start_next_round()

    def populate_text(self, text_widget, label, font_name):
        """Fill the text widget with sample text in the given font."""
        label.setText(font_name)
        text_widget.setFont(QFont(font_name, self.default_font_size))
        html_sample_text = """
        <h1>Heading: The quick brown fox jumps over the lazy dog</h1>
        <p><b>Bold:</b> <b>This is bold text</b></p>
        <p><i>Italic:</i> <i>This is italicized text</i></p>
        <p><b><i>Bold & Italic:</i></b> <b><i>This is bold and italicized text</i></b></p>
        <ul>
            <li>First bullet point</li>
            <li>Second bullet point</li>
        </ul>
        <blockquote>A font comparison tool for better typography.</blockquote>
        """
        text_widget.setHtml(html_sample_text)

    def select_left(self):
        """Mark the left font as the winner and proceed."""
        if self.selection_enabled:
            pairs = list(zip(self.current_round_fonts[::2], self.current_round_fonts[1::2]))
            left_font, _ = pairs[self.current_pair_index]
            self.round_winners.append(left_font)
            self.winner_counts[left_font] += 1
            self.current_pair_index += 1
            self.update_fonts()

    def select_right(self):
        """Mark the right font as the winner and proceed."""
        if self.selection_enabled:
            pairs = list(zip(self.current_round_fonts[::2], self.current_round_fonts[1::2]))
            _, right_font = pairs[self.current_pair_index]
            self.round_winners.append(right_font)
            self.winner_counts[right_font] += 1
            self.current_pair_index += 1
            self.update_fonts()

    def start_next_round(self):
        """Start the next round or display the final results."""
        if len(self.round_winners) > 1:
            # Handle odd number of fonts: carry over one font to the next round
            if len(self.round_winners) % 2 == 1:
                self.round_winners.append(self.round_winners[-1])

            self.current_round_fonts = self.round_winners
            self.round_winners = []
            self.current_pair_index = 0
            self.round_number += 1
            self.update_fonts()
        else:
            self.display_result()

    def display_result(self):
        """Display the final winning font and summary."""
        self.selection_enabled = False  # Disable further input
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)

        winner = self.round_winners[0]
        
        # Sort the fonts by how many times they were selected
        result_lines = [
            f"{font} ({count})"
            for font, count in sorted(self.winner_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        

        # Show at most 6 results
        if len(result_lines) > 6:
            result_text = "Final Winner:\t" + "\n\t* ".join(result_lines[:6]) 
        else:
            result_text = "Final Winner:\t" + "\n\t* ".join(result_lines)

        self.status_label.setText(result_text)

    def eventFilter(self, source, event):
        """Handle key events for left and right arrow keys."""
        if event.type() == QEvent.KeyPress and self.selection_enabled:
            if event.key() == Qt.Key_Left:
                self.select_left()
                return True
            elif event.key() == Qt.Key_Right:
                self.select_right()
                return True
        return super().eventFilter(source, event)


def main():
    app = QApplication(sys.argv)

    # Load system fonts and filter English-compatible ones
    all_fonts = QFontDatabase().families()
    english_fonts = filter_english_fonts(all_fonts)

    filter_string = None
    subset_size = len(english_fonts)
    subset_init = None

    # Process command-line arguments
    for arg in sys.argv[1:]:
        if arg.isdigit():
            subset_size = int(arg)
            subset_init = 1
        else:
            filter_string = arg

    # Filter fonts based on filter_string
    if filter_string:
        english_fonts = filter_fonts_by_string(english_fonts, filter_string)

    # Interactive dialog if subset_size is not specified
    if not subset_init and not filter_string:
        dialog = FontSelectionDialog(len(english_fonts))
        if dialog.exec() == QDialog.Accepted:
            filter_string, subset_size_str = dialog.get_values()
            subset_size = int(subset_size_str) if subset_size_str else len(english_fonts)

    # Select random subset of fonts
    selected_fonts = random.sample(english_fonts, min(subset_size, len(english_fonts)))

    # Launch the application
    window = FontTesterApp(selected_fonts)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
