import asyncio
import time
import sys
import os

def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1


async def tcp_echo_client(plaintxt, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1',int(sys.argv[1]),loop=loop)

    print('Send encrpt,%s' % plaintxt)
    cmd1 = 'encrypt,%s' % plaintxt
    writer.write(cmd1.encode())
    data1 = await reader.read(1024)
    if not data1 or data1.decode() == "EXIT":
        loop.stop()
    response1 = data1.decode('utf-8')
    print('Received: %r' % response1)

    ciphertxt = response1.split(',')[1]
    print('Send decrpt,%s' % ciphertxt)
    cmd2 = 'decrypt,%s' % ciphertxt
    writer.write(cmd2.encode('utf-8'))
    data2 = await reader.read(1024)
    if not data2 or data2.decode() == "EXIT":
        loop.stop()
    response2 = data2.decode()
    print('Received: %r' % response2)
    count = findfile_num(os.getcwd(), 'security_response_')
    f = open('security_response_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write('P: %s' % plaintxt)
    f.write('\n')
    f.write('C: %s' % ciphertxt)
    f.close()
    print('Close the socket')
    writer.close()


loop = asyncio.get_event_loop()
plaintxt = sys.argv[2]
loop.run_until_complete(tcp_echo_client(plaintxt, loop))
loop.close()


