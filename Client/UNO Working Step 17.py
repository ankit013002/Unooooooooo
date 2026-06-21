import pygame
import socket
import threading
import os

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((1920, 1080))  # Windowed mode
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

# Load and scale Uno Back image
try:
    uno_back_image = pygame.image.load(os.path.join('Cards', 'Uno Back.png'))
    uno_back_image = pygame.transform.scale(uno_back_image, (100, 150))  # Scale the image to desired size
    CARD_IMAGES["Uno Back"] = uno_back_image
    print("Loaded and scaled image: Cards/Uno Back.png")
except pygame.error as e:
    print(f"Failed to load image: Cards/Uno Back.png, {e}")
except FileNotFoundError as e:
    print(f"File not found: Cards/Uno Back.png")

# Load arrow images
left_arrow_image = pygame.image.load(os.path.join('Additional_Assets', 'Left Arrow.png'))
right_arrow_image = pygame.image.load(os.path.join('Additional_Assets', 'Right Arrow.png'))

left_arrow_image = pygame.transform.scale(left_arrow_image, (80, 80))  # Resize to fit better
right_arrow_image = pygame.transform.scale(right_arrow_image, (80, 80))  # Resize to fit better

lobby_image = pygame.image.load(os.path.join('Additional_Assets', 'Us.jpg'))

lobby_background_image = pygame.image.load(os.path.join('Additional_Assets', 'UNO Refined Lobby.png'))

lobby_background_image = pygame.transform.scale(lobby_background_image, (1920, 1080))

game_background_image = pygame.image.load(os.path.join('Additional_Assets', 'UNO Refined Game.png'))
game_background_image = pygame.transform.scale(game_background_image, (1920, 1080))

credits_background_image = pygame.image.load(os.path.join('Additional_Assets', 'Us.jpg'))

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
opponent_hands = [[] for _ in range(4)]  # To track opponent hands
discard_pile = None
your_turn = False
choose_color = False
show_credits = False

scroll_offset = 0  # Initialize scroll offset
max_scroll_offset = 0  # Maximum scroll offset

def listen_to_server():
    global connected_players, game_started, player_id, player_hand, discard_pile, your_turn, choose_color, opponent_hands
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
                    opponent_hands = [hands[i].split(",") for i in range(len(hands)) if i != player_id]
                    for i in range(len(opponent_hands)):
                        opponent_hands[i] = [card.strip() for card in opponent_hands[i] if card.strip()]
            elif data.startswith("DRAW2"):
                parts = data.split()  # Split the string into a list of substrings
                if len(parts) >= 5:  # Ensure there are enough elements
                    piece1 = " ".join(parts[1:3])  # Join the second and third elements
                    player_hand.append(piece1)  # Add the joined string to the player's hand
                    piece2 = " ".join(parts[3:5])  # Join the fourth and fifth elements
                    player_hand.append(piece2)  # Add the joined string to the player's hand

            elif data.startswith("DRAW4"):
                parts = data.split()  # Split the string into a list of substrings
                if len(parts) >= 9:  # Ensure there are enough elements
                    piece1 = " ".join(parts[1:3])  # Join the second and third elements
                    player_hand.append(piece1)  # Add the joined string to the player's hand
                    piece2 = " ".join (parts[3:5])  # Join the fourth and fifth elements
                    player_hand.append(piece2)  # Add the joined string to the player's hand
                    piece3 = " ".join(parts[5:7])  # Join the sixth and seventh elements
                    player_hand.append(piece3)  # Add the joined string to the player's hand
                    piece4 = " ".join(parts[7:9])  # Join the eighth and ninth elements
                    player_hand.append(piece4)  # Add the joined string to the player's hand
                
            elif data.startswith("DRAW"):
                card = " ".join(data.split()[1:])
                player_hand.append(card)
                your_turn = True
            elif data.strip() == "INVALID PLAY":
                your_turn = True
            elif data.strip().startswith("CHOOSE_COLOR"):
                choose_color = True
    except Exception as e:
        print(f"Error in listen_to_server: {e}")

def draw_lobby():
    screen.blit(lobby_background_image, (0, 0))
    font = pygame.font.Font(None, 36)
    connected_text = font.render(f"Connected Players: {connected_players}", True, (255, 255, 255))
    screen.blit(connected_text, (100, 50))
    button_color = (0, 255, 0) if ready else (255, 0, 0)
    button_rect = pygame.Rect(1350, 800, 200, 50)
    pygame.draw.rect(screen, button_color, button_rect)
    ready_text = font.render("I'm Ready", True, (0, 0, 0))
    text_rect = ready_text.get_rect(center=button_rect.center)
    screen.blit(ready_text, text_rect)
    
    # Credits button
    credits_button_rect = pygame.Rect(50, 950, 200, 50)
    pygame.draw.rect(screen, (255, 255, 0), credits_button_rect)
    credits_text = font.render("Credits", True, (0, 0, 0))
    credits_text_rect = credits_text.get_rect(center=credits_button_rect.center)
    screen.blit(credits_text, credits_text_rect)
    
    # Calculate the position to center the lobby image
    # lobby_x = (screen.get_width() - lobby_image.get_width()) // 2
    # lobby_y = (screen.get_height() - lobby_image.get_height()) // 2
    
    # Draw the lobby image at the calculated position
    # screen.blit(lobby_image, (lobby_x, lobby_y))
    
    pygame.display.flip()

def draw_credits():
    screen.blit(game_background_image, (0, 0))
    
    # Calculate the position to center the image on the left half of the screen
    image_x = (screen.get_width() // 2 - credits_background_image.get_width()) // 2
    image_y = (screen.get_height() - credits_background_image.get_height()) // 2
    screen.blit(credits_background_image, (image_x, image_y))  # Show the image on the left half
    
    font = pygame.font.Font(None, 36)
    credits_text = """This game was developed by:
    
    - Ankit Patel
    
    Special thanks to:
    
    - Kisu Patel
    
    """
    
    # Define UNO-themed colors
    uno_colors = [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255)]  # Red, Yellow, Green, Blue
    
    # Calculate the starting y position to center the text vertically
    text_lines = credits_text.split('\n')
    total_text_height = len(text_lines) * 40  # 40 is the line height
    start_y = (screen.get_height() - total_text_height) // 2
    
    y_offset = start_y
    color_index = 0
    for line in text_lines:
        x_offset = 2 * (screen.get_width() // 3) - 80  # Start on the left side of the right half
        words = line.split(' ')
        for word in words:
            text_color = uno_colors[color_index % len(uno_colors)]  # Cycle through UNO colors for each word
            text_surface = font.render(word, True, text_color)
            screen.blit(text_surface, (x_offset, y_offset))
            x_offset += text_surface.get_width() + font.size(' ')[0]  # Add the width of a space
            color_index += 1
        y_offset += 40  # Increase y_offset by the line height
    
    # Paragraph thanking girlfriend
    thank_you_text = "A special thanks to my girlfriend for being my inspiration and support throughout this project. Your love and encouragement have been invaluable."
    thank_you_lines = thank_you_text.split(' ')
    paragraph_x_offset = screen.get_width() // 2
    paragraph_y_offset = screen.get_height() - 200  # Adjust this value to position the paragraph as desired
    color_index = 0
    for word in thank_you_lines:
        text_color = uno_colors[color_index % len(uno_colors)]
        text_surface = font.render(word, True, text_color)
        screen.blit(text_surface, (paragraph_x_offset, paragraph_y_offset))
        paragraph_x_offset += text_surface.get_width() + font.size(' ')[0]
        if paragraph_x_offset > screen.get_width() - 200:  # Adjust wrapping point
            paragraph_x_offset = screen.get_width() // 2
            paragraph_y_offset += 40
        color_index += 1

    # Back button
    back_button_rect = pygame.Rect(1720, 10, 180, 50)
    pygame.draw.rect(screen, (255, 0, 0), back_button_rect)
    back_text = font.render("Back", True, (0, 0, 0))
    back_text_rect = back_text.get_rect(center=back_button_rect.center)
    screen.blit(back_text, back_text_rect)
    
    pygame.display.flip()

discard_pile_x = 0
discard_pile_y = 0
draw_pile_x = 0
draw_pile_y = 0
max_visible_cards = 0
left_arrow_rect = None
right_arrow_rect = None

def draw_game():
    global discard_pile_x, discard_pile_y, draw_pile_x, draw_pile_y, scroll_offset, max_scroll_offset, max_visible_cards, left_arrow_rect, right_arrow_rect
    screen.blit(game_background_image, (0, 0))
    font = pygame.font.Font(None, 36)
    circle_font = pygame.font.Font(None, 48)  # Font for the card count numbers

    # Center the discard pile
    if discard_pile in CARD_IMAGES:
        discard_pile_x = screen.get_width() // 2 - CARD_IMAGES[discard_pile].get_width() // 2
        discard_pile_y = screen.get_height() // 2 - CARD_IMAGES[discard_pile].get_height() // 2
        screen.blit(CARD_IMAGES[discard_pile], (discard_pile_x, discard_pile_y))
    else:
        discard_text = font.render(f"Discard Pile: {discard_pile}", True, (255, 255, 255))
        discard_pile_x = screen.get_width() // 2 - discard_text.get_width() // 2
        discard_pile_y = screen.get_height() // 2 - discard_text.get_height() // 2
        screen.blit(discard_text, (discard_pile_x, discard_pile_y))
    
    # Draw the stack of cards image to the left of the discard pile
    if "Uno Back" in CARD_IMAGES:
        draw_pile_x = discard_pile_x - CARD_IMAGES["Uno Back"].get_width() - 20
        draw_pile_y = discard_pile_y
        screen.blit(CARD_IMAGES["Uno Back"], (draw_pile_x, draw_pile_y))
    
    # Draw opponent hands and circles with numbers
    for idx in range(connected_players - 1):
        hand_length = len(opponent_hands[idx])
        for i in range(hand_length):
            screen.blit(CARD_IMAGES["Uno Back"], (50 + i * 100, 50 + idx * 50))
        pygame.draw.circle(screen, (255, 255, 255), (25, 75 + idx * 50), 25)
        count_text = circle_font.render(str(hand_length), True, (0, 0, 0))
        count_rect = count_text.get_rect(center=(25, 75 + idx * 50))
        screen.blit(count_text, count_rect)

    # Draw player's hand and circle with number
    card_width = 100  # Width of each card
    max_visible_cards = (screen.get_width() - 200) // card_width  # Calculate maximum visible cards
    total_cards = len(player_hand)
    max_scroll_offset = max(0, total_cards - max_visible_cards)

    start_index = scroll_offset
    end_index = min(total_cards, start_index + max_visible_cards)

    for i in range(start_index, end_index):
        card = player_hand[i]
        if card in CARD_IMAGES:
            screen.blit(CARD_IMAGES[card], (100 + (i - start_index) * 100, 700))
        else:
            card_text = font.render(card, True, (255, 255, 255))
            screen.blit(card_text, (100 + (i - start_index) * 100, 700))

    pygame.draw.circle(screen, (255, 255, 255), (25, 725), 25)
    count_text = circle_font.render(str(len(player_hand)), True, (0, 0, 0))
    count_rect = count_text.get_rect(center=(25, 725))
    screen.blit(count_text, count_rect)

    if your_turn:
        turn_text = font.render("Your Turn", True, (255, 255, 255))
        screen.blit(turn_text, (50, 400))
    if choose_color:
        color_buttons = ["Red", "Yellow", "Green", "Blue"]
        for i, color in enumerate(color_buttons):
            button_color = pygame.Color(color.lower())
            button_rect = pygame.Rect(800 + i * 100, 150, 100, 50)
            pygame.draw.rect(screen, button_color, button_rect)
            color_text = font.render(color, True, (0, 0, 0))
            text_rect = color_text.get_rect(center=button_rect.center)
            screen.blit(color_text, text_rect)

    # Draw arrow buttons
    left_arrow_rect = left_arrow_image.get_rect(topleft=(10, 600))
    right_arrow_rect = right_arrow_image.get_rect(topright=(screen.get_width() - 90, 600))

    screen.blit(left_arrow_image, left_arrow_rect.topleft)
    screen.blit(right_arrow_image, right_arrow_rect.topleft)

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
                print(f"Mouse clicked at ({x}, {y})")
                if show_credits:
                    if 1720 <= x <= 1900 and 10 <= y <= 60:
                        show_credits = False
                elif not game_started:
                    if 1350 <= x <= 1550 and 800 <= y <= 850:
                        if not ready:
                            client_socket.sendall("READY".encode())
                            ready = True
                    elif 50 <= x <= 250 and 950 <= y <= 1000:
                        show_credits = True
                elif choose_color:
                    if 800 <= x <= 1200 and 150 <= y <= 200:
                        color_index = (x - 800) // 100
                        chosen_color = ["Red", "Yellow", "Green", "Blue"][color_index]
                        client_socket.sendall(f"CHOOSE_COLOR {chosen_color}".encode())
                        choose_color = False
                        your_turn = False
                elif left_arrow_rect.collidepoint(x, y):
                    print("Left arrow clicked")
                    scroll_offset = max(0, scroll_offset - 1)
                    print(f"Scroll offset set to: {scroll_offset}")
                elif right_arrow_rect.collidepoint(x, y):
                    print("Right arrow clicked")
                    scroll_offset = min(max_scroll_offset, scroll_offset + 1)
                    print(f"Scroll offset set to: {scroll_offset}")
                elif your_turn:
                    for i, card in enumerate(player_hand):
                        if 100 + (i - scroll_offset) * 100 <= x <= 200 + (i - scroll_offset) * 100 and 700 <= y <= 800:
                            client_socket.sendall(f"PLAY {card}".encode())
                            if "Draw 4" in card or "Wild" in card:
                                choose_color = True
                            your_turn = False
                            break
                    # Check if the user clicked on the draw card stack
                    if discard_pile_x - CARD_IMAGES["Uno Back"].get_width() - 20 <= x <= discard_pile_x - 20  and discard_pile_y <= y <= discard_pile_y + CARD_IMAGES["Uno Back"].get_height():
                        print("User clicked on the draw card stack.")
                        client_socket.sendall("DRAW".encode())
                        your_turn = False
                
        if show_credits:
            draw_credits()
        elif game_started:
            draw_game()
        else:
            draw_lobby()
except KeyboardInterrupt:
    print("Shutting down client...")
finally:
    client_socket.close()
    print("Client closed.")
