import aiohttp
import asyncio
import sys
import os
import time

# python3 pytest_simplewebclient.py 8888 'test.txt'

def findfile_num(start, name):
    c = 0
    for relpath, dirs, files in os.walk(start):
        for file in files:
            if file.startswith(name):
                c += 1
    return c + 1

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    async with aiohttp.ClientSession() as session:
        port = sys.argv[1]
        file_path = sys.argv[2]
        url = 'http://127.0.0.1:%s/%s' % (port,file_path)
        path = await fetch(session, url)
        print(path)
        count = findfile_num(os.getcwd(), 'web_response_')
        f = open('web_response_%s.txt' % count, 'w')
        f.write('timestamp: %s' % str(time.time()))
        f.write('\n')
        f.write("requested file path: %s" % path)
        f.write('\n')
        # f.write("response code: %s" % code)
        f.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())