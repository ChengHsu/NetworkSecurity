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


def calculate(num1, num2, op):
    if op == '+':
        res = float(num1) + float(num2)
    if op == '-':
        res = float(num1) - float(num2)
    if op == '*':
        res = float(num1) * float(num2)
    else:
        if num2 == '0.0' or num2 == '0':
            return 'ERROR'
            res = float(num1) / float(num2)
    return str(res)


def process_expr(strs):
    stack = []
    ops = ['+', '-', '*', '/']
    length = len(strs)
    if length == 1:
        res = strs[0]
    elif length == 2:
        res = calculate('0', strs[1], strs[0])
    else:
        for i in range(length - 1, -1, -1):
            if strs[i] not in ops:
                stack.append(strs[i])
            if strs[i] in ops:
                num1 = stack.pop()
                num2 = stack.pop()
                res = calculate(num1, num2, strs[i])
                if res == "ERROR":
                    return res
                stack.append(res)
        res = stack[0]
    return str(res)


async def handle_echo(reader, writer):
    data = await reader.read(1024)
    problem = data.decode()
    if not problem or problem == "EXIT":
        loop.stop()
    strs = problem.split(' ')
    res = process_expr(strs)
    writer.write(res.encode())
    await writer.drain()
    count = findfile_num(os.getcwd(), 'calc_message_')
    f = open('calc_message_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("problem: %s" % problem)
    f.write('\n')
    f.write("result: %s" % res)
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
