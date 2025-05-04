import uuid
import time
import json
import hashlib
from typing import Dict, Optional, List
from pathlib import Path
from backend.game_state import GameState

class StateNode:
    """Represents a single state in the game's history"""
    def __init__(self, state_dict_json: str, parent_id: Optional[str] = None, message: str = ""):
        # Generate state hash from the state data
        state_dict = json.loads(state_dict_json)
        # Create a hashable string from the state
        state_str = json.dumps({
            'resources': state_dict['resources'],
            'relics': state_dict['relics'],
            'active_cards': state_dict['active_cards'],
            'card_queue': state_dict['card_queue']
        }, sort_keys=True)  # sort_keys to ensure consistent ordering
        self.node_id = hashlib.sha256(state_str.encode()).hexdigest()[:8]  # Use first 8 chars for readability
        
        self.parent_id = parent_id
        self.child_ids: List[str] = []
        self.last_played = time.time()  # Renamed from timestamp to last_played
        self.message = message
        self.state_dict_json = state_dict_json

class StateManager:
    """Manages the tree of game states"""
    def __init__(self, config_path: Path, mode: str):
        self.nodes: Dict[str, StateNode] = {}
        self.current_node_id: Optional[str] = None
        self.root_node_id: Optional[str] = None
        self.config_path = config_path
        self.mode = mode

    def initialize(self, initial_game_state: GameState) -> None:
        """Initialize the state manager with the initial game state"""
        if not self.nodes:
            state_dict = initial_game_state.to_dict()
            state_json = json.dumps(state_dict)
            root_node = StateNode(state_json, parent_id=None, message="Initial State")
            self.nodes[root_node.node_id] = root_node
            self.root_node_id = root_node.node_id
            self.current_node_id = root_node.node_id
            print(f"History initialized with root node: {self.root_node_id}")

    def save_state(self, current_game_state: GameState, message: str = "") -> str:
        """Save the current game state and return the node ID"""
        if self.current_node_id is None:
            raise Exception("StateManager not initialized.")

        parent_id = self.current_node_id
        state_dict = current_game_state.to_dict()
        state_json = json.dumps(state_dict)

        # Create new node
        new_node = StateNode(state_json, parent_id=parent_id, message=message)
        
        # Check if this state already exists
        if new_node.node_id in self.nodes:
            # Update the existing node's last_played and message
            existing_node = self.nodes[new_node.node_id]
            existing_node.last_played = time.time()
            existing_node.message = message
            # Update parent-child relationship if needed
            if parent_id and new_node.node_id not in self.nodes[parent_id].child_ids:
                self.nodes[parent_id].child_ids.append(new_node.node_id)
            self.current_node_id = new_node.node_id
            print(f"Updated existing state: {new_node.node_id}")
            return new_node.node_id
        
        # If it's a new state, add it to the tree
        self.nodes[new_node.node_id] = new_node
        if parent_id:
            self.nodes[parent_id].child_ids.append(new_node.node_id)
        self.current_node_id = new_node.node_id
        print(f"Saved new state: {new_node.node_id}")
        return new_node.node_id

    def load_state(self, node_id: str) -> GameState:
        """Load a game state from a specific node"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found.")

        node_to_load = self.nodes[node_id]
        state_dict = json.loads(node_to_load.state_dict_json)
        loaded_game_state = GameState.from_dict(state_dict, self.config_path, self.mode)

        self.current_node_id = node_id
        print(f"Loaded state from node: {node_id}")
        return loaded_game_state

    def get_tree_structure(self) -> List[Dict]:
        """Get the tree structure for visualization"""
        structure = []
        for node_id, node in self.nodes.items():
            structure.append({
                'id': node.node_id,
                'parent': node.parent_id,
                'message': node.message,
                'last_played': node.last_played,
                'is_current': node.node_id == self.current_node_id,
                'children': node.child_ids
            })
        return structure

    def save_to_file(self, filepath: str = "game_history.json") -> None:
        """Save the entire state history to a file"""
        data = {
            'nodes': {
                node_id: {
                    'parent_id': node.parent_id,
                    'child_ids': node.child_ids,
                    'last_played': node.last_played,
                    'message': node.message,
                    'state_dict_json': node.state_dict_json
                }
                for node_id, node in self.nodes.items()
            },
            'current_node_id': self.current_node_id,
            'root_node_id': self.root_node_id
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filepath: str = "game_history.json") -> None:
        """Load the state history from a file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.nodes = {}
        for node_id, node_data in data['nodes'].items():
            self.nodes[node_id] = StateNode(
                state_dict_json=node_data['state_dict_json'],
                parent_id=node_data['parent_id'],
                message=node_data['message']
            )
            self.nodes[node_id].child_ids = node_data['child_ids']
            self.nodes[node_id].last_played = node_data['last_played']
        
        self.current_node_id = data['current_node_id']
        self.root_node_id = data['root_node_id'] 