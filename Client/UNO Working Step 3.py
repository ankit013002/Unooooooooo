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
values = [str(i) for i in range(10)] + ["Skip", "Reverse", "Draw Two"]

for color in colors:
    for value in values:
        image_path = os.path.join('Cards', f"{color}- {value}.png")
        try:
            CARD_IMAGES[f"{color} {value}"] = pygame.image.load(image_path)
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

def listen_to_server():
    global connected_players, game_started, player_id, player_hand, discard_pile, your_turn
    try:
        while True:
            data = client_socket.recv(1024).decode()
            print(f"Received data: {data}")
            if "YOUR TURN" in data:
                your_turn = True
                data = data.replace("YOUR TURN", "")
            if data.startswith("CONNECTED"):
                connected_players = int(data.split()[1])
                print(f"Connected Players: {connected_players}")
            elif data.startswith("ASSIGN_ID"):
                player_id = int(data.split()[1])
                print(f"Assigned Player ID: {player_id}")
            elif data.strip() == "START":
                game_started = True
                print("Game is starting! game_started set to True")
            elif data.startswith("STATE"):
                if player_id is not None:
                    parts = data.split(" ")
                    discard_pile = parts[1] + " " + parts[2]
                    hands = " ".join(parts[3:]).split(";")
                    player_hand = hands[player_id].split(",")
                    player_hand = [card.strip() for card in player_hand if card.strip()]
                    print(f"Parsed player hand: {player_hand}")
                    print(f"Parsed discard pile: {discard_pile}")
                else:
                    print("Error: player_id is None, ignoring state message")
            elif data.startswith("DRAW"):
                card = data.split()[1] + " " + data.split()[2]
                player_hand.append(card)
                print(f"Drew card: {card}")
            elif data.strip() == "INVALID PLAY":
                print("Invalid play, try again.")
    except Exception as e:
        print(f"Error in listen_to_server: {e}")

def draw_lobby():
    screen.fill((150, 150, 150))  # Fill the screen with a light gray color
    font = pygame.font.Font(None, 36)

    # Render connected players text
    connected_text = font.render(f"Connected Players: {connected_players}", True, (255, 255, 255))
    screen.blit(connected_text, (100, 50))

    # Define button properties
    button_color = (0, 255, 0) if ready else (255, 0, 0)
    button_rect = pygame.Rect(1350, 800, 200, 50)  # x, y, width, height

    # Draw the button rectangle
    pygame.draw.rect(screen, button_color, button_rect)

    # Render the "I'm Ready" text
    ready_text = font.render("I'm Ready", True, (0, 0, 0))  # Black text
    text_rect = ready_text.get_rect(center=button_rect.center)

    # Blit the text onto the button
    screen.blit(ready_text, text_rect)

    # Update the display
    pygame.display.flip()

def draw_game():
    screen.fill((0, 100, 0))  # Fill the screen with a green color

    font = pygame.font.Font(None, 36)

    # Render the discard pile
    if discard_pile in CARD_IMAGES:
        screen.blit(CARD_IMAGES[discard_pile], (800, 50))
    else:
        discard_text = font.render(f"Discard Pile: {discard_pile}", True, (255, 255, 255))
        screen.blit(discard_text, (800, 50))

    # Render the player's hand
    for i, card in enumerate(player_hand):
        if card in CARD_IMAGES:
            screen.blit(CARD_IMAGES[card], (50 + i * 100, 700))
        else:
            print(f"Card image not found: {card}")

    # Render "Your Turn" text if it's the player's turn
    if your_turn:
        turn_text = font.render("Your Turn", True, (255, 255, 255))
        screen.blit(turn_text, (800, 150))

    # Draw a "Draw Card" button
    draw_button_color = (255, 255, 0)
    draw_button_rect = pygame.Rect(50, 700, 100, 50)
    pygame.draw.rect(screen, draw_button_color, draw_button_rect)
    draw_button_text = font.render("Draw", True, (0, 0, 0))
    draw_button_text_rect = draw_button_text.get_rect(center=draw_button_rect.center)
    screen.blit(draw_button_text, draw_button_text_rect)

    # Update the display
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
                    print(f"Mouse click at ({x}, {y}), game not started")
                    if 1350 <= x <= 1550 and 800 <= y <= 850:
                        if not ready:
                            client_socket.sendall("READY".encode())
                            ready = True
                            print("Sent READY to server")
                elif your_turn:
                    print(f"Mouse click at ({x}, {y}), it's your turn")
                    # Check if a card was clicked
                    for i, card in enumerate(player_hand):
                        if 50 + i * 100 <= x <= 150 + i * 100 and 700 <= y <= 800:
                            print(f"Playing card: {card}")
                            client_socket.sendall(f"PLAY {card}".encode())
                            your_turn = False
                            break
                    # Check if the "Draw Card" button was clicked
                    if 50 <= x <= 150 and 700 <= y <= 750:
                        print("Drawing a card")
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
