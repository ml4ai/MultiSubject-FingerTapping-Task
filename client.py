import socket
from select import select
import threading
import pygame
import sys
import os

os.environ["SDL_VIDEO_CENTERED"] = "1"

pygame.init()
SCREENWIDTH = 1200
SCREENHEIGHT = 1200
SCREENSIZE = [SCREENWIDTH, SCREENHEIGHT]
SCREEN = pygame.display.set_mode(SCREENSIZE)

pygame.display.set_caption("Finger tapping-Client")

nickname = input("Choose your nickname: ")

RADIUS = 200
ZEROINTENSITY = 0
MAXINTENSITY = 255

COLOR = (0,255,255)
YPOS = 500
XPOS = 300
POS = (XPOS, YPOS)
circlerect = pygame.draw.circle(SCREEN, COLOR, POS, RADIUS) #subject 1

COLOR1 = (0,255,255)
YPOS1 = 500
XPOS1 = 900
POS1 = (XPOS1, YPOS1)
circlerect1 = pygame.draw.circle(SCREEN, COLOR1, POS1, RADIUS) #subject 2

pygame.font.init()
screen = pygame.display.set_mode(SCREENSIZE)
size = 80
font = pygame.font.SysFont("comicsans", size)
textsurface = font.render("Subject 1", False, (100,100,0))
# screen.blit(textsurface,(180,200))
# pygame.display.update()

pygame.font.init()
screen1 = pygame.display.set_mode(SCREENSIZE)
font1 = pygame.font.SysFont("comicsans", size)
textsurface1 = font1.render("Subject 2", False, (100,100,0))
# screen1.blit(textsurface1,(780,200))
# pygame.display.update()

Color_line=(255,255,255)
pygame.draw.line(SCREEN, Color_line, (600, 0), (600, 1200))
pygame.display.update() 

pygame.display.update(circlerect)
pygame.display.update(circlerect1)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      #socket initialization
client.connect(('127.0.0.1', 7978))                             #connecting client to server

def receive():
    while True:    
        screen.blit(textsurface,(180,200)) 
        pygame.display.flip()
        screen1.blit(textsurface1,(780,200))
        pygame.display.flip() #display subject name on screen                                                  #making valid connection
        
        try:
            message = client.recv(1024).decode('ascii')
            if message == 'NICKNAME':
                client.send(nickname.encode('ascii'))
                continue
            else:
                print(message)
                if message == 'T':
                    COLOR = (0,100,100)   
                    pygame.draw.circle(SCREEN, COLOR, POS1, RADIUS)
                    pygame.display.update(circlerect1)
                    print('Recived from:',nickname, message)
                elif message == 'F':
                    COLOR = (0,255,255)   
                    pygame.draw.circle(SCREEN, COLOR, POS1, RADIUS)
                    pygame.display.update(circlerect1)
                    print('Recived from:',nickname, message)
                else:
                    continue
        except:                                                 #case on wrong ip/port details
            print("An error occured!")
            client.close()
            break
def write():
    while True:   
        screen.blit(textsurface,(180,200)) 
        pygame.display.flip()
        screen1.blit(textsurface1,(780,200))
        pygame.display.flip() #display subject name on screen                                              #message layout
        for events in pygame.event.get():
            if events.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            #Here for any commands inside the for loop  
            if events.type == pygame.KEYDOWN:
                if events.key == pygame.K_SPACE:
                    COLOR = (0,100,100)
                    pygame.draw.circle(SCREEN, COLOR, POS, RADIUS)
                    pygame.display.update(circlerect)
                    message = 'T'
                    client.send(message.encode('ascii'))
                    print(message)

            elif events.type == pygame.KEYUP:
                COLOR = (0,255,255)
                pygame.draw.circle(SCREEN, COLOR, POS, RADIUS)
                pygame.display.update(circlerect)   
                message = 'F'   
                client.send(message.encode('ascii'))
                print(message)                                                                                                                                                           
        # message = '{}: {}'.format(nickname, input(''))
        # client.send(message.encode('ascii'))

receive_thread = threading.Thread(target=receive)               #receiving multiple messages
receive_thread.start()
write_thread = threading.Thread(target=write)                   #sending messages 
write_thread.start()


class Client:
    def __init__(self, host: str, port: int):
        self._client_id = -1

        # Establish two-channel connection to server
        self._from_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_server.connect((host, port))
        self._from_server.setblocking(False)

        self._to_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._to_server.connect((host, port + 1))
        self._to_server.setblocking(False)

        readable, _, _ = select([self._to_server], [], [self._to_server])
        if readable:
            self._client_id = int(readable[0].recv(1024).decode('utf-8'))
        else:
            raise RuntimeError("Fail to establish connection with server")

        self._running = True

        print("Connected to server, client ID: " + str(self._client_id))

    def run(self):
        # Create a thread for sending client input to server
        control_thread = threading.Thread(target=self._send_input, daemon=True)
        control_thread.start()

        
