import socket
import sys
import threading
import time


def tcplink(sock,addr):
    print('Accept new connection from %s:%s' % addr)
    sock.send(b'Welcome!')
    i = 0
    while True:
        i = i + 1
        data = sock.recv(1024)
        time.sleep(1)
        if not data or data.decode('utf8') == 'EXIT':
            break

        f = open('/Users/xucheng/Desktop/NetworkSecurity/pytest/echo_message_%s' % i,'w')
        f.write('Timestamp: %s' % str(time.time()))
        f.write('\n')
        f.write(str(addr))
        f.write('\n')
        f.write(str(data))
        f.close()
        sock.send(b'Received msg.')


    sock.close()
    print('Connection from %s:%s closed.' % addr)



# Create a socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Set host name and port
host = socket.gethostname()
port = int(sys.argv[1])


# Bind Address
s.bind((host, port))

# Listen to the port
s.listen(5)
print('Waiting for connection...\n')

while True:
    # Accept a new connection
    csock, addr = s.accept()
    print('Received connection from {}'.format(addr))
    # create a new thread to handle new connection
    # Every connection should be handled by a new thread or the single thread cannot accept other connections
    t = threading.Thread(target = tcplink, args = (csock,addr))
    t.start()