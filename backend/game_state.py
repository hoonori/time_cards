import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from .game_loader import GameLoader
import time

@dataclass
class Card:
    title: str
    description: str
    drawed_at: int
    priority: int
    choices: List[Dict]
    card_type: str = "delayed"  # Default to delayed type
    requirements: Optional[Dict] = None  # Optional requirements for drawing the card
    stack_count: int = 1  # Initialize stack count to 1

    def to_dict(self) -> Dict:
        """Convert Card object to serializable dictionary"""
        return {
            "title": self.title,
            "description": self.description,
            "drawed_at": self.drawed_at,
            "priority": self.priority,
            "choices": self.choices,
            "card_type": self.card_type,
            "requirements": self.requirements,
            "stack_count": self.stack_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        """Create Card object from dictionary"""
        card = cls(
            title=data["title"],
            description=data["description"],
            drawed_at=data["drawed_at"],
            priority=data["priority"],
            choices=data["choices"],
            card_type=data.get("card_type", "delayed"),
            requirements=data.get("requirements")
        )
        card.stack_count = data.get("stack_count", 1)
        return card

@dataclass
class GameEvent:
    """Represents a single game event that caused resource changes"""
    timestamp: int
    event_type: str  # 'card_choice', 'relic_effect', 'time_advance'
    source: str  # Card title or relic name
    description: str
    resource_changes: Dict[str, int]
    requirements_met: bool = True

@dataclass
class Relic:
    name: str
    description: str
    passive_effects: List[Dict]
    count: int = 1  # Default to 1 for non-stackable relics

    def to_dict(self) -> Dict:
        """Convert Relic object to serializable dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "passive_effects": self.passive_effects,
            "count": self.count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Relic':
        """Create Relic object from dictionary"""
        return cls(**data)

@dataclass
class PolicyRule:
    card_title: str
    choice_description: str

class Policy:
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self.target_time: Optional[int] = None
        self.is_relative: bool = False
        self.is_unlimited: bool = False
        self.base_time: Optional[int] = None  # 기준 시간

    def add_rule(self, card_title: str, choice_description: str):
        """Add a new rule to the policy"""
        self.rules.append(PolicyRule(card_title, choice_description))

    def remove_rule(self, index: int):
        """Remove a rule at the specified index"""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)

    def reorder_rule(self, from_index: int, to_index: int):
        """Move a rule from one position to another"""
        if 0 <= from_index < len(self.rules) and 0 <= to_index < len(self.rules):
            rule = self.rules.pop(from_index)
            self.rules.insert(to_index, rule)

    def set_target_time(self, time_str: str, current_time: int = 0):
        """Set the target time for policy execution
        Args:
            time_str: Can be:
                - "-1" for unlimited execution
                - "+N" for relative time (current_time + N)
                - "N" for absolute time N
            current_time: The current time when policy execution starts
        """
        if time_str == "-1":
            self.is_unlimited = True
            self.is_relative = False
            self.target_time = None
            self.base_time = None
        elif time_str.startswith("+"):
            self.is_unlimited = False
            self.is_relative = True
            self.target_time = int(time_str[1:])
            self.base_time = current_time  # 기준 시간 저장
            print(f"[DEBUG][Policy] Set relative target_time: base_time={self.base_time}, target_time={self.target_time}")
        else:
            self.is_unlimited = False
            self.is_relative = False
            self.target_time = int(time_str)
            self.base_time = None
            print(f"[DEBUG][Policy] Set absolute target_time: {self.target_time}")

    def get_target_time(self, current_time: int) -> Optional[int]:
        """Get the actual target time based on current time"""
        if self.is_unlimited:
            return None
        if self.is_relative:
            return (self.base_time or 0) + self.target_time
        return self.target_time

    def find_matching_choice(self, card: Card) -> Optional[int]:
        """Find the index of the first matching choice for a card based on policy rules"""
        for rule in self.rules:
            if rule.card_title == card.title:
                for i, choice in enumerate(card.choices):
                    if choice["description"] == rule.choice_description:
                        return i
        return None

class GameState:
    def __init__(self, config_path: Path, mode: str = "life", skip_card_init: bool = False):
        # Load configurations using GameLoader
        config = GameLoader.load_config(mode)
        self.resource_config = config['resource_config']
        self.relic_config = config['relic_config']
        self.card_config = config['card_config']
            
        # Initialize game state
        self.current_time = 0
        self.resources = self._init_resources()
        self.relics = []
        if not skip_card_init:
            self.active_cards = self._init_starting_cards()
            self.card_queue = self._init_future_cards()
        else:
            self.active_cards = []
            self.card_queue = []
        print(f"[DEBUG][GameState] Initialized active_cards: {[ (c.title, c.drawed_at, [ch['description'] for ch in c.choices]) for c in self.active_cards ]}")
        self.effect_timers = {}  # Track when effects were last applied
        self.event_history: List[GameEvent] = []  # Track game events
        self.policy = Policy()  # Initialize policy
        self._on_action_callbacks = []  # For observer pattern
        
    def _init_resources(self) -> Dict[str, int]:
        """Initialize resources with their starting amounts"""
        return {
            name: config["initial_amount"]
            for name, config in self.resource_config["resources"].items()
        }
        
    def _init_starting_cards(self) -> List[Card]:
        """Get cards that start at t=0"""
        starting_cards = []
        for card_id, card_data in self.card_config["cards"].items():
            if card_data.get("drawed_at", None) == 0:
                starting_cards.append(Card(
                    title=card_data["title"],
                    description=card_data["description"],
                    drawed_at=0,
                    priority=card_data.get("priority", 1),
                    choices=card_data["choices"],
                    card_type=card_data.get("card_type", "delayed"),
                    requirements=card_data.get("requirements")  # Pass requirements from card config
                ))
        print(f"[DEBUG][GameState] _init_starting_cards: {[ (c.title, c.drawed_at, [ch['description'] for ch in c.choices]) for c in starting_cards ]}")
        return sorted(starting_cards, key=lambda x: x.priority)
    
    def _init_future_cards(self) -> List[Card]:
        """Get cards that are scheduled for future times (drawed_at > 0)"""
        future_cards = []
        for card_id, card_data in self.card_config["cards"].items():
            if card_data.get("drawed_at", None) and card_data["drawed_at"] > 0:
                future_cards.append(Card(
                    title=card_data["title"],
                    description=card_data["description"],
                    drawed_at=card_data["drawed_at"],
                    priority=card_data.get("priority", 1),
                    choices=card_data["choices"],
                    card_type=card_data.get("card_type", "delayed"),
                    requirements=card_data.get("requirements")  # Pass requirements from card config
                ))
        return sorted(future_cards, key=lambda x: (x.drawed_at, x.priority))
    
    def can_make_choice(self, card_index: int, choice_index: int) -> bool:
        """Check if player has required resources/relics for a choice"""
        if not (0 <= card_index < len(self.active_cards)):
            return False
            
        card = self.active_cards[card_index]
        if not (0 <= choice_index < len(card.choices)):
            return False
            
        choice = card.choices[choice_index]
        if "requirements" not in choice:
            return True
            
        # Check resource requirements
        if "resources" in choice["requirements"]:
            for resource, amount in choice["requirements"]["resources"].items():
                if self.resources[resource] < amount:
                    return False
                    
        # Check relic requirements
        if "relics" in choice["requirements"]:
            required_relics = set(choice["requirements"]["relics"])
            player_relics = set(relic.name for relic in self.relics)
            if not required_relics.issubset(player_relics):
                return False
                
        return True

    def validate_resource_change(self, resource: str, change: int) -> bool:
        """Validate if a resource change is allowed"""
        config = self.resource_config["resources"][resource]
        new_amount = self.resources[resource] + change
        
        # Check if negative values are allowed
        if not config.get("allow_negative", False) and new_amount < 0:
            return False
            
        # Check min/max bounds
        if "min_amount" in config and new_amount < config["min_amount"]:
            return False
        if "max_amount" in config and new_amount > config["max_amount"]:
            return False
            
        return True

    def _check_and_draw_current_cards(self) -> None:
        """Check and draw any cards that are due at or before current time"""
        print(f"\n[DEBUG] === Checking for cards to draw at time {self.current_time} ===")
        print(f"[DEBUG] Current card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        
        # Find cards that are due at or before current time
        due_cards = [card for card in self.card_queue if card.drawed_at <= self.current_time]
        if due_cards:
            print(f"[DEBUG] Found {len(due_cards)} cards due at or before time {self.current_time}")
            self._draw_cards()
        else:
            print(f"[DEBUG] No cards due at or before time {self.current_time}")

    def register_on_action_callback(self, callback):
        print("[DEBUG][CALLBACK] register_on_action_callback called")
        self._on_action_callbacks.append(callback)
        print(f"[DEBUG][CALLBACK] callbacks after registration: {self._on_action_callbacks}")
        print(f"[DEBUG][CALLBACK] game_state id: {id(self)}")
    
    def _trigger_on_action(self, message=""):
        print(f"[DEBUG][CALLBACK] _trigger_on_action called with message: {message}")
        for cb in self._on_action_callbacks:
            print("[DEBUG][CALLBACK] Calling callback...")
            cb(self, message=message)

    def make_choice(self, card_index: int, choice_index: int) -> bool:
        """Apply the effects of a choice"""
        print(f"\n[DEBUG] === Making choice for card {card_index}, choice {choice_index} ===")
        print(f"[DEBUG] Current resources before choice: {self.resources}")
        
        if not self.can_make_choice(card_index, choice_index):
            print("[DEBUG] Cannot make choice: requirements not met")
            return False
            
        card = self.active_cards[card_index]
        choice = card.choices[choice_index]
        effects = choice.get("effects", {})
        
        print(f"[DEBUG] Card: {card.title}")
        print(f"[DEBUG] Choice: {choice['description']}")
        print(f"[DEBUG] Effects: {effects}")
        
        # Create event for this choice
        event = GameEvent(
            timestamp=self.current_time,
            event_type='card_choice',
            source=card.title,
            description=f"Chose: {choice['description']}",
            resource_changes=effects.get("resources", {}),
            requirements_met=True
        )
        self.event_history.append(event)
        
        # Apply resource changes
        if "resources" in effects:
            print("[DEBUG] Applying resource changes:")
            for resource, change in effects["resources"].items():
                old_value = self.resources[resource]
                self.resources[resource] += change
                print(f"[DEBUG] {resource}: {old_value} -> {self.resources[resource]} (change: {change})")
        
        print(f"[DEBUG] Resources after choice: {self.resources}")
                
        # Add/remove relics
        if "relics" in effects:
            print("[DEBUG] Processing relic changes:")
            if "gain" in effects["relics"]:
                for relic_id in effects["relics"]["gain"]:
                    if relic_id in self.relic_config["relics"]:
                        relic_data = self.relic_config["relics"][relic_id]
                        # Check if relic already exists
                        existing_relic = next((r for r in self.relics if r.name == relic_data["name"]), None)
                        if existing_relic:
                            old_count = existing_relic.count
                            existing_relic.count += 1
                            print(f"[DEBUG] Increased {relic_data['name']} count: {old_count} -> {existing_relic.count}")
                        else:
                            self.relics.append(Relic(
                                name=relic_data["name"],
                                description=relic_data["description"],
                                passive_effects=relic_data["passive_effects"]
                            ))
                            print(f"[DEBUG] Added new relic: {relic_data['name']}")
            if "lose" in effects["relics"]:
                for relic_id in effects["relics"]["lose"]:
                    self.relics = [r for r in self.relics if r.name != relic_id]
                    print(f"[DEBUG] Removed relic: {relic_id}")
                    
        # Queue next cards
        if "next_cards" in effects:
            print("[DEBUG] Queueing next cards:")
            for next_card in effects["next_cards"]:
                card_data = self.card_config["cards"][next_card["card"]]
                draw_time = self.current_time + next_card["time_offset"]
                print(f"[DEBUG] Queueing card {next_card['card']} for time {draw_time} (current: {self.current_time}, offset: {next_card['time_offset']})")
                self.card_queue.append(Card(
                    title=card_data["title"],
                    description=card_data["description"],
                    drawed_at=draw_time,
                    priority=card_data.get("priority", 1),
                    choices=card_data["choices"],
                    card_type=card_data.get("card_type", "delayed"),
                    requirements=card_data.get("requirements")  # Pass requirements from card config
                ))
            
            # After queueing new cards, check if any are due to be drawn
            self._check_and_draw_current_cards()
                
        # Handle stacked cards
        if card.stack_count > 1:
            # Decrease stack count instead of removing the card
            card.stack_count -= 1
            print(f"[DEBUG] Decreased stack count for {card.title} to {card.stack_count}")
        else:
            # Remove the card that was chosen
            self.active_cards.pop(card_index)
            print(f"[DEBUG] Removed card from active cards: {card.title}")
        
        # If there are other cards at the same time, automatically select the highest priority one
        # BUT only if they were already active before this choice was made
        if self.active_cards:
            # Stop auto-choice if any immediate cards remain
            if any(card.card_type == "immediate" for card in self.active_cards):
                print("[DEBUG] Stopping auto-choice due to immediate cards")
                return True
                
            # Get the current time to identify newly drawn cards
            current_time = self.current_time
            
            # Filter out cards that were just drawn (they will have the current time)
            existing_cards = [card for card in self.active_cards if card.drawed_at < current_time]
            if existing_cards:
                # Only auto-select if this wasn't an auto-selected choice
                if not hasattr(self, '_auto_selecting'):
                    self._auto_selecting = True
                    highest_priority_card = max(existing_cards, key=lambda x: (x.priority, -x.drawed_at))
                    highest_priority_index = self.active_cards.index(highest_priority_card)
                    print(f"[DEBUG] Auto-selecting highest priority existing card: {highest_priority_card.title}")
                    # Find the first available choice
                    for choice_idx in range(len(highest_priority_card.choices)):
                        if self.can_make_choice(highest_priority_index, choice_idx):
                            print(f"[DEBUG] Auto-making choice {choice_idx} for {highest_priority_card.title}")
                            self.make_choice(highest_priority_index, choice_idx)
                            break
                    self._auto_selecting = False
            else:
                print("[DEBUG] No existing cards to auto-select")
        
        print(f"[DEBUG] === End of make_choice ===\n")
        self._trigger_on_action(message="Card choice")
        return True
    
    def get_effect_countdowns(self) -> Dict[str, Dict[str, int]]:
        """Get countdowns for all relic effects"""
        countdowns = {}
        for relic in self.relics:
            for effect in relic.passive_effects:
                if effect["type"] == "resource_per_time":
                    key = f"{relic.name}_{effect['resource']}"
                    if key not in self.effect_timers:
                        self.effect_timers[key] = 0
                    time_since_last = self.current_time - self.effect_timers[key]
                    remaining = effect["interval"] - (time_since_last % effect["interval"])
                    countdowns[key] = {
                        "relic": relic.name,
                        "resource": effect["resource"],
                        "amount": effect["amount"] * relic.count,
                        "remaining": remaining,
                        "interval": effect["interval"]
                    }
        return countdowns

    def _draw_cards(self) -> None:
        """Draw new cards for the current time"""
        # Draw new cards
        new_active_cards = []
        cards_to_remove = []  # Track cards that should be removed from queue
        print(f"\n[DEBUG] === Drawing cards at time {self.current_time} ===")
        print(f"[DEBUG] Initial active cards: {[(card.title, card.drawed_at, card.stack_count) for card in self.active_cards]}")
        print(f"[DEBUG] Initial card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        
        for card in self.card_queue:
            print(f"\n[DEBUG] Processing card in queue: {card.title}")
            print(f"[DEBUG] Card drawed_at: {card.drawed_at}")
            print(f"[DEBUG] Current time: {self.current_time}")
            
            # Check if this exact card instance is already active
            card_already_active = False
            for active_card in self.active_cards:
                if active_card is card:  # Check if it's the same card instance
                    card_already_active = True
                    print(f"[DEBUG] Found exact card instance already active: {active_card.title} (time {active_card.drawed_at})")
                    break
            
            print(f"[DEBUG] Card already in active cards: {card_already_active}")
            
            if card.drawed_at <= self.current_time:
                print(f"[DEBUG] Card {card.title} is due to be drawn")
                print(f"[DEBUG] Card requirements: {card.requirements}")
                print(f"[DEBUG] Current relics: {[r.name for r in self.relics]}")
                
                # Check if card has requirements
                can_draw = True
                if card.requirements is not None:
                    # Check relic requirements
                    if 'relics' in card.requirements:
                        required_relics = {r.lower() for r in card.requirements['relics']}
                        player_relics = {r.name.lower() for r in self.relics}
                        print(f"[DEBUG] Required relics: {required_relics}")
                        print(f"[DEBUG] Player relics: {player_relics}")
                        if not required_relics.issubset(player_relics):
                            can_draw = False
                            print(f"[DEBUG] Card {card.title} cannot be drawn: missing required relics")
                if can_draw:
                    if not card_already_active:
                        # Check if we have a similar card already active (only check title)
                        similar_card = next(
                            (c for c in self.active_cards 
                             if c.title == card.title),  # Only check title, ignore drawed_at
                            None
                        )
                        if similar_card:
                            # Stack the card
                            similar_card.stack_count += 1
                            print(f"[DEBUG] Stacked card {card.title} (new count: {similar_card.stack_count})")
                            cards_to_remove.append(card)  # Add to removal list when stacked
                        else:
                            # Add as new card
                            new_active_cards.append(card)
                            print(f"[DEBUG] Card {card.title} will be drawn")
                    else:
                        print(f"[DEBUG] Card {card.title} (time {card.drawed_at}) already in active cards, skipping")
            else:
                print(f"[DEBUG] Card {card.title} is not due yet (drawed_at: {card.drawed_at})")
        
        print(f"\n[DEBUG] New cards to draw: {[(card.title, card.drawed_at) for card in new_active_cards]}")
        print(f"[DEBUG] Cards to remove from queue: {[(card.title, card.drawed_at) for card in cards_to_remove]}")
        
        # Remove cards that were either drawn or stacked
        self.card_queue = [
            card for card in self.card_queue
            if card not in new_active_cards and card not in cards_to_remove
        ]
        print(f"[DEBUG] Remaining card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        
        self.active_cards.extend(sorted(new_active_cards, key=lambda x: x.priority))
        print(f"[DEBUG] Final active cards: {[(card.title, card.drawed_at, card.stack_count) for card in self.active_cards]}")
        print(f"[DEBUG] === End of drawing cards ===\n")

    def _process_passive_effects(self) -> None:
        """Process passive effects from relics"""
        print(f"\n[DEBUG] === Processing passive effects at time {self.current_time} ===")
        print(f"[DEBUG] Current resources before effects: {self.resources}")
        print(f"[DEBUG] Current relics: {[(r.name, r.count) for r in self.relics]}")
        
        # Apply passive effects from relics
        for relic in self.relics:
            for effect in relic.passive_effects:
                if effect["type"] == "resource_per_time":
                    # Check requirements if any
                    can_apply = True
                    if "requirements" in effect:
                        for req in effect["requirements"]:
                            if isinstance(req, dict):
                                # Check resource requirements
                                if "resource" in req:
                                    # If the requirement is stackable, multiply by relic count
                                    required_amount = req["amount"]
                                    if req.get("stackable", False):
                                        required_amount *= relic.count
                                    if self.resources[req["resource"]] < required_amount:
                                        can_apply = False
                                        print(f"[DEBUG] Cannot apply effect: {req['resource']} < {required_amount}")
                                        break
                                # Check relic requirements
                                elif "relic" in req:
                                    if not any(r.name == req["relic"] for r in self.relics):
                                        can_apply = False
                                        print(f"[DEBUG] Cannot apply effect: missing required relic {req['relic']}")
                                        break
                            else:
                                # Simple requirement (just resource name)
                                if self.resources[req] <= 0:
                                    can_apply = False
                                    print(f"[DEBUG] Cannot apply effect: {req} <= 0")
                                    break
                    
                    if can_apply:
                        key = f"{relic.name}_{effect['resource']}"
                        if key not in self.effect_timers:
                            self.effect_timers[key] = 0
                        
                        # Calculate how many intervals have passed
                        time_since_last = self.current_time - self.effect_timers[key]
                        intervals = time_since_last // effect["interval"]
                        
                        if intervals > 0:
                            # Create event for this relic effect
                            event = GameEvent(
                                timestamp=self.current_time,
                                event_type='relic_effect',
                                source=relic.name,
                                description=f"Passive effect triggered ({intervals} intervals)",
                                resource_changes={effect["resource"]: effect["amount"] * intervals * relic.count},
                                requirements_met=True
                            )
                            self.event_history.append(event)
                            
                            # Apply the effect for each interval
                            amount = effect["amount"] * intervals * relic.count
                            self.resources[effect["resource"]] += amount
                            # Update the timer
                            self.effect_timers[key] = self.current_time
                            print(f"[DEBUG] Applied {amount} {effect['resource']} from {relic.name} (intervals: {intervals})")
        
        print(f"[DEBUG] Resources after effects: {self.resources}")
        print(f"[DEBUG] === End of processing passive effects ===\n")

    def _advance_time_core(self, target_time: int) -> bool:
        """Core time advancement logic that ensures consistent behavior across all modes.
        
        Args:
            target_time: The time to advance to
            
        Returns:
            bool: True if time was advanced successfully, False otherwise
        """
        print(f"\n[DEBUG] === _advance_time_core called ===")
        print(f"[DEBUG] Current time: {self.current_time}")
        print(f"[DEBUG] Target time: {target_time}")
        print(f"[DEBUG] Active cards: {[(card.title, card.drawed_at) for card in self.active_cards]}")
        print(f"[DEBUG] Card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        print(f"[DEBUG] Current resources: {self.resources}")
        
        # Check for immediate cards
        immediate_cards = [card for card in self.active_cards if card.card_type == "immediate"]
        if immediate_cards:
            print(f"[DEBUG] Cannot advance time: {len(immediate_cards)} immediate cards need to be handled")
            print(f"[DEBUG] Immediate cards: {[card.title for card in immediate_cards]}")
            return False
            
        if not self.active_cards and not self.card_queue:
            print("[DEBUG] No more cards to process")
            return False
            
        # Advance time and process passive effects
        print(f"[DEBUG] Advancing time from {self.current_time} to {target_time}")
        self.current_time = target_time
        self._process_passive_effects()
        
        # Draw cards for the new time
        print(f"[DEBUG] Drawing cards for new time {self.current_time}")
        self._draw_cards()
        
        print(f"[DEBUG] Final resources: {self.resources}")
        print(f"[DEBUG] === End of _advance_time_core ===")
        return True

    def advance_time(self, mode: str = "auto") -> bool:
        """Move time forward and process passive effects. Returns True if time was advanced.
        
        Args:
            mode: One of "auto", "manual", or "advance_cards"
                - auto: Only advance if no active cards (except immediate)
                - manual: Advance if no immediate cards
                - advance_cards: Jump to next card time
        """
        print(f"\n[DEBUG][TIME] ===== advance_time called with mode: {mode} =====")
        print(f"[DEBUG][TIME] Current time: {self.current_time}")
        print(f"[DEBUG][TIME] Active cards: {[(card.title, card.drawed_at) for card in self.active_cards]}")
        print(f"[DEBUG][TIME] Card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        
        # Handle different modes
        if mode == "auto":
            print("[DEBUG] Auto mode: checking for any active cards")
            if self.active_cards:
                print(f"[DEBUG] Have active cards at time {self.current_time}, not advancing time")
                return False
            target_time = self.current_time + 1
        elif mode == "manual":
            print("[DEBUG] Manual mode: advancing by 1 time unit")
            target_time = self.current_time + 1
        elif mode == "advance_cards":
            print("[DEBUG] Advance cards mode: finding next card time")
            if not self.card_queue:
                print("[DEBUG] No more cards in queue")
                return False
            target_time = min(card.drawed_at for card in self.card_queue)
            print(f"[DEBUG] Jumping to next card time: {target_time}")
        else:
            print(f"[DEBUG] Invalid mode: {mode}")
            return False
            
        # Use core time advancement logic
        result = self._advance_time_core(target_time)
        return result

    def is_game_over(self) -> bool:
        """Check if the game is over"""
        # No more cards to play
        if not self.active_cards and not self.card_queue:
            return True
            
        # Check resource-based game over conditions
        for resource, amount in self.resources.items():
            config = self.resource_config["resources"][resource]
            if "min_amount" in config and amount < config["min_amount"]:
                return True
            if "max_amount" in config and amount > config["max_amount"]:
                return True
                
        return False

    def to_dict(self) -> Dict:
        """Convert GameState to serializable dictionary"""
        return {
            "current_time": self.current_time,
            "resources": self.resources,
            "relics": [relic.to_dict() for relic in self.relics],
            "active_cards": [card.to_dict() for card in self.active_cards],
            "card_queue": [card.to_dict() for card in self.card_queue],
            "event_history": [
                {
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "source": event.source,
                    "description": event.description,
                    "resource_changes": event.resource_changes,
                    "requirements_met": event.requirements_met
                }
                for event in self.event_history
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict, config_path: Path, mode: str) -> 'GameState':
        """Create GameState from dictionary"""
        state = cls(config_path, mode, skip_card_init=True)
        state.current_time = data["current_time"]
        state.resources = data["resources"]
        state.relics = [Relic.from_dict(r_data) for r_data in data["relics"]]
        state.active_cards = [Card.from_dict(c_data) for c_data in data["active_cards"]]
        state.card_queue = [Card.from_dict(q_data) for q_data in data["card_queue"]]
        # Restore event history
        if "event_history" in data:
            state.event_history = [
                GameEvent(
                    timestamp=event["timestamp"],
                    event_type=event["event_type"],
                    source=event["source"],
                    description=event["description"],
                    resource_changes=event["resource_changes"],
                    requirements_met=event["requirements_met"]
                )
                for event in data["event_history"]
            ]
        return state 

    def manual_time_advance(self, amount: int) -> bool:
        """Manually advance time by the specified amount"""
        print(f"\n[DEBUG][TIME] ===== manual_time_advance called =====")
        print(f"[DEBUG][TIME] Attempting to advance time by {amount} units from {self.current_time}")
        
        # Check for immediate cards first
        immediate_cards = [card for card in self.active_cards if card.card_type == "immediate"]
        if immediate_cards:
            print(f"[DEBUG] Cannot advance time: {len(immediate_cards)} immediate cards need to be handled")
            print(f"[DEBUG] Immediate cards: {[card.title for card in immediate_cards]}")
            return False
            
        # Advance time step by step
        for i in range(amount):
            print(f"[DEBUG] Manual advance iteration {i+1}/{amount}")
            print(f"[DEBUG] Current time before advance: {self.current_time}")
            print(f"[DEBUG] Current active cards: {[(card.title, card.drawed_at) for card in self.active_cards]}")
            print(f"[DEBUG] Current card queue: {[(card.title, card.drawed_at) for card in self.card_queue]}")
            
            # Use core time advancement logic for each step
            if not self._advance_time_core(self.current_time + 1):
                print(f"[DEBUG] Failed to advance time at iteration {i+1}")
                return False
                
            print(f"[DEBUG] Successfully advanced to time {self.current_time}")
            print(f"[DEBUG] Active cards after advance: {[(card.title, card.drawed_at) for card in self.active_cards]}")
            print(f"[DEBUG] Card queue after advance: {[(card.title, card.drawed_at) for card in self.card_queue]}")
        
        print(f"[DEBUG] ===== End of manual_time_advance =====")
        return True 

    def execute_policy(self) -> bool:
        """Execute the current policy. Returns True if policy execution should continue."""
        print(f"\n[DEBUG][POLICY] === Executing policy at time {self.current_time} ===")
        print(f"[DEBUG][POLICY] Policy state: is_unlimited={self.policy.is_unlimited}, is_relative={self.policy.is_relative}, base_time={self.policy.base_time}, target_time={self.policy.target_time}")
        target_time = self.policy.get_target_time(self.current_time)
        print(f"[DEBUG][POLICY] Policy get_target_time(current_time={self.current_time}) -> {target_time}")
        if target_time is not None and self.current_time >= target_time:
            print(f"[DEBUG][POLICY] Reached target time {target_time}, stopping policy execution at current_time {self.current_time}")
            return False

        # Check if we have any active cards
        if not self.active_cards:
            print("[DEBUG] No active cards, advancing time")
            return self.advance_time(mode="auto")

        # Find the first card that has a matching policy choice
        found_match = False
        for i, card in enumerate(self.active_cards):
            choice_index = self.policy.find_matching_choice(card)
            if choice_index is not None and self.can_make_choice(i, choice_index):
                print(f"[DEBUG] Found matching policy choice for {card.title}: {card.choices[choice_index]['description']}")
                self.make_choice(i, choice_index)
                found_match = True
                return True

        # If we get here, we have cards but none match the policy or are selectable
        print("[DEBUG] No matching policy choices found or none are selectable.")
        # Check if any card is selectable at all
        any_selectable = False
        for i, card in enumerate(self.active_cards):
            for j, choice in enumerate(card.choices):
                if self.can_make_choice(i, j):
                    any_selectable = True
                    break
            if any_selectable:
                break
        if not any_selectable:
            print("[DEBUG] No selectable choices for any active card. Advancing time (manual mode).")
            advanced = self.manual_time_advance(1)
            if not advanced:
                print("[DEBUG] Time could not be advanced (manual). Stopping policy execution to prevent infinite loop.")
                return False
            return True
        else:
            print("[DEBUG] There are selectable choices, but none match the policy. Stopping policy execution.")
            return False

    def run_policy(self) -> None:
        """Run the policy until it stops"""
        iteration = 0
        while True:
            print(f"[DEBUG][POLICY] run_policy loop iteration {iteration}, current_time={self.current_time}")
            should_continue = self.execute_policy()
            print(f"[DEBUG][POLICY] run_policy loop iteration {iteration} result: should_continue={should_continue}, current_time={self.current_time}")
            iteration += 1
            if not should_continue:
                print(f"[DEBUG][POLICY] run_policy exiting at iteration {iteration}, current_time={self.current_time}")
                break 

def save_callback(game_state, message=""):
    try:
        print(f"[DEBUG][CALLBACK] save_callback called with message: {message}")
        print(f"[DEBUG][CALLBACK] save_callback: state_manager id={{id(state_manager)}}, game_state id={{id(game_state)}}")
        state_manager.save_state(game_state, message=message or "Policy action")
    except Exception as e:
        print(f"[DEBUG][CALLBACK] save_callback exception: {e}") 