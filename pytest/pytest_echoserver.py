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

async def handle_echo(reader, writer):
    data = await reader.read(100)
    msg = data.decode()
    if not msg or msg == "EXIT":
        loop.stop()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (msg, addr))
    print("Send: %r" % msg)
    writer.write(data)
    await writer.drain()
    count = findfile_num(os.getcwd(), 'echo_message_')
    f = open('echo_message_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("address: %s:%s" % (str(addr[0]),str(addr[1])))
    f.write('\n')
    f.write("data: %s" % msg)
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
