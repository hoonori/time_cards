from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
                            QGridLayout, QDialog, QSizePolicy, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette
from backend.game_state import GameState
from pathlib import Path

class TimelineCard(QFrame):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMinimumWidth(150)
        self.setMaximumWidth(200)
        
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title_label = QLabel(self.card.title)
        title_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Time
        time_label = QLabel(f"{self.card.drawed_at}")
        time_label.setFont(QFont("Arial", 7))
        layout.addWidget(time_label)
        
        # Priority
        prio_label = QLabel(f"Priority: {self.card.priority}")
        prio_label.setFont(QFont("Arial", 7))
        layout.addWidget(prio_label)
        
        self.setLayout(layout)

class MiniCard(QFrame):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedSize(18, 40)  # Make it fit within the grid cell
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        
        # Just show a colored block with priority
        priority_label = QLabel(str(self.card.priority))
        priority_label.setFont(QFont("Arial", 6))
        priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(priority_label)
        
        # Set background color based on priority
        palette = self.palette()
        color = QColor("#FFD700" if self.card.priority == 1 else "#C0C0C0")  # Gold for high priority, Silver for others
        palette.setColor(QPalette.ColorRole.Window, color)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

class TimelineGrid(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_time = 100
        self.current_time = 0
        self.cards = []
        self.cards_row = 2
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(10, 5, 10, 5)
        
        # Grid container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        self.update_grid()
        self.main_layout.addWidget(self.grid_container)
    
    def update_grid(self):
        # Clear existing grid
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Calculate visible time range (ensure it's an integer)
        visible_range = max(0, int(self.max_time - self.current_time) + 1)
        
        # Add time labels and grid lines
        for t in range(visible_range):
            actual_time = t + self.current_time
            # Time label
            if actual_time % 5 == 0:
                time_label = QLabel(str(actual_time))
                time_label.setFont(QFont("Arial", 6))
                time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid_layout.addWidget(time_label, 0, t * 2)  # Multiply by 2 to account for spacers
            
            # Grid line
            line = QFrame()
            line.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
            line.setLineWidth(2 if actual_time % 5 == 0 else 1)
            self.grid_layout.addWidget(line, 1, t * 2)  # Multiply by 2 to account for spacers
            
            # Add spacer column
            if t < visible_range - 1:
                spacer = QWidget()
                spacer.setFixedWidth(20)
                self.grid_layout.addWidget(spacer, 0, t * 2 + 1)  # Place spacer in odd columns
                self.grid_layout.addWidget(QWidget(), 1, t * 2 + 1)  # Add spacer for grid line row too
    
    def update_cards(self, cards, game_window):
        self.current_time = game_window.game.current_time
        
        # Update grid to show from current time
        self.update_grid()
        
        # Clear existing cards
        for card in self.cards:
            card.setParent(None)
        self.cards.clear()
        
        # Add new cards
        for card in sorted(cards, key=lambda x: x.drawed_at):
            if card.drawed_at >= self.current_time:  # Only show future cards
                mini_card = MiniCard(card, self)
                mini_card.mousePressEvent = lambda _, c=card: game_window.show_card_details(c)
                
                # Calculate grid column position relative to current time
                relative_pos = card.drawed_at - self.current_time
                col = relative_pos * 2  # Account for spacer columns
                self.grid_layout.addWidget(mini_card, self.cards_row, col)
                self.cards.append(mini_card)
        
        # Update max_time if needed
        if cards:
            self.max_time = max(card.drawed_at for card in cards) + 5  # Add some buffer

class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container for grid and cards
        self.timeline_container = QWidget()
        self.timeline_container.setMinimumHeight(200)
        container_layout = QVBoxLayout(self.timeline_container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Grid
        self.grid = TimelineGrid()
        container_layout.addWidget(self.grid)
        
        # Cards area
        self.cards_widget = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(0)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.cards_widget)
        
        # Add container to scroll area
        scroll = QScrollArea()
        scroll.setWidget(self.timeline_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll)
    
    def update_timeline(self, cards, max_time):
        # Update grid
        self.grid.max_time = max_time
        self.grid.setup_ui()
        
        # Clear existing cards
        for i in reversed(range(self.cards_layout.count())):
            self.cards_layout.itemAt(i).widget().setParent(None)
        
        # Add cards at their respective positions
        for card in sorted(cards, key=lambda x: x.drawed_at):
            card_widget = TimelineCard(card)
            
            # Calculate position based on time
            position = card.drawed_at * 21  # 20px spacing + 1px grid line
            card_widget.setFixedWidth(100)  # Fixed width for cards
            
            # Add spacer before card to position it
            if position > 0:
                spacer = QWidget()
                spacer.setFixedWidth(position)
                self.cards_layout.addWidget(spacer)
            
            self.cards_layout.addWidget(card_widget)
        
        # Add final spacer to maintain layout
        final_spacer = QWidget()
        final_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.cards_layout.addWidget(final_spacer)

class CardDetailsDialog(QDialog):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(self.card.title)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.card.title)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(self.card.description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Time and Priority
        info_label = QLabel(f"Time: {self.card.drawed_at} | Priority: {self.card.priority}")
        layout.addWidget(info_label)
        
        # Choices
        choices_label = QLabel("Choices:")
        choices_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(choices_label)
        
        for choice in self.card.choices:
            choice_frame = QFrame()
            choice_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
            choice_layout = QVBoxLayout()
            
            # Choice description
            choice_desc = QLabel(choice["description"])
            choice_desc.setWordWrap(True)
            choice_layout.addWidget(choice_desc)
            
            # Requirements
            if "requirements" in choice:
                req_text = "Requirements:\n"
                if "resources" in choice["requirements"]:
                    for resource, amount in choice["requirements"]["resources"].items():
                        req_text += f"  • {resource}: {amount}\n"
                if "relics" in choice["requirements"]:
                    for relic in choice["requirements"]["relics"]:
                        req_text += f"  • Relic: {relic}\n"
                req_label = QLabel(req_text)
                req_label.setStyleSheet("color: #FF6B6B;")
                choice_layout.addWidget(req_label)
            
            # Effects
            if "effects" in choice:
                eff_text = "Effects:\n"
                if "resources" in choice["effects"]:
                    for resource, amount in choice["effects"]["resources"].items():
                        sign = "+" if amount > 0 else ""
                        eff_text += f"  • {resource}: {sign}{amount}\n"
                if "relics" in choice["effects"]:
                    if "gain" in choice["effects"]["relics"]:
                        for relic in choice["effects"]["relics"]["gain"]:
                            eff_text += f"  • Gain Relic: {relic}\n"
                    if "lose" in choice["effects"]["relics"]:
                        for relic in choice["effects"]["relics"]["lose"]:
                            eff_text += f"  • Lose Relic: {relic}\n"
                eff_label = QLabel(eff_text)
                eff_label.setStyleSheet("color: #4CAF50;")
                choice_layout.addWidget(eff_label)
            
            choice_frame.setLayout(choice_layout)
            layout.addWidget(choice_frame)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class ChoiceWidget(QFrame):
    def __init__(self, choice, parent=None):
        super().__init__(parent)
        self.choice = choice
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel(self.choice["description"])
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Arial", 10))
        layout.addWidget(desc_label)
        
        # Requirements
        if "requirements" in self.choice:
            req_text = "Required:\n"
            if "resources" in self.choice["requirements"]:
                for resource, amount in self.choice["requirements"]["resources"].items():
                    req_text += f"  • {resource}: {amount}\n"
            if "relics" in self.choice["requirements"]:
                for relic in self.choice["requirements"]["relics"]:
                    req_text += f"  • Relic: {relic}\n"
            req_label = QLabel(req_text)
            req_label.setStyleSheet("color: #FF6B6B;")
            layout.addWidget(req_label)
        
        # Effects
        if "effects" in self.choice:
            eff_text = "Effects:\n"
            if "resources" in self.choice["effects"]:
                for resource, amount in self.choice["effects"]["resources"].items():
                    sign = "+" if amount > 0 else ""
                    eff_text += f"  • {resource}: {sign}{amount}\n"
            if "relics" in self.choice["effects"]:
                if "gain" in self.choice["effects"]["relics"]:
                    for relic in self.choice["effects"]["relics"]["gain"]:
                        eff_text += f"  • Gain Relic: {relic}\n"
                if "lose" in self.choice["effects"]["relics"]:
                    for relic in self.choice["effects"]["relics"]["lose"]:
                        eff_text += f"  • Lose Relic: {relic}\n"
            eff_label = QLabel(eff_text)
            eff_label.setStyleSheet("color: #4CAF50;")
            layout.addWidget(eff_label)
        
        self.setLayout(layout)

class CardWidget(QFrame):
    def __init__(self, card, index, parent=None):
        super().__init__(parent)
        self.card = card
        self.index = index
        self.game_window = parent
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Header with title and time
        header_layout = QHBoxLayout()
        
        title_label = QLabel(self.card.title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        time_label = QLabel(f"{self.card.drawed_at}")
        time_label.setFont(QFont("Arial", 10))
        header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(self.card.description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Choices
        choices_label = QLabel("Choices:")
        choices_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(choices_label)
        
        for i, choice in enumerate(self.card.choices):
            choice_layout = QHBoxLayout()
            
            # Choice details
            choice_widget = ChoiceWidget(choice)
            choice_layout.addWidget(choice_widget)
            
            # Button container for preview and select
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setSpacing(5)
            
            # Preview button
            preview_btn = QPushButton("Preview")
            preview_btn.setFixedWidth(70)
            preview_btn.setCheckable(True)  # Make the button toggleable
            preview_btn.clicked.connect(lambda checked, idx=i: 
                self.game_window.preview_choice(self.index, idx) if checked 
                else self.game_window.clear_preview())
            button_layout.addWidget(preview_btn)
            
            # Choice button
            choice_btn = QPushButton("Select")
            choice_btn.setFixedWidth(70)
            choice_btn.clicked.connect(lambda checked, idx=i: self.game_window.make_choice(self.index, idx))
            if not self.game_window.game.can_make_choice(self.index, i):
                choice_btn.setEnabled(False)
                preview_btn.setEnabled(False)
            button_layout.addWidget(choice_btn)
            
            choice_layout.addWidget(button_container)
            layout.addLayout(choice_layout)
        
        self.setLayout(layout)

class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game = GameState(Path("config"))
        self.auto_jump = False
        self.previewing_choice = None
        self.advance_btn = None  # Store reference to advance button
        self.setup_ui()
        self.update_display()
        
    def setup_ui(self):
        self.setWindowTitle("Time Cards Game")
        self.setMinimumSize(1200, 800)  # Increased minimum width for split layout
        
        # Central widget with horizontal split
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # Changed to horizontal layout
        
        # Left panel for stats and controls
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        
        # Stats section
        stats_group = QGroupBox("Stats")
        stats_layout = QVBoxLayout()
        
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.time_label)
        
        # Resources with individual labels for better visibility
        self.resource_labels = {}  # Store resource labels in a dict for easy access
        for resource in self.game.resource_config['resources']:
            label = QLabel()
            label.setFont(QFont("Arial", 10))
            self.resource_labels[resource] = label
            stats_layout.addWidget(label)
        
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)
        
        # Controls section
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        self.advance_btn = QPushButton("Advance Time")  # Store reference
        self.advance_btn.clicked.connect(self.advance_time)
        controls_layout.addWidget(self.advance_btn)
        
        self.auto_jump_btn = QPushButton("Auto Jump")
        self.auto_jump_btn.setCheckable(True)
        self.auto_jump_btn.clicked.connect(self.toggle_auto_jump)
        controls_layout.addWidget(self.auto_jump_btn)
        
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        # Add spacer at the bottom of left panel
        left_layout.addStretch()
        
        main_layout.addWidget(left_panel)
        
        # Right panel for timeline and cards
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Timeline section
        timeline_group = QGroupBox("Upcoming Events")
        timeline_layout = QVBoxLayout()
        
        timeline_scroll = QScrollArea()
        self.timeline_grid = TimelineGrid()
        timeline_scroll.setWidget(self.timeline_grid)
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        timeline_scroll.setMinimumHeight(150)
        timeline_layout.addWidget(timeline_scroll)
        
        timeline_group.setLayout(timeline_layout)
        right_layout.addWidget(timeline_group)
        
        # Active cards section
        cards_group = QGroupBox("Active Cards")
        cards_layout = QVBoxLayout()
        
        self.cards_scroll = QScrollArea()
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_scroll.setWidget(self.cards_widget)
        self.cards_scroll.setWidgetResizable(True)
        cards_layout.addWidget(self.cards_scroll)
        
        cards_group.setLayout(cards_layout)
        right_layout.addWidget(cards_group)
        
        main_layout.addWidget(right_panel)
    
    def update_display(self, force_clear_preview=False):
        """
        Update the display while maintaining preview state unless forced to clear
        force_clear_preview: if True, clear preview regardless of current state
        """
        # Update time
        self.time_label.setText(f"Time: {self.game.current_time}")
        
        # Get current preview state
        preview_choice = None if force_clear_preview else self.previewing_choice
        
        # Update resource labels
        for resource, amount in self.game.resources.items():
            label = self.resource_labels[resource]
            resource_name = self.game.resource_config['resources'][resource]['name']
            
            # If previewing and the previewed card still exists, show the difference
            if preview_choice is not None:
                card_index, choice_index = preview_choice
                if card_index < len(self.game.active_cards):  # Check if card still exists
                    card = self.game.active_cards[card_index]
                    choice = card.choices[choice_index]
                    
                    # Calculate resource change if this choice is made
                    change = 0
                    if "effects" in choice and "resources" in choice["effects"]:
                        change = choice["effects"]["resources"].get(resource, 0)
                    
                    # Show current value and change
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        label.setText(f"{resource_name}: {amount} ({sign}{change} → {amount + change})")
                        # Color the text based on whether it's an increase or decrease
                        label.setStyleSheet(f"color: {'#4CAF50' if change > 0 else '#FF6B6B'}")
                        continue
            
            # Default display if not previewing or no change
            label.setText(f"{resource_name}: {amount}")
            label.setStyleSheet("")
        
        # Update timeline
        self.timeline_grid.update_cards(self.game.card_queue, self)
        
        # Clear and update active cards
        for i in reversed(range(self.cards_layout.count())):
            self.cards_layout.itemAt(i).widget().setParent(None)
            
        for i, card in enumerate(self.game.active_cards):
            card_widget = CardWidget(card, i, self)
            self.cards_layout.addWidget(card_widget)
        
        # Update advance button state
        has_next_cards = bool(self.game.card_queue)
        self.advance_btn.setEnabled(has_next_cards)
        if not has_next_cards:
            self.advance_btn.setText("No More Cards")
        else:
            self.advance_btn.setText("Advance Time")
            
        # Update auto jump button state
        self.auto_jump_btn.setEnabled(has_next_cards)
        if not has_next_cards and self.auto_jump:
            self.auto_jump = False
            self.auto_jump_btn.setChecked(False)
    
    def show_card_details(self, card):
        dialog = CardDetailsDialog(card, self)
        dialog.exec()
            
    def make_choice(self, card_index, choice_index):
        if self.game.can_make_choice(card_index, choice_index):
            self.game.make_choice(card_index, choice_index)
            self.update_display(force_clear_preview=True)  # Force clear preview after making choice
            
            # If auto jump is enabled and no active cards remain, jump to next card
            if self.auto_jump and not self.game.active_cards and self.game.card_queue:
                self.jump_to_next_card()
            
    def toggle_auto_jump(self, checked):
        self.auto_jump = checked
        if checked:
            self.auto_jump_btn.setText("Stop Auto")
            # If no active cards, jump immediately
            if not self.game.active_cards and self.game.card_queue:
                self.jump_to_next_card()
        else:
            self.auto_jump_btn.setText("Auto Jump")
    
    def jump_to_next_card(self):
        if not self.game.card_queue:
            return
            
        # Find the next card's time
        next_time = min(card.drawed_at for card in self.game.card_queue)
        
        # Jump to that time
        while self.game.current_time < next_time:
            self.game.advance_time()
        
        self.update_display(force_clear_preview=True)  # Force clear preview after jump
    
    def advance_time(self):
        self.game.advance_time()
        self.update_display(force_clear_preview=True)  # Force clear preview after time advance
        
        # If auto jump is enabled and no active cards remain, jump to next card
        if self.auto_jump and not self.game.active_cards and self.game.card_queue:
            self.jump_to_next_card()

    def preview_choice(self, card_index, choice_index):
        """Show a preview of what would happen if this choice was made"""
        self.previewing_choice = (card_index, choice_index)
        self.update_display()

    def clear_preview(self):
        """Clear the preview and restore normal display"""
        self.previewing_choice = None
        self.update_display()

def main():
    app = QApplication([])
    
    # Set application style
    app.setStyle("Fusion")
    
    window = GameWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main() 