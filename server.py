import socket
from select import select
from utils import send
import pygame
import sys
import json
import threading
import config as cfg


class Server:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

        self._to_client_connections = []
        self._from_client_connections = {}

        # Establish connection where clients can get game state update
        self._to_client_request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._to_client_request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse socket
        self._to_client_request.bind((self._host, self._port))
        self._to_client_request.setblocking(False)

        # Establish connection where clients send control commands
        self._from_client_request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_client_request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse socket
        self._from_client_request.bind((self._host, self._port + 1))
        self._from_client_request.setblocking(False)

        self._exit_request = False
        self._currentID = 0

        self._state = {}

        self._current_session_index = -1
        self._paused = True
        self._counter = 0.0
        self._counter_target = cfg.SECONDS_COUNT_DOWN

        self._thread_lock = threading.Lock()

        print(f"[NETWORK] ({self._host}, {self._port})")

    def run(self):
        """
        Set up threads for handling connections
        """
        to_client_request_thread = threading.Thread(target=self._dispatch_to_client_request, daemon=True)
        to_client_request_thread.start()

        from_client_request_thread = threading.Thread(target=self._dispatch_from_client_request, daemon=True)
        from_client_request_thread.start()

        from_client_commands_thread = threading.Thread(target=self._from_client_commands, daemon=True)
        from_client_commands_thread.start()

        to_client_update_state_thread = threading.Thread(target=self._to_client_update_state, daemon=True)
        to_client_update_state_thread.start()

        server_control_thread = threading.Thread(target=self._server_control, daemon=True)
        server_control_thread.start()

        # Wait for threads to finish
        to_client_request_thread.join()
        from_client_request_thread.join()
        from_client_commands_thread.join()
        to_client_update_state_thread.join()
        server_control_thread.join()
        
        # Close server connection
        self._to_client_request.close()
        self._from_client_request.close()

    def _dispatch_to_client_request(self):
        """
        Dispatch client's connection for receiving game state updates from server
        """
        # Listen for client connection
        self._to_client_request.listen()

        while not self._exit_request:
            readable, _, _ = select([self._to_client_request], [], [self._to_client_request], 0.1)
            if readable:
                client_conn, client_addr = readable[0].accept()
                client_conn.setblocking(False)
                self._to_client_connections.append(client_conn)
                print("Sending replies to [" + client_addr[0] + ", " + str(client_addr[1]) + ']')

    def _dispatch_from_client_request(self):
        """
        Establish connection to receive clients' command
        """
        # Listen for client connection
        self._from_client_request.listen()

        while not self._exit_request:
            readable, _, _ = select([self._from_client_request], [], [self._from_client_request], 0.1)

            if readable:
                client_conn, client_addr = readable[0].accept()
                client_conn.setblocking(False)

                _, writable, _ = select([], [client_conn], [client_conn])
                try:
                    send(writable[0], self._currentID)
                except BrokenPipeError:
                    print("Connection closed")
                    continue

                self._thread_lock.acquire()
                self._from_client_connections[client_conn] = self._currentID
                self._state[self._currentID] = 0
                self._thread_lock.release()

                print("Receiving commands from [" + str(self._currentID) + ", " + client_addr[0] + ", " + str(client_addr[1]) + ']')

                self._currentID += 1
    
    def _to_client_update_state(self):
        """
        Update game state then send game state updates to clients
        """
        start_ticks = pygame.time.get_ticks()

        clock = pygame.time.Clock()
        while not self._exit_request:
            if self._paused:
                data = {}
                data["message_type"] = "state"
                data["state"] = self._state
                data["session_index"] = self._current_session_index
                data["timer"] = int(self._counter_target - self._counter + 1.0)

                _, writable, exceptional = select([], self._to_client_connections, self._to_client_connections, 0)
                for connection in writable:
                    try:
                        send(connection, data)
                    except:
                        print("Connection closed")
                        connection.close()
                        self._to_client_connections.remove(connection)
                
                for connection in exceptional:
                    connection.close()
                    self._to_client_connections.remove(connection)

                start_ticks = pygame.time.get_ticks()
                clock.tick(10)
                continue

            seconds = (pygame.time.get_ticks() - start_ticks)/1000.0

            if self._counter > self._counter_target:
                self._current_session_index += 1

                if self._current_session_index >= len(cfg.SESSION):
                    self._exit_request = True
                    break

                self._counter_target = cfg.SECONDS_PER_SESSION[self._current_session_index]
                self._counter = 0.0
                start_ticks = pygame.time.get_ticks()

            elif seconds >= self._counter:
                self._counter += 1.0

            data = {}
            data["message_type"] = "state"
            data["state"] = self._state
            data["session_index"] = self._current_session_index
            data["timer"] = int(self._counter_target - self._counter + 1.0)

            _, writable, exceptional = select([], self._to_client_connections, self._to_client_connections, 0)
            for connection in writable:
                try:
                    send(connection, data)
                except:
                    print("Connection closed")
                    connection.close()
                    self._to_client_connections.remove(connection)
            
            for connection in exceptional:
                connection.close()
                self._to_client_connections.remove(connection)
            
            clock.tick(144)

        while self._to_client_connections:
            _, writable, exceptional = select([], self._to_client_connections, self._to_client_connections)

            for connection in writable:
                data = {}
                data["message_type"] = "command"
                data["message"] = "CLOSE"

                try:
                    send(connection, data)
                except BrokenPipeError:
                    print("Connection closed")

                connection.close()
                self._to_client_connections.remove(connection)
            
            for connection in exceptional:
                connection.close()
                self._to_client_connections.remove(connection)
            
            clock.tick(144)

    def _from_client_commands(self):
        """
        Handle clients' commands
        """
        while not self._exit_request:
            readable, _, exceptional = select(self._from_client_connections.keys(), [], self._from_client_connections.keys(), 0.2)

            for id in self._state.keys():
                self._state[id] = 0

            for connection in readable:
                client_id = self._from_client_connections[connection]

                message = connection.recv(128)

                if not message:
                    continue

                try:
                    command = json.loads(message.decode('utf-8'))
                except json.decoder.JSONDecodeError as err:
                    print(err)
                    continue

                if command == "TAP":
                    self._state[client_id] = 1
                elif command == "CLOSE":
                    connection.close()
                    self._thread_lock.acquire()
                    del self._from_client_connections[connection]
                    del self._state[client_id]
                    self._thread_lock.release()

            for connection in exceptional:
                connection.close()
                self._thread_lock.acquire()
                del self._from_client_connections[connection]
                del self._state[client_id]
                self._thread_lock.release()

        for connection in self._from_client_connections:
            connection.close()

    def _server_control(self):
        """
        Control the server 
        """
        while not self._exit_request:
            readable, _, _ = select([sys.stdin], [], [], 0.5)

            if not readable:
                continue

            command = readable[0].readline().strip()

            if command == "h" or command == "help":
                print("-----")
                print("unpause: Unpause the game")
                print("restart: Restart the game")
                print("exit: Close the server")
                print("h or help: List available commands")
                print("-----")

            elif command == "unpause":
                self._paused = False

            elif command == "restart":
                self._paused = True
                self._counter = 0.0
                self._counter_target = cfg.SECONDS_COUNT_DOWN
                self._current_session_index = -1

            elif command == "exit":
                self._exit_request = True

            else:
                print("Unknown command")


if __name__ == "__main__":
    pygame.init()

    assert len(sys.argv) >= 2

    host = sys.argv[1]
    port = 6060 if len(sys.argv) < 3 else int(sys.argv[2])

    server = Server(host, port)
    server.run()
