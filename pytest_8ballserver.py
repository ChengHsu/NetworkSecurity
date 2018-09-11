import asyncio
import time
import sys
import random
import os

answers = ("Your guess is as good as mine.", "You need a vacation.", "It's Trump's fault!",
           "I don't know. What do you think?",
           "Nobody ever said it would be easy, they only said it would be worth it.",
           "You really expect me to answer that?", "You're going to get what you deserve.",
           "That depends on how much you're willing to pay.")

def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1

async def handle_echo(reader, writer):
    global dict
    data = await reader.read(1024)
    question = data.decode()
    if not question or question == "EXIT":
        loop.stop()
    addr = writer.get_extra_info('peername')

    print("Received %r from %r" % (question, addr))
    if question in dict:
        ans = dict.get(question)
    else:
        ans = random.choice(answers)
        dict[question] = ans
    print("Send: %r" % ans)
    writer.write(ans.encode())
    await writer.drain()
    count = findfile_num(os.getcwd(), '8ball_message_')
    f = open('8ball_message_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("question: %s" % question)
    f.write('\n')
    f.write("Data: %s" % ans)
    f.close()

    print('Close the client socket')
    writer.close()


# 1.Start: get event loop
loop = asyncio.get_event_loop()

global dict
dict = {}
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
