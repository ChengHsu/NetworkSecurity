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


async def tcp_echo_client(problem, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', int(sys.argv[1]), loop=loop)
    print('Send: %s' % problem)
    writer.write(problem.encode())
    data = await reader.read(1024)
    if not data or data.decode() == "EXIT":
        loop.stop()
    response = data.decode()
    print('Received: %r' % response)
    count = findfile_num(os.getcwd(), 'calc_response_')
    f = open('calc_response_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write('response: %s' % response)
    f.close()
    print('Close the socket')
    writer.close()


loop = asyncio.get_event_loop()
problem = sys.argv[2]
loop.run_until_complete(tcp_echo_client(problem, loop))
loop.close()
