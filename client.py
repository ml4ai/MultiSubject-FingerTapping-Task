import socket
from select import select
import threading
import pygame
import sys
from utils import send
from utils import Subject
import json
import config as cfg

WINDOW_SIZE = (400, 800)


class Client:
    def __init__(self, host: str, port: int, client_name: str):
        self._client_name = client_name

        # Establish two-channel connection to server
        self._from_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_server.connect((host, port))
        self._from_server.setblocking(False)

        self._to_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._to_server.connect((host, port + 1))
        self._to_server.setblocking(False)

        _, writable, _ = select([], [self._to_server], [self._to_server])
        try:
            send(writable[0], self._client_name)
        except BrokenPipeError:
            raise RuntimeError("Fail to establish connection with server")

        self._running = True

        self._tapped = False

        print("Connected to server, client ID: " + self._client_name)

    def run(self):
        # Create a thread for sending client input to server
        control_thread = threading.Thread(target=self._send_input, daemon=True)
        control_thread.start()

        # Create a thread for controlling client from terminal
        client_control_thread = threading.Thread(target=self._client_control, daemon=True)
        client_control_thread.start()

        # Set up game window
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Multi-Subject Finger Tapping Task")

        while self._running:
            # Exit the game if user hits close
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

                    # Notify server that client closes the connection
                    _, writable, _ = select([], [self._to_server], [self._to_server])
                    if writable:
                        send(writable[0], "CLOSE")
                    else:
                        raise RuntimeError("Lost connection with server")

            if not self._running:
                break

            # Get update from server about the state of the game
            readable, _, _ = select([self._from_server], [], [self._from_server])
            if readable:
                message = readable[0].recv(cfg.HEADER)

                if not message:
                    continue

                try:
                    data = json.loads(message.decode('utf-8'))
                except json.decoder.JSONDecodeError as err:
                    print(err)
                    continue

                # Exit game when server is closed
                if data["message_type"] == "command":
                    if data["message"] == "CLOSE":
                        self._running = False
                        print("Server closed")
                        break
            else:
                self._running = False
                print("Server closed")
                break

            # Add sprites to sprite group
            counter = 1
            all_sprites_list = pygame.sprite.Group()
            for name, state in data["state"].items():
                # Always show client as pink
                if name == self._client_name:
                    color = (255, 0, 255) if state else (100, 0, 100)
                    subject = Subject((100, 100), color)
                    all_sprites_list.add(subject)
                # Show other players if the count down is happening or during synchronization period
                elif int(data["session_index"]) < 0 or cfg.SESSION[int(data["session_index"])] > 0:
                    color = (255, 255, 255) if state else (100, 100, 100)
                    subject = Subject((100, 100 + counter * 220), color)
                    all_sprites_list.add(subject)
                    counter += 1

            # Draw background
            screen.fill((0, 0, 0))

            # Draw sprite group
            all_sprites_list.draw(screen)

            # Display timer
            font = pygame.font.Font(None, 74)
            text = font.render(str(data["timer"]), 1, (255, 255, 255))
            screen.blit(text, (10, 10))

            # Update client screen
            pygame.display.flip()
        
        # Close receiving connection
        self._from_server.close()

        # Close pygame window
        pygame.quit()

        # Wait for threads to finish
        control_thread.join()
        client_control_thread.join()

    def _send_input(self):
        """
        Send user's input command to server
        """
        clock = pygame.time.Clock() # Control the rate of sending data to server
        while self._running:
            # Get keys pressed by user
            keys = pygame.key.get_pressed()

            # Send control commands to server
            if keys[pygame.K_SPACE] and not self._tapped:
                self._tapped = True
                _, writable, _ = select([], [self._to_server], [self._to_server])
                if writable:
                    try:
                        send(writable[0], "TAP")
                    except BrokenPipeError:
                        print("Server closed")
                        self._running = False
            elif not keys[pygame.K_SPACE]:
                self._tapped = False

            clock.tick(60)
        
        # Close sending connection
        self._to_server.close()

    def _client_control(self):
        """
        Control client
        """
        while self._running:
            readable, _, _ = select([sys.stdin], [], [], 0.5)

            if not readable:
                continue

            command = readable[0].readline().strip()
            
            if command == "h" or command == "help":
                print("-----")
                print("exit: Close the game")
                print("h or help: List available commands")
                print("-----")
            elif command == "exit":
                self._running = False
                _, writable, _ = select([], [self._to_server], [self._to_server], 1.0)
                if writable:
                    try:
                        send(writable[0], "CLOSE")
                    except BrokenPipeError:
                        print("Server closed")
            else:
                print("Unknown command")


if __name__ == "__main__":
    pygame.init()

    assert len(sys.argv) >= 3

    host = sys.argv[1]
    port = int(sys.argv[2])
    client_name = sys.argv[3]

    client = Client(host, port, client_name)
    client.run()
