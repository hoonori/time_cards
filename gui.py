from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
                            QGridLayout, QDialog, QSizePolicy, QGroupBox, QTreeWidget,
                            QTreeWidgetItem, QMessageBox, QRadioButton, QTextEdit, QSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette
from backend.game_state import GameState
from backend.state_history import StateManager
from pathlib import Path
import sys
import time
from backend.game_loader import GameLoader

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
        
        # Card type indicator
        if self.card.card_type == "immediate":
            type_label = QLabel("⚠️ Must be handled now!")
            type_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
            layout.addWidget(type_label)
        
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

class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Game Mode")
        self.setModal(True)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Get available modes
        modes = GameLoader.get_available_modes()
        if not modes:
            QMessageBox.critical(self, "Error", "No game modes found in config directory!")
            self.reject()
            return
            
        # Create buttons for each mode
        for mode in modes:
            btn = QPushButton(mode)
            description = GameLoader.get_mode_description(mode)
            if description:
                btn.setToolTip(description)
            btn.clicked.connect(lambda checked, m=mode: self.accept_mode(m))
            layout.addWidget(btn)
            
    def accept_mode(self, mode: str):
        self.selected_mode = mode
        self.accept()
        
    def get_selected_mode(self) -> str:
        return getattr(self, 'selected_mode', None)

class HistoryDialog(QDialog):
    """Dialog for viewing and loading game states"""
    def __init__(self, state_manager: StateManager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Game History")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Tree widget for state history
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Last Played", "Message", "ID"])
        self.tree.itemDoubleClicked.connect(self.load_selected_state)
        layout.addWidget(self.tree)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Selected State")
        load_btn.clicked.connect(self.load_selected_state)
        button_layout.addWidget(load_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.update_tree()
    
    def update_tree(self):
        """Update the tree widget with current state history"""
        self.tree.clear()
        
        # Create a mapping of node IDs to tree items
        items = {}
        
        # First pass: create all items
        for node_data in self.state_manager.get_tree_structure():
            item = QTreeWidgetItem([
                time.strftime("%H:%M:%S", time.localtime(node_data['last_played'])),
                node_data['message'],
                node_data['id']
            ])
            items[node_data['id']] = item
            
            # Mark current node
            if node_data['is_current']:
                for i in range(3):
                    item.setBackground(i, QColor("#E6F3FF"))
        
        # Second pass: set up parent-child relationships
        for node_data in self.state_manager.get_tree_structure():
            item = items[node_data['id']]
            if node_data['parent']:
                parent_item = items[node_data['parent']]
                parent_item.addChild(item)
            else:
                self.tree.addTopLevelItem(item)
        
        # Expand all items
        self.tree.expandAll()
    
    def load_selected_state(self):
        """Load the selected state into the game"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a state to load.")
            return
            
        item = selected_items[0]
        node_id = item.text(2)  # ID is in the third column
        
        try:
            self.parent().load_game_state(node_id)
            self.accept()  # Close dialog after successful load
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load state: {str(e)}")

class GameLogDialog(QDialog):
    """Dialog for viewing the game event log"""
    def __init__(self, game: GameState, parent=None):
        super().__init__(parent)
        self.game = game
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Game Log")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create text area for log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_log)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.update_log()
    
    def update_log(self):
        """Update the log display with current events"""
        self.log_text.clear()
        
        # Group events by time
        events_by_time = {}
        for event in self.game.event_history:
            if event.timestamp not in events_by_time:
                events_by_time[event.timestamp] = []
            events_by_time[event.timestamp].append(event)
        
        # Display events chronologically
        for timestamp in sorted(events_by_time.keys()):
            self.log_text.append(f"\n=== Time {timestamp} ===")
            
            for event in events_by_time[timestamp]:
                # Format the event header
                header = f"\n[{event.event_type.upper()}] {event.source}"
                self.log_text.append(header)
                
                # Format the description
                self.log_text.append(f"Description: {event.description}")
                
                # Format resource changes
                if event.resource_changes:
                    self.log_text.append("Resource Changes:")
                    for resource, change in event.resource_changes.items():
                        sign = "+" if change > 0 else ""
                        self.log_text.append(f"  • {resource}: {sign}{change}")
                
                # Add a separator
                self.log_text.append("-" * 50)

class TimeAdvanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advance Time")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Time input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Advance time by:"))
        self.time_input = QSpinBox()
        self.time_input.setMinimum(1)
        self.time_input.setMaximum(100)
        self.time_input.setValue(5)  # Default value
        input_layout.addWidget(self.time_input)
        input_layout.addWidget(QLabel("time units"))
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_time_advance(self) -> int:
        return self.time_input.value()

class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Time Cards Game")
        self.setMinimumSize(800, 600)
        
        # Show mode selection dialog
        mode_dialog = ModeSelectionDialog(self)
        if mode_dialog.exec() == QDialog.DialogCode.Accepted:
            self.mode = mode_dialog.get_selected_mode()
        else:
            sys.exit()
            
        # Initialize game state and state manager
        config_path = Path("config")
        self.game = GameState(config_path, self.mode)
        self.state_manager = StateManager(config_path, self.mode)
        self.state_manager.initialize(self.game)
        
        self.auto_jump = True
        self.previewing_choice = None
        self.advance_btn = None
        
        # Initialize UI components
        self.relics_group = None
        self.setup_ui()
        self.update_display()
    
    def setup_ui(self):
        self.setWindowTitle(f"Time Cards Game - {self.mode.capitalize()} Mode")
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
        
        # Relics section
        self.relics_group = QGroupBox("Relics")  # Store reference to relics group
        self.relics_group.setObjectName("Relics")  # Set object name for finding
        relics_layout = QVBoxLayout()
        
        # Initialize with empty state
        self.empty_relic_label = QLabel("No relics yet")
        self.empty_relic_label.setFont(QFont("Arial", 10))
        relics_layout.addWidget(self.empty_relic_label)
        
        self.relics_group.setLayout(relics_layout)
        left_layout.addWidget(self.relics_group)
        
        # Controls section
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        # --- First row: Advance Cards & Auto Advance ---
        card_advance_layout = QHBoxLayout()
        self.advance_cards_btn = QPushButton("Advance Cards")
        self.advance_cards_btn.clicked.connect(self.jump_to_next_card)
        self.advance_cards_btn.setFixedWidth(140)
        card_advance_layout.addWidget(self.advance_cards_btn)

        self.auto_jump_radio = QRadioButton("Auto Advance")
        self.auto_jump_radio.setChecked(True)
        self.auto_jump_radio.toggled.connect(self.toggle_auto_jump)
        card_advance_layout.addWidget(self.auto_jump_radio)
        card_advance_layout.addStretch()
        controls_layout.addLayout(card_advance_layout)

        # --- Second row: Manual Time Advance ---
        manual_time_layout = QHBoxLayout()
        advance_label = QLabel("Advance")
        manual_time_layout.addWidget(advance_label)
        self.time_input = QSpinBox()
        self.time_input.setMinimum(1)
        self.time_input.setMaximum(100)
        self.time_input.setValue(5)
        self.time_input.setFixedWidth(60)
        manual_time_layout.addWidget(self.time_input)
        units_label = QLabel("time units")
        manual_time_layout.addWidget(units_label)
        self.manual_time_advance_btn = QPushButton("Manual Time Advance")
        self.manual_time_advance_btn.setFixedWidth(160)
        self.manual_time_advance_btn.clicked.connect(self.manual_time_advance)
        manual_time_layout.addWidget(self.manual_time_advance_btn)
        manual_time_layout.addStretch()
        controls_layout.addLayout(manual_time_layout)

        # Add history and log buttons as before
        history_btn = QPushButton("View History")
        history_btn.clicked.connect(self.show_history)
        controls_layout.addWidget(history_btn)
        game_log_btn = QPushButton("Game Log")
        game_log_btn.clicked.connect(self.show_game_log)
        controls_layout.addWidget(game_log_btn)
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
        
        # Initial display update
        self.update_display()
    
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
        
        # Update relic labels
        relics_group = self.findChild(QGroupBox, "Relics")
        if relics_group:
            relics_layout = relics_group.layout()
            # Clear existing labels
            while relics_layout.count():
                item = relics_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add new labels
            if self.game.relics:
                for relic in self.game.relics:
                    # Create a frame for each relic
                    relic_frame = QFrame()
                    relic_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
                    relic_layout = QVBoxLayout()
                    
                    # Name and count
                    name_label = QLabel(f"{relic.name} (x{relic.count})")
                    name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    relic_layout.addWidget(name_label)
                    
                    # Description
                    desc_label = QLabel(relic.description)
                    desc_label.setWordWrap(True)
                    relic_layout.addWidget(desc_label)
                    
                    # Effects
                    if relic.passive_effects:
                        effects_label = QLabel("Effects:")
                        effects_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                        relic_layout.addWidget(effects_label)
                        
                        # Get countdowns for this relic
                        countdowns = self.game.get_effect_countdowns()
                        
                        for effect in relic.passive_effects:
                            if effect["type"] == "resource_per_time":
                                resource = effect["resource"]
                                amount = effect["amount"] * relic.count  # Multiply by count
                                interval = effect["interval"]
                                
                                # Get countdown info
                                key = f"{relic.name}_{resource}"
                                countdown = countdowns.get(key, {})
                                remaining = countdown.get("remaining", interval)
                                
                                # Format the effect text
                                effect_text = f"  • {resource}: {amount:+} every {interval} time units"
                                if "requirements" in effect:
                                    req_text = " (Requires: "
                                    for req in effect["requirements"]:
                                        if isinstance(req, dict):
                                            req_text += f"{req['resource']} >= {req['amount']}, "
                                        else:
                                            req_text += f"{req}, "
                                    req_text = req_text[:-2] + ")"
                                    effect_text += req_text
                                
                                # Add effect text
                                effect_label = QLabel(effect_text)
                                effect_label.setStyleSheet("color: #4CAF50;")
                                relic_layout.addWidget(effect_label)
                                
                                # Add countdown on new line
                                countdown_text = f"    Next effect in: {remaining} time units"
                                countdown_label = QLabel(countdown_text)
                                countdown_label.setStyleSheet("color: #666666;")  # Gray color for countdown
                                relic_layout.addWidget(countdown_label)
                    
                    relic_frame.setLayout(relic_layout)
                    relics_layout.addWidget(relic_frame)
            else:
                empty_label = QLabel("No relics yet")
                empty_label.setFont(QFont("Arial", 10))
                relics_layout.addWidget(empty_label)
        
        # Update timeline
        self.timeline_grid.update_cards(self.game.card_queue, self)
        
        # Clear and update active cards
        for i in reversed(range(self.cards_layout.count())):
            self.cards_layout.itemAt(i).widget().setParent(None)
            
        for i, card in enumerate(self.game.active_cards):
            card_widget = CardWidget(card, i, self)
            self.cards_layout.addWidget(card_widget)
        
        # Update advance cards button state
        has_next_cards = bool(self.game.card_queue)
        self.advance_cards_btn.setEnabled(has_next_cards)
        if not has_next_cards:
            self.advance_cards_btn.setText("No More Cards")
        else:
            self.advance_cards_btn.setText("Advance Cards")
        # Manual Time Advance is always enabled
        self.manual_time_advance_btn.setEnabled(True)
        self.manual_time_advance_btn.setText("Manual Time Advance")
            
        # Update auto jump radio state
        self.auto_jump_radio.setEnabled(True)  # Always enable the radio button
        # Don't change the checked state of auto jump radio
    
    def show_card_details(self, card):
        dialog = CardDetailsDialog(card, self)
        dialog.exec()
            
    def make_choice(self, card_index, choice_index):
        if not self.game.can_make_choice(card_index, choice_index):
            return
            
        # Get card and choice info for history message
        card = self.game.active_cards[card_index]
        card_title = card.title
        choice_desc = card.choices[choice_index]['description']
        message = f"Chose '{choice_desc}' on card '{card_title}' (Time: {self.game.current_time})"
        
        # Make the choice
        success = self.game.make_choice(card_index, choice_index)
        
        if success:
            # Save state to history
            self.state_manager.save_state(self.game, message=message)
            
            # Update display and handle auto-jump
            self.update_display(force_clear_preview=True)
            if self.auto_jump and not self.game.active_cards and self.game.card_queue:
                self.jump_to_next_card()
            
    def toggle_auto_jump(self, checked):
        self.auto_jump = checked
        if checked:
            self.auto_jump_radio.setText("Stop Auto")
            # If no active cards, jump immediately
            if not self.game.active_cards and self.game.card_queue:
                self.jump_to_next_card()
        else:
            self.auto_jump_radio.setText("Auto Advance")
    
    def jump_to_next_card(self):
        if not self.game.card_queue:
            return
            
        # Find the next card's time
        next_time = min(card.drawed_at for card in self.game.card_queue)
        
        # Jump to that time
        while self.game.current_time <= next_time:  # Changed from < to <=
            print(f"[DEBUG] Advancing time from {self.game.current_time} to {next_time}")
            self.game.advance_time()
            if not self.game.card_queue:  # Break if no more cards
                break
        
        self.update_display(force_clear_preview=True)  # Force clear preview after jump
    
    def advance_time(self):
        # Check if there are any immediate cards
        immediate_cards = [card for card in self.game.active_cards if card.card_type == "immediate"]
        if immediate_cards:
            QMessageBox.warning(self, "Immediate Cards", 
                "You must handle all immediate cards before advancing time!")
            return
            
        if self.game.advance_time():
            self.update_display(force_clear_preview=True)
            
            # If auto jump is enabled and no active cards remain, advance time again
            if self.auto_jump and not self.game.active_cards and self.game.card_queue:
                self.advance_time()

    def preview_choice(self, card_index, choice_index):
        """Show a preview of what would happen if this choice was made"""
        self.previewing_choice = (card_index, choice_index)
        self.update_display()

    def clear_preview(self):
        """Clear the preview and restore normal display"""
        self.previewing_choice = None
        self.update_display()

    def show_history(self):
        """Show the history dialog"""
        dialog = HistoryDialog(self.state_manager, self)
        dialog.exec()
    
    def load_game_state(self, node_id: str):
        """Load a game state from history"""
        try:
            loaded_state = self.state_manager.load_state(node_id)
            self.game = loaded_state
            
            # If there are cards in the queue, jump to the next card's time
            if self.game.card_queue:
                next_time = min(card.drawed_at for card in self.game.card_queue)
                while self.game.current_time < next_time:
                    self.game.advance_time()
            
            self.update_display(force_clear_preview=True)
            print(f"Successfully loaded state from node {node_id}")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Failed to load state: {str(e)}")

    def show_game_log(self):
        """Show the game log dialog"""
        dialog = GameLogDialog(self.game, self)
        dialog.exec()

    def manual_time_advance(self):
        """Advance time by the specified amount, regardless of cards (manual time advance)."""
        amount = self.time_input.value()
        if hasattr(self.game, 'advance_time_by'):
            self.game.advance_time_by(amount, ignore_cards=True)
        else:
            # Fallback: increment time and process passive effects for the full amount
            for _ in range(amount):
                self.game.current_time += 1
                if hasattr(self.game, '_process_passive_effects'):
                    self.game._process_passive_effects()
        self.update_display(force_clear_preview=True)

def main():
    app = QApplication([])
    
    # Set application style
    app.setStyle("Fusion")
    
    window = GameWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main() 