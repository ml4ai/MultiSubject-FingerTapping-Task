# Multi-Subject Finger Tapping

## Install dependencies

Require Python >= 3.6. Ensure that both the server and client computers have the required packages

```python
pip3 install -r requirements.txt
```

## Server

Run the server script.

```python
python3 server.py <host> <port>
```

where `<host>` is IPv4 address of the server, and `<port>` is port reserved for server.

Available server commands:

- `h` or `help`: List of server commands
- `unpause`: Unpause the game
- `restart`: Restart the game
- `exit`: Close the game on server and clients

DANGER: Do not interrupt the game from the terminal.

## User Clients

Use the host IPv4 address and port specified by the server to start the client.

```python
python3 client.py <host> <port> <name>
```

where `<host>` is IPv4 address of the server, `<port>` is port used by the server, and `<name>` is the name of the client.

Available client commands:

- `h` or `help`: List of server commands
- `exit`: Close the game

DANGER: Do not interrupt the game from the terminal.
