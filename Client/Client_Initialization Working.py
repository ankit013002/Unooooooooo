import pygame
import socket
import threading
import subprocess  # Add this import to start UNO.py

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((1600, 900))
pygame.display.set_caption("Client")

# Client settings
SERVER_HOST = '127.0.0.1' # When running on the same machine
SERVER_PORT = 65432 # Port to connect to

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))

player_id = None
ready = False
connected_players = 0
game_started = False

def listen_to_server():
    global connected_players, game_started
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data.startswith("CONNECTED"):
                connected_players = int(data.split()[1])
            elif data == "START":
                game_started = True
                print("Game is starting!")
                subprocess.Popen(["python", "UNO.py"])  # Start UNO.py
                break
    except:
        pass

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


threading.Thread(target=listen_to_server).start()

running = True
try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not game_started:
                    x, y = event.pos
                    if 1350 <= x <= 1550 and 800 <= y <= 850:
                        if not ready:
                            client_socket.sendall("READY".encode())
                            ready = True
        if game_started:
            print("Game started!")
        else:
            draw_lobby()
except KeyboardInterrupt:
    print("Shutting down client...")
finally:
    pygame.quit()
    client_socket.close()
    print("Client closed.")
