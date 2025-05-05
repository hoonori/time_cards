import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from .game_loader import GameLoader

@dataclass
class Card:
    title: str
    description: str
    drawed_at: int
    priority: int
    choices: List[Dict]

    def to_dict(self) -> Dict:
        """Convert Card object to serializable dictionary"""
        return {
            "title": self.title,
            "description": self.description,
            "drawed_at": self.drawed_at,
            "priority": self.priority,
            "choices": self.choices
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        """Create Card object from dictionary"""
        return cls(**data)

@dataclass
class Relic:
    name: str
    description: str
    passive_effects: List[Dict]

    def to_dict(self) -> Dict:
        """Convert Relic object to serializable dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "passive_effects": self.passive_effects
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Relic':
        """Create Relic object from dictionary"""
        return cls(**data)

class GameState:
    def __init__(self, config_path: Path, mode: str = "life"):
        # Load configurations using GameLoader
        config = GameLoader.load_config(mode)
        self.resource_config = config['resource_config']
        self.relic_config = config['relic_config']
        self.card_config = config['card_config']
            
        # Initialize game state
        self.current_time = 0
        self.resources = self._init_resources()
        self.relics = []
        self.active_cards = self._init_starting_cards()
        self.card_queue = []  # Cards to be drawn in future
        
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
                    priority=card_data["priority"],
                    choices=card_data["choices"]
                ))
        return sorted(starting_cards, key=lambda x: x.priority)
    
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
    
    def make_choice(self, card_index: int, choice_index: int) -> bool:
        """Apply the effects of a choice"""
        if not self.can_make_choice(card_index, choice_index):
            return False
            
        card = self.active_cards[card_index]
        choice = card.choices[choice_index]
        effects = choice.get("effects", {})
        
        # Apply resource changes
        if "resources" in effects:
            for resource, change in effects["resources"].items():
                self.resources[resource] += change
                
        # Add/remove relics
        if "relics" in effects:
            if "gain" in effects["relics"]:
                for relic_id in effects["relics"]["gain"]:
                    if relic_id in self.relic_config["relics"]:
                        relic_data = self.relic_config["relics"][relic_id]
                        self.relics.append(Relic(
                            name=relic_data["name"],
                            description=relic_data["description"],
                            passive_effects=relic_data["passive_effects"]
                        ))
            if "lose" in effects["relics"]:
                for relic_id in effects["relics"]["lose"]:
                    self.relics = [r for r in self.relics if r.name != relic_id]
                    
        # Queue next cards
        if "next_cards" in effects:
            for next_card in effects["next_cards"]:
                card_data = self.card_config["cards"][next_card["card"]]
                self.card_queue.append(Card(
                    title=card_data["title"],
                    description=card_data["description"],
                    drawed_at=self.current_time + next_card["time_offset"],
                    priority=card_data.get("priority", 1),
                    choices=card_data["choices"]
                ))
                
        # Remove the card that was chosen
        self.active_cards.pop(card_index)
        
        # If there are other cards at the same time, automatically select the highest priority one
        if self.active_cards:
            highest_priority_card = max(self.active_cards, key=lambda x: (x.priority, -x.drawed_at))
            highest_priority_index = self.active_cards.index(highest_priority_card)
            # Find the first available choice
            for choice_idx in range(len(highest_priority_card.choices)):
                if self.can_make_choice(highest_priority_index, choice_idx):
                    self.make_choice(highest_priority_index, choice_idx)
                    break
        
        return True
    
    def advance_time(self) -> None:
        """Move time forward and process passive effects"""
        if not self.active_cards and not self.card_queue:
            return  # Game is over
            
        # Find next event time
        next_time = float('inf')
        if self.card_queue:
            next_time = min(card.drawed_at for card in self.card_queue)
            
        # Move time forward
        time_delta = next_time - self.current_time
        self.current_time = next_time
        
        # Apply passive effects from relics
        for relic in self.relics:
            for effect in relic.passive_effects:
                if effect["type"] == "resource_per_time":
                    # Check requirements if any
                    if "requirements" in effect:
                        for res, req in effect["requirements"].items():
                            if "min" in req and self.resources[res] < req["min"]:
                                continue
                            if "max" in req and self.resources[res] > req["max"]:
                                continue
                    
                    # Calculate and apply resource change
                    intervals = time_delta // effect["interval"]
                    if intervals > 0:
                        self.resources[effect["resource"]] += effect["amount"] * intervals
        
        # Draw new cards
        new_active_cards = [
            card for card in self.card_queue
            if card.drawed_at == self.current_time
        ]
        self.card_queue = [
            card for card in self.card_queue
            if card.drawed_at > self.current_time
        ]
        self.active_cards.extend(sorted(new_active_cards, key=lambda x: x.priority))
    
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
            "card_queue": [card.to_dict() for card in self.card_queue]
        }

    @classmethod
    def from_dict(cls, data: Dict, config_path: Path, mode: str) -> 'GameState':
        """Create GameState from dictionary"""
        # Create new instance with config
        state = cls(config_path, mode)
        
        # Restore state from data
        state.current_time = data["current_time"]
        state.resources = data["resources"]
        state.relics = [Relic.from_dict(r_data) for r_data in data["relics"]]
        state.active_cards = [Card.from_dict(c_data) for c_data in data["active_cards"]]
        state.card_queue = [Card.from_dict(q_data) for q_data in data["card_queue"]]
        
        return state 