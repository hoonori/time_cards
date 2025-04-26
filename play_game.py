from backend.game_state import GameState
from pathlib import Path

def display_resources(game: GameState):
    print("\n=== Resources ===")
    for resource, amount in game.resources.items():
        print(f"{game.resource_config['resources'][resource]['name']}: {amount}")

def display_relics(game: GameState):
    if game.relics:
        print("\n=== Relics ===")
        for relic in game.relics:
            print(f"{relic.name}: {relic.description}")

def display_active_cards(game: GameState):
    print("\n=== Active Cards ===")
    for i, card in enumerate(game.active_cards):
        print(f"\nCard {i + 1}: {card.title}")
        print(f"Description: {card.description}")
        print("Choices:")
        for j, choice in enumerate(card.choices):
            can_make = game.can_make_choice(i, j)
            status = "✓" if can_make else "✗"
            print(f"  {j + 1}. [{status}] {choice['description']}")
            if "requirements" in choice:
                if "resources" in choice["requirements"]:
                    print("     Required resources:")
                    for resource, amount in choice["requirements"]["resources"].items():
                        print(f"       - {resource}: {amount}")
                if "relics" in choice["requirements"]:
                    print("     Required relics:")
                    for relic in choice["requirements"]["relics"]:
                        print(f"       - {relic}")

def main():
    config_path = Path("config")
    game = GameState(config_path)
    
    print("Welcome to the Card Game!")
    print("You start with a mysterious letter...")
    
    while not game.is_game_over():
        print(f"\nTime: {game.current_time}")
        display_resources(game)
        display_relics(game)
        display_active_cards(game)
        
        if not game.active_cards:
            print("\nAdvancing time to next event...")
            game.advance_time()
            continue
            
        try:
            card_choice = input("\nWhich card do you want to act on? (1-{}, or 'q' to quit): ".format(len(game.active_cards)))
            if card_choice.lower() == 'q':
                break
                
            card_index = int(card_choice) - 1
            if not (0 <= card_index < len(game.active_cards)):
                print("Invalid card number!")
                continue
                
            choice = input(f"Which choice? (1-{len(game.active_cards[card_index].choices)}): ")
            choice_index = int(choice) - 1
            
            if game.can_make_choice(card_index, choice_index):
                game.make_choice(card_index, choice_index)
                print("\nChoice made! Moving forward...")
            else:
                print("\nCannot make that choice - requirements not met!")
                
        except ValueError:
            print("Please enter valid numbers!")
            continue
            
    print("\nGame Over!")
    print("Final state:")
    display_resources(game)
    display_relics(game)

if __name__ == "__main__":
    main() 