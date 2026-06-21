import socket
import threading
import random

# Server settings
HOST = '127.0.0.1'
PORT = 65432

# Global variables
clients = []
player_ready = [False] * 4  # To track which players are ready
server_socket = None

# UNO game variables
colors = ["Red", "Yellow", "Green", "Blue"]
values = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Skip", "Reverse", "Draw"]
# Create a larger deck by multiplying the initial deck by 3
deck = ([f"{color} {value}" for color in colors for value in values] * 3)  # Each card appears three times
deck += ["Draw 4"] * 12  # Add the Draw 4 cards to the deck
deck += ["Wild"] * 12  # Add the Wild cards to the deck
discard_pile = []
player_hands = [[] for _ in range(4)]
current_turn = 0
direction = 1  # 1 for clockwise, -1 for counterclockwise

def handle_client(conn, addr, player_id):
    global player_ready
    print(f"Player {player_id + 1} connected from {addr}")
    conn.sendall(f"ASSIGN_ID {player_id}\n".encode())  # Send the assigned player ID to the client
    try:
        while True:
            print(f"Waiting for data from player {player_id + 1}...")
            data = conn.recv(1024).decode()
            print(f"Received data from player {player_id + 1}: {data}")
            if not data:
                break
            if data == "READY":
                player_ready[player_id] = True
                print(f"Player {player_id + 1} is ready.")
                if all(player_ready[:len(clients)]):
                    start_game()
            else:
                handle_game_action(player_id, data)
    except Exception as e:
        print(f"Error in handle_client: {e}")
    finally:
        conn.close()
        print(f"Player {player_id + 1} disconnected.")
        player_ready[player_id] = False
        clients.remove(conn)
        notify_clients()

def handle_game_action(player_id, action):
    global current_turn, direction
    if action.startswith("PLAY"):
        parts = action.split(maxsplit=1)
        if len(parts) < 2:
            send_message_to_player(player_id, "INVALID PLAY\n")
            return
        card = parts[1].strip()
        print(f"Player {player_id + 1} played: {card}")
        if "Wild" in card or "Draw 4" in card:
            print(f"Player {player_id + 1} played a special card: {card}")
            if is_valid_play(player_hands[player_id], card):
                player_hands[player_id].remove(card)
                discard_pile.append(card)
                send_message_to_player(player_id, "CHOOSE_COLOR\n")
                if "Draw 4" in card:
                    next_player_id = (current_turn + direction) % len(clients)
                    draw_four(next_player_id)
                    current_turn = (current_turn + direction) % len(clients)
                current_turn = (current_turn + direction) % len(clients)
                return  # Wait for color choice before notifying the next player
            else:
                send_message_to_player(player_id, "INVALID PLAY\n")
        else:
            if is_valid_play(player_hands[player_id], card):
                player_hands[player_id].remove(card)
                discard_pile.append(card)
                if "Reverse" in card:
                    direction *= -1
                    current_turn = (current_turn + direction) % len(clients)
                elif "Skip" in card:
                    current_turn = (current_turn + direction) % len(clients)
                    current_turn = (current_turn + direction) % len(clients)
                elif "Draw" in card:
                    next_player_id = (current_turn + direction) % len(clients)
                    draw_two(next_player_id)
                    current_turn = (current_turn + direction) % len(clients)
                    current_turn = (current_turn + direction) % len(clients)
                else:
                    current_turn = (current_turn + direction) % len(clients)
                broadcast_game_state()
                notify_next_player()
            else:
                send_message_to_player(player_id, "INVALID PLAY\n")
    elif action == "DRAW":
        print(f"Player {player_id + 1} drew a card.")
        draw_card(player_id)
        notify_next_player()  # Notify the next player after drawing a card
    elif action.startswith("CHOOSE_COLOR"):
        parts = action.split()
        if len(parts) < 2:
            send_message_to_player(player_id, "INVALID COLOR CHOICE\n")
            return
        new_color = parts[1]
        if not discard_pile:
            send_message_to_player(player_id, "INVALID COLOR CHOICE\n")
            return
        top_card = discard_pile.pop()
        if "Wild" in top_card:
            new_card = f"{new_color} Wild"
        elif "Draw 4" in top_card:
            new_card = f"{new_color} Plus"
        else:
            new_card = f"{new_color} {top_card.split()[1]}"
        discard_pile.append(new_card)
        broadcast_game_state()
        notify_next_player()
    print(f"Current turn: {current_turn}")
    print("\n--------------------------------------------\n")

def draw_two(player_id):
    card = deck.pop()
    player_hands[player_id].append(card)
    card_two = deck.pop()
    player_hands[player_id].append(card_two)
    send_message_to_player(player_id, f"DRAW2 {card}; {card_two}\n")
    
    broadcast_game_state()

def draw_four(player_id):
    card = deck.pop()
    player_hands[player_id].append(card)
    card_two = deck.pop()
    player_hands[player_id].append(card_two)
    card_three = deck.pop()
    player_hands[player_id].append(card_three)
    card_four = deck.pop()
    player_hands[player_id].append(card_four)
    send_message_to_player(player_id, f"DRAW4 {card} {card_two} {card_three} {card_four}\n")
    
    broadcast_game_state()

def is_valid_play(player_hand, card):
    if "Wild" in card or "Draw 4" in card:
        return True  # Always a valid play for Wild and Draw 4
    last_discard = discard_pile[-1]  # Get the last card in the discard pile
    discard_color, discard_value = last_discard.split(maxsplit=1)  # Split the color and value
    card_color, card_value = card.split(maxsplit=1)  # Split the color and value of the card being played
    return discard_color == card_color or discard_value == card_value  # Check if the color or value matches

def draw_card(player_id):
    if deck:
        card = deck.pop()
        player_hands[player_id].append(card)
        send_message_to_player(player_id, f"DRAW {card}\n")
        broadcast_game_state()


def start_game():
    print("All players ready. Starting the game...")
    random.shuffle(deck)
    for i in range(7):  # Deal 7 cards to each player
        for player_hand in player_hands:
            player_hand.append(deck.pop())
    discard_pile.append(deck.pop())  # Start the discard pile with one card
    broadcast_game_state()
    for conn in clients:
        conn.sendall("START\n".encode())  # Send the START message to all clients
    notify_next_player()

def notify_next_player():
    next_player_id = current_turn
    print(f"Notifying player {next_player_id + 1} that it's their turn.")
    send_message_to_player(next_player_id, "YOUR TURN\n")

def send_message_to_player(player_id, message):
    clients[player_id].sendall(message.encode())

def broadcast_game_state():
    game_state = f"STATE {discard_pile[-1]} " + " ; ".join([",".join(hand) for hand in player_hands])
    for conn in clients:
        conn.sendall(f"{game_state}\n".encode())

def notify_clients():
    connected_str = f"CONNECTED {len(clients)}\n"
    for conn in clients:
        conn.sendall(connected_str.encode())

def accept_connections():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server listening on {HOST}:{PORT}")
    player_id = 0

    try:
        while player_id < 4:
            conn, addr = server_socket.accept()
            clients.append(conn)
            threading.Thread(target=handle_client, args=(conn, addr, player_id)).start()
            player_id += 1
            notify_clients()
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        for conn in clients:
            conn.close()
        server_socket.close()
        print("Server closed.")

if __name__ == "__main__":
    accept_connections()
