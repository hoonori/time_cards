import yaml
from pathlib import Path
from typing import Dict, List, Optional

class GameLoader:
    """Handles loading game configurations and initializing game states"""
    
    @staticmethod
    def get_available_modes() -> List[str]:
        """Get list of available game modes from config directory"""
        config_path = Path("config")
        return [d.name for d in config_path.iterdir() if d.is_dir()]
    
    @staticmethod
    def get_mode_description(mode: str) -> Optional[str]:
        """Get description for a game mode"""
        desc_file = Path("config") / mode / "description.txt"
        if desc_file.exists():
            try:
                with open(desc_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Error reading mode description: {e}")
        return None
    
    @staticmethod
    def load_config(mode: str) -> Dict:
        """Load all configuration files for a mode"""
        mode_path = Path("config") / mode
        
        try:
            # Load resources
            with open(mode_path / "resources.yaml", 'r', encoding='utf-8') as f:
                resource_config = yaml.safe_load(f)
            
            # Load relics
            with open(mode_path / "relics.yaml", 'r', encoding='utf-8') as f:
                relic_config = yaml.safe_load(f)
            
            # Load cards
            with open(mode_path / "cards.yaml", 'r', encoding='utf-8') as f:
                card_config = yaml.safe_load(f)
            
            return {
                'resource_config': resource_config,
                'relic_config': relic_config,
                'card_config': card_config
            }
        except Exception as e:
            raise RuntimeError(f"Error loading game configuration for mode '{mode}': {str(e)}")
    
    @staticmethod
    def create_game_state(mode: str) -> Dict:
        """Create configuration data for a new game state"""
        config_path = Path("config")
        return GameLoader.load_config(mode) 