import asyncio
import sys
import time
import os

def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1

async def tcp_echo_client(msg, loop):

    reader, writer = await asyncio.open_connection('127.0.0.1',int(sys.argv[1]),loop=loop)
    print('Send: %r' % msg)
    writer.write(msg.encode())
    data = await reader.read(100)
    if not data or data.decode() == "EXIT":
        loop.stop()
    print('Received: %r' % data.decode())
    count = findfile_num(os.getcwd(),'echo_response_')
    f = open('echo_response_%s.txt'%count, 'w')

    f.write('Timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write('Echoed data: %s' % data.decode())
    f.close()
    print('Close the socket')
    writer.close()
global count
count = 0
loop = asyncio.get_event_loop()
loop.run_until_complete(tcp_echo_client(sys.argv[2], loop))
loop.close()