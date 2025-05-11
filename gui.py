from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
                            QGridLayout, QDialog, QSizePolicy, QGroupBox, QTreeWidget,
                            QTreeWidgetItem, QMessageBox, QRadioButton, QTextEdit, QSpinBox,
                            QComboBox, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QAction
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
        
        # Title and stack count
        title_layout = QHBoxLayout()
        title_label = QLabel(self.card.title)
        title_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label)
        
        if self.card.stack_count > 1:
            stack_label = QLabel(f"x{self.card.stack_count}")
            stack_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            stack_label.setStyleSheet("color: #4CAF50;")
            title_layout.addWidget(stack_label)
        
        layout.addLayout(title_layout)
        
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
        
        # Add stack count if greater than 1
        if self.card.stack_count > 1:
            stack_label = QLabel(f"x{self.card.stack_count}")
            stack_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            stack_label.setStyleSheet("color: #4CAF50;")
            header_layout.addWidget(stack_label)
        
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

class PolicyPanel(QGroupBox):
    def __init__(self, game_window):
        super().__init__("Policy Panel")
        self.game_window = game_window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Rules list
        self.rules_list = QTreeWidget()
        self.rules_list.setHeaderLabels(["Card", "Choice"])
        self.rules_list.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.rules_list.itemChanged.connect(self.on_rule_moved)
        layout.addWidget(self.rules_list)

        # Add rule section
        add_rule_layout = QHBoxLayout()
        self.card_combo = QComboBox()
        self.choice_combo = QComboBox()
        add_btn = QPushButton("Add Rule")
        add_btn.clicked.connect(self.add_rule)
        add_rule_layout.addWidget(self.card_combo)
        add_rule_layout.addWidget(self.choice_combo)
        add_rule_layout.addWidget(add_btn)
        layout.addLayout(add_rule_layout)

        # Run until section
        run_until_layout = QHBoxLayout()
        run_until_layout.addWidget(QLabel("Run Until:"))
        self.run_until_input = QLineEdit()
        self.run_until_input.setPlaceholderText("e.g., 10, +10, or -1")
        run_until_layout.addWidget(self.run_until_input)
        layout.addLayout(run_until_layout)

        # Run policy button
        self.run_policy_btn = QPushButton("Run Policy")
        self.run_policy_btn.clicked.connect(self.run_policy)
        layout.addWidget(self.run_policy_btn)

        self.setLayout(layout)
        self.update_card_choices()

    def update_card_choices(self):
        self.card_combo.clear()
        self.choice_combo.clear()

        # 모든 카드 타이틀을 config에서 가져오기
        all_card_titles = [card_data["title"] for card_data in self.game_window.game.card_config["cards"].values()]
        print(f"[DEBUG][PolicyPanel] All card titles from config: {all_card_titles}")

        for title in sorted(set(all_card_titles)):
            self.card_combo.addItem(title)

        self.card_combo.currentTextChanged.connect(self.update_choices)
        self.update_choices()

    def update_choices(self):
        self.choice_combo.clear()
        selected_card = self.card_combo.currentText()

        # config에서 해당 카드의 choices 가져오기
        card_data = None
        for c in self.game_window.game.card_config["cards"].values():
            if c["title"] == selected_card:
                card_data = c
                break

        if card_data and "choices" in card_data:
            for choice in card_data["choices"]:
                self.choice_combo.addItem(choice["description"])
            print(f"[DEBUG][PolicyPanel] Choices for {selected_card}: {[choice['description'] for choice in card_data['choices']]}")
        else:
            print(f"[DEBUG][PolicyPanel] No choices found for {selected_card}")

    def add_rule(self):
        """Add a new rule to the policy"""
        card_title = self.card_combo.currentText()
        choice_desc = self.choice_combo.currentText()
        if card_title and choice_desc:
            self.game_window.game.policy.add_rule(card_title, choice_desc)
            self.update_rules_list()

    def update_rules_list(self):
        """Update the rules list display"""
        self.rules_list.clear()
        for rule in self.game_window.game.policy.rules:
            item = QTreeWidgetItem([rule.card_title, rule.choice_description])
            self.rules_list.addTopLevelItem(item)

    def on_rule_moved(self, item, column):
        """Handle rule reordering"""
        print(f"\n[DEBUG] === Rule moved ===")
        print(f"[DEBUG] Item: {item.text(0)} - {item.text(1)}")
        print(f"[DEBUG] Column: {column}")
        
        # Get the new index
        new_index = self.rules_list.indexOfTopLevelItem(item)
        print(f"[DEBUG] New index: {new_index}")
        
        # Get the old index by finding the rule in the policy
        old_index = None
        for i, rule in enumerate(self.game_window.game.policy.rules):
            if rule.card_title == item.text(0) and rule.choice_description == item.text(1):
                old_index = i
                break
        
        if old_index is not None:
            print(f"[DEBUG] Old index: {old_index}")
            self.game_window.game.policy.reorder_rule(old_index, new_index)
            self.update_rules_list()
        else:
            print("[DEBUG] Could not find rule in policy")
        print(f"[DEBUG] === End of rule moved ===\n")

    def run_policy(self):
        """Run the policy with the specified target time"""
        time_str = self.run_until_input.text().strip()
        if not time_str:
            QMessageBox.warning(self, "Error", "Please specify a target time")
            return

        # Register save_callback before running policy (clear previous to avoid duplicates)
        self.game_window.game._on_action_callbacks = []
        def save_callback(game_state, message=""):
            print(f"[DEBUG][CALLBACK] save_callback called with message: {message}")
            print(f"[DEBUG][CALLBACK] save_callback: state_manager id={id(self.game_window.state_manager)}, game_state id={id(game_state)}")
            self.game_window.state_manager.save_state(game_state, message=message or "Policy action")
        self.game_window.game.register_on_action_callback(save_callback)

        try:
            # 현재 게임 시간 전달
            self.game_window.game.policy.set_target_time(time_str, self.game_window.game.current_time)
            self.game_window.game.run_policy()
            self.game_window.update_display()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

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
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left panel (existing UI)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Time label
        self.time_label = QLabel(f"Time: {self.game.current_time}")
        self.time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(self.time_label)
        
        # Resources group
        resources_group = QGroupBox("Resources")
        resources_layout = QVBoxLayout()
        self.resource_labels = {}
        for resource, amount in self.game.resources.items():
            label = QLabel(f"{resource}: {amount}")
            self.resource_labels[resource] = label
            resources_layout.addWidget(label)
        resources_group.setLayout(resources_layout)
        left_layout.addWidget(resources_group)
        
        # Relics group
        self.relics_group = QGroupBox("Relics")
        self.relics_group.setObjectName("Relics")
        relics_layout = QVBoxLayout()
        self.relics_group.setLayout(relics_layout)
        left_layout.addWidget(self.relics_group)
        
        # Timeline grid
        self.timeline_grid = TimelineGrid(self)
        left_layout.addWidget(self.timeline_grid)
        
        # Active cards
        cards_group = QGroupBox("Active Cards")
        self.cards_layout = QHBoxLayout()
        cards_group.setLayout(self.cards_layout)
        left_layout.addWidget(cards_group)
        
        # Manual time advance + interval in one row
        manual_time_layout = QHBoxLayout()
        manual_time_layout.addWidget(QLabel("Advance by:"))
        self.time_input = QSpinBox()
        self.time_input.setMinimum(1)
        self.time_input.setMaximum(100)
        self.time_input.setValue(5)
        manual_time_layout.addWidget(self.time_input)
        manual_time_layout.addWidget(QLabel("time units"))
        self.manual_time_advance_btn = QPushButton("Manual Time Advance")
        self.manual_time_advance_btn.clicked.connect(self.manual_time_advance)
        manual_time_layout.addWidget(self.manual_time_advance_btn)
        left_layout.addLayout(manual_time_layout)
        
        # Time control buttons (auto/advance cards)
        time_control_layout = QHBoxLayout()
        self.auto_jump_radio = QRadioButton("Auto Advance")
        self.auto_jump_radio.setChecked(self.auto_jump)
        self.auto_jump_radio.toggled.connect(self.toggle_auto_jump)
        time_control_layout.addWidget(self.auto_jump_radio)
        self.advance_cards_btn = QPushButton("Advance Cards")
        self.advance_cards_btn.clicked.connect(self.jump_to_next_card)
        time_control_layout.addWidget(self.advance_cards_btn)
        left_layout.addLayout(time_control_layout)

        # History and Log buttons in left panel
        history_log_layout = QHBoxLayout()
        history_btn = QPushButton("View History")
        history_btn.clicked.connect(self.show_history)
        history_log_layout.addWidget(history_btn)
        game_log_btn = QPushButton("Game Log")
        game_log_btn.clicked.connect(self.show_game_log)
        history_log_layout.addWidget(game_log_btn)
        left_layout.addLayout(history_log_layout)

        # Add left panel to main layout
        main_layout.addWidget(left_panel, stretch=2)
        
        # Add policy panel
        self.policy_panel = PolicyPanel(self)
        main_layout.addWidget(self.policy_panel, stretch=1)
        
        # Menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        save_action = QAction("Save State", self)
        save_action.triggered.connect(self.save_game_state)
        file_menu.addAction(save_action)
        
        load_action = QAction("Load State", self)
        load_action.triggered.connect(self.load_game_state)
        file_menu.addAction(load_action)
        
        history_action = QAction("View History", self)
        history_action.triggered.connect(self.show_history)
        file_menu.addAction(history_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        log_action = QAction("Game Log", self)
        log_action.triggered.connect(self.show_game_log)
        view_menu.addAction(log_action)

    def update_display(self, force_clear_preview=False):
        """
        Update the display while maintaining preview state unless forced to clear
        force_clear_preview: if True, clear preview regardless of current state
        """
        print("\n[DEBUG] ===== update_display called =====")
        print(f"[DEBUG] Current time: {self.game.current_time}")
        print(f"[DEBUG] Active cards before update: {[(card.title, card.drawed_at) for card in self.game.active_cards]}")
        print(f"[DEBUG] Card queue before update: {[(card.title, card.drawed_at) for card in self.game.card_queue]}")
        
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
        print("[DEBUG] Updating timeline grid...")
        self.timeline_grid.update_cards(self.game.card_queue, self)
        
        # Clear and update active cards
        print("[DEBUG] Updating active cards display...")
        for i in reversed(range(self.cards_layout.count())):
            self.cards_layout.itemAt(i).widget().setParent(None)
            
        for i, card in enumerate(self.game.active_cards):
            print(f"[DEBUG] Adding card to display: {card.title} (time: {card.drawed_at})")
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
        
        print(f"[DEBUG] Active cards after update: {[(card.title, card.drawed_at) for card in self.game.active_cards]}")
        print("[DEBUG] ===== End of update_display =====")
    
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
        print(f"[DEBUG] Jumping to next card time: {next_time}")
        if not self.game.advance_time(mode="advance_cards"):
            print("[DEBUG] Failed to advance to next card time")
            return
            
        self.update_display(force_clear_preview=True)  # Force clear preview after jump
    
    def advance_time(self):
        # Check if there are any immediate cards
        immediate_cards = [card for card in self.game.active_cards if card.card_type == "immediate"]
        if immediate_cards:
            QMessageBox.warning(self, "Immediate Cards", 
                "You must handle all immediate cards before advancing time!")
            return
            
        if self.game.advance_time(mode="auto"):
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
            self.update_display(force_clear_preview=True)
            print(f"Successfully loaded state from node {node_id}")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Failed to load state: {str(e)}")

    def show_game_log(self):
        """Show the game log dialog"""
        dialog = GameLogDialog(self.game, self)
        dialog.exec()

    def manual_time_advance(self):
        print("\n[DEBUG] ===== manual_time_advance called =====")
        # Restrict if there are immediate cards
        immediate_cards = [card for card in self.game.active_cards if card.card_type == "immediate"]
        if immediate_cards:
            print(f"[DEBUG] Cannot advance: found immediate cards: {[card.title for card in immediate_cards]}")
            QMessageBox.warning(self, "Immediate Cards", 
                "You must handle all immediate cards before advancing time!")
            return

        amount = self.time_input.value()
        print(f"[DEBUG] Attempting to advance time by {amount} units")
        for i in range(amount):
            print(f"[DEBUG] Manual advance iteration {i+1}/{amount}")
            print(f"[DEBUG] Current time before advance: {self.game.current_time}")
            print(f"[DEBUG] Current active cards: {[(card.title, card.drawed_at) for card in self.game.active_cards]}")
            print(f"[DEBUG] Current card queue: {[(card.title, card.drawed_at) for card in self.game.card_queue]}")
            
            # In manual mode, we should advance time even if there are non-immediate cards
            if not self.game.advance_time(mode="manual"):
                print("[DEBUG] advance_time returned False, stopping manual advance")
                break
                
            # Only stop if we drew any immediate cards
            immediate_cards = [card for card in self.game.active_cards if card.card_type == "immediate"]
            if immediate_cards:
                print(f"[DEBUG] Immediate cards drawn during advance, stopping manual advance")
                print(f"[DEBUG] Immediate cards: {[card.title for card in immediate_cards]}")
                break
                
            print(f"[DEBUG] Successfully advanced to time {self.game.current_time}")
            print(f"[DEBUG] Active cards after advance: {[(card.title, card.drawed_at) for card in self.game.active_cards]}")
            print(f"[DEBUG] Card queue after advance: {[(card.title, card.drawed_at) for card in self.game.card_queue]}")
            
        print("[DEBUG] ===== End of manual_time_advance =====")
        self.update_display(force_clear_preview=True)

    def save_game_state(self):
        # Implement the logic to save the game state
        print("Saving game state")

def main():
    app = QApplication([])
    
    # Set application style
    app.setStyle("Fusion")
    
    window = GameWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main() 