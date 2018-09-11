import asyncio
import time
import sys
import logging
import functools
import os


def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1


async def handle_echo(reader, writer):
    global balance
    data = await reader.read(1024)
    cmd = data.decode()
    if not cmd or cmd == "EXIT":
        loop.stop()
    if cmd == "balance":
        print("Send: %s" % balance)
        writer.write(str(balance).encode())
        await writer.drain()
    if "deposit" in cmd:
        balance += int(cmd.split(' ')[1])
        writer.write('OK'.encode())
        await writer.drain()
    if "withdraw" in cmd:
        if int(cmd.split(' ')[1]) >= balance:
            balance = 0
            writer.write((cmd.split(' ')[1]).encode())
        else:
            balance -= int(cmd.split(' ')[1])
            writer.write((cmd.split(' ')[1]).encode())
        await writer.drain()
    print(str(balance))
    count = findfile_num(os.getcwd(), 'bank_message_')
    f = open('bank_message_%s.txt' % count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("command: %s" % cmd)
    f.write('\n')
    f.write("balance: %s" % balance)
    f.close()
    print('Close the client socket')
    writer.close()


global balance
balance = 0
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
