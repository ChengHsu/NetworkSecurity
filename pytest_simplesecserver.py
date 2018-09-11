import asyncio
import time
import sys
import logging
from simplecrypt import encrypt, decrypt
import os

from Crypto.Cipher import XOR
import base64


def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1




def encrypt(key, plaintext):
  cipher = XOR.new(key)
  return base64.b64encode(cipher.encrypt(plaintext))

def decrypt(key, ciphertext):
  cipher = XOR.new(key)
  return cipher.decrypt(base64.b64decode(ciphertext))


async def handle_echo(reader, writer):
    ciphertxt = ''
    plaintxt = ''

    for i in range(2):
        data = await reader.read(1024)
        cmd = data.decode()
        if not cmd or cmd == "EXIT":
            loop.stop()
        strs = cmd.split(',')
        if strs[0] == 'encrypt':
            ciphertxt = encrypt('notsosecretkey',strs[1])
            ciphertxt = ciphertxt.decode('utf-8')
            # ciphertxt = encrypt(strs[1], 'password')
            writer.write(('cipher,%s' % ciphertxt).encode('utf-8'))
            await writer.drain()
        elif strs[0] == 'decrypt':
            plaintxt = decrypt('notsosecretkey',strs[1])
            plaintxt = plaintxt.decode('utf-8')
            writer.write(('plain,%s' % plaintxt).encode('utf-8'))
            await writer.drain()

    count = findfile_num(os.getcwd(), 'security_message_')
    f = open('security_message_%s.txt' % count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("P: %s" % plaintxt)
    f.write('\n')
    f.write("C: %s" % ciphertxt)
    f.close()
    print('Close the client socket')
    writer.close()


# 1.Start: get event loop
loop = asyncio.get_event_loop()
# 2.Start a socket server, with a callback for each client connected
coro = asyncio.start_server(handle_echo, '127.0.0.1', int(sys.argv[1]), loop=loop)
server = loop.run_until_complete(coro)
# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
