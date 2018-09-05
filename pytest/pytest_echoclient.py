import socket
import sys
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostname()
port = int(sys.argv[1])
s.connect((host, port))

print(s.recv(1024).decode('utf-8'))
i = 0
while True:
    i = i + 1
    inp = input('>>> Send: ')
    if inp == 'EXIT':
        break
    s.send(bytes(inp,'utf8'))
    try:
        data = s.recv(1024)
    except ConnectionRefusedError:
        print('Server shut down')
        break
    print(str(data,'utf8'))

    f = open('/Users/xucheng/Desktop/NetworkSecurity/pytest/echo_response_%s' % i, 'w')
    f.write('Timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write(host + ':' + str(port))
    f.write('\n')
    f.write(str(data))
    f.close()

s.close()

