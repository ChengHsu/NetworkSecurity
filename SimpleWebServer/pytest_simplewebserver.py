from aiohttp import web
import os
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

# python3 pytest_simplewebserver.py 888'127.0.0.1'
async def handle(request):
    filename = request.match_info.get('filename', "Anonymous")
    # path = os.path.abspath(os.path.join(os.getcwd(), "../.."))
    path = os.getcwd()
    print(path)
    text = ''
    code = 0
    for root, dirs, files in os.walk(path):
        if request.match_info['filename'] in files:
            text = os.path.join(root, filename)
            print('Find the file.')
            code = 200
        else:
            code = 404
            text = 'File does not exist.'
    count = findfile_num(os.getcwd(), 'web_message_')
    f = open('web_message_%s.txt'%count, 'w')
    f.write('timestamp: %s' % str(time.time()))
    f.write('\n')
    f.write("requested file: %s" % text )
    f.write('\n')
    f.write("response code: %s" % code )
    f.close()
    return web.Response(status=code, text=text)

app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{filename}', handle)])
host = sys.argv[2]
port = sys.argv[1]
web.run_app(app,host=host,port=port)