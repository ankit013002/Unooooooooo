import pygame
import socket
import threading
import os

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((1600, 900))
pygame.display.set_caption("Client")

# Load card images
CARD_IMAGES = {}
colors = ['Blue', 'Green', 'Red', 'Yellow']
values = [str(i) for i in range(10)] + ["Skip", "Reverse", "Draw"]

for color in colors:
    for value in values:
        image_path = os.path.join('Cards', f"{color} {value}.png")
        try:
            CARD_IMAGES[f"{color} {value}"] = pygame.image.load(image_path)
            print(f"Loaded image: {image_path}")
        except pygame.error as e:
            print(f"Failed to load image: {image_path}, {e}")
        except FileNotFoundError as e:
            print(f"File not found: {image_path}")

# Additional special cards
special_cards = ["Draw 4", "Wild"]
for card in special_cards:
    image_path = os.path.join('Cards', f"{card}.png")
    try:
        CARD_IMAGES[card] = pygame.image.load(image_path)
        print(f"Loaded image: {image_path}")
    except pygame.error as e:
        print(f"Failed to load image: {image_path}, {e}")
    except FileNotFoundError as e:
        print(f"File not found: {image_path}")

# Load Wild cards with colors
wild_colors = ["Blue Wild", "Green Wild", "Red Wild", "Yellow Wild"]
for card in wild_colors:
    image_path = os.path.join('Cards', f"{card}.png")
    try:
        CARD_IMAGES[card] = pygame.image.load(image_path)
        print(f"Loaded image: {image_path}")
    except pygame.error as e:
        print(f"Failed to load image: {image_path}, {e}")
    except FileNotFoundError as e:
        print(f"File not found: {image_path}")

# Load Draw 4 cards with colors
draw4_colors = ["Blue Plus", "Green Plus", "Red Plus", "Yellow Plus"]
for card in draw4_colors:
    image_path = os.path.join('Cards', f"{card}.png")
    try:
        CARD_IMAGES[card] = pygame.image.load(image_path)
        print(f"Loaded image: {image_path}")
    except pygame.error as e:
        print(f"Failed to load image: {image_path}, {e}")
    except FileNotFoundError as e:
        print(f"File not found: {image_path}")

# Client settings
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))

player_id = None
ready = False
connected_players = 0
game_started = False
player_hand = []
discard_pile = None
your_turn = False
choose_color = False

def listen_to_server():
    global connected_players, game_started, player_id, player_hand, discard_pile, your_turn, choose_color
    try:
        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                continue
            if "YOUR TURN" in data:
                your_turn = True
                data = data.replace("YOUR TURN", "")
            if data.startswith("CONNECTED"):
                connected_players = int(data.split()[1])
            elif data.startswith("ASSIGN_ID"):
                player_id = int(data.split()[1])
                print(f"Assigned Player ID: {player_id}")
            elif data.strip() == "START":
                game_started = True
                print("Game is starting! game_started set to True")
            elif data.startswith("STATE"):
                if player_id is not None:
                    parts = data.split(" ")
                    if "Wild" in parts[1] or "Draw 4" in parts[1]:
                        discard_pile = parts[1]
                        offset = 2
                    else:
                        discard_pile = parts[1] + " " + parts[2]
                        offset = 3
                    hands = " ".join(parts[offset:]).split(";")
                    player_hand = hands[player_id].split(",")
                    player_hand = [card.strip() for card in player_hand if card.strip()]
            elif data.startswith("DRAW"):
                card = " ".join(data.split()[1:])
                player_hand.append(card)
            elif data.strip() == "INVALID PLAY":
                your_turn = True
            elif data.strip().startswith("CHOOSE_COLOR"):
                choose_color = True
    except Exception as e:
        print(f"Error in listen_to_server: {e}")

def draw_lobby():
    screen.fill((150, 150, 150))
    font = pygame.font.Font(None, 36)
    connected_text = font.render(f"Connected Players: {connected_players}", True, (255, 255, 255))
    screen.blit(connected_text, (100, 50))
    button_color = (0, 255, 0) if ready else (255, 0, 0)
    button_rect = pygame.Rect(1350, 800, 200, 50)
    pygame.draw.rect(screen, button_color, button_rect)
    ready_text = font.render("I'm Ready", True, (0, 0, 0))
    text_rect = ready_text.get_rect(center=button_rect.center)
    screen.blit(ready_text, text_rect)
    pygame.display.flip()

def draw_game():
    screen.fill((0, 100, 0))
    font = pygame.font.Font(None, 36)
    if discard_pile in CARD_IMAGES:
        screen.blit(CARD_IMAGES[discard_pile], (800, 50))
    else:
        discard_text = font.render(f"Discard Pile: {discard_pile}", True, (255, 255, 255))
        screen.blit(discard_text, (800, 50))
    for i, card in enumerate(player_hand):
        if card in CARD_IMAGES:
            screen.blit(CARD_IMAGES[card], (50 + i * 100, 700))
        else:
            card_text = font.render(card, True, (255, 255, 255))
            screen.blit(card_text, (50 + i * 100, 700))
    if your_turn:
        turn_text = font.render("Your Turn", True, (255, 255, 255))
        screen.blit(turn_text, (800, 150))
    if choose_color:
        color_buttons = ["Red", "Yellow", "Green", "Blue"]
        for i, color in enumerate(color_buttons):
            button_color = pygame.Color(color.lower())
            button_rect = pygame.Rect(800 + i * 100, 150, 100, 50)
            pygame.draw.rect(screen, button_color, button_rect)
            color_text = font.render(color, True, (0, 0, 0))
            text_rect = color_text.get_rect(center=button_rect.center)
            screen.blit(color_text, text_rect)
    draw_button_color = (255, 255, 0)
    draw_button_rect = pygame.Rect(50, 700, 100, 50)
    pygame.draw.rect(screen, draw_button_color, draw_button_rect)
    draw_button_text = font.render("Draw", True, (0, 0, 0))
    draw_button_text_rect = draw_button_text.get_rect(center=draw_button_rect.center)
    screen.blit(draw_button_text, draw_button_text_rect)
    pygame.display.flip()

threading.Thread(target=listen_to_server).start()

running = True
try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if not game_started:
                    if 1350 <= x <= 1550 and 800 <= y <= 850:
                        if not ready:
                            client_socket.sendall("READY".encode())
                            ready = True
                elif choose_color:
                    if 800 <= x <= 1200 and 150 <= y <= 200:
                        color_index = (x - 800) // 100
                        chosen_color = ["Red", "Yellow", "Green", "Blue"][color_index]
                        client_socket.sendall(f"CHOOSE_COLOR {chosen_color}".encode())
                        choose_color = False
                        your_turn = False
                elif your_turn:
                    for i, card in enumerate(player_hand):
                        if 50 + i * 100 <= x <= 150 + i * 100 and 700 <= y <= 800:
                            client_socket.sendall(f"PLAY {card}".encode())
                            if "Draw 4" in card or "Wild" in card:
                                choose_color = True
                            your_turn = False
                            break
                    if 50 <= x <= 150 and 700 <= y <= 750:
                        client_socket.sendall("DRAW".encode())
                        your_turn = False
        if game_started:
            draw_game()
        else:
            draw_lobby()
except KeyboardInterrupt:
    print("Shutting down client...")
finally:
    client_socket.close()
    print("Client closed.")