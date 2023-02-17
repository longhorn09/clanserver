from gevent.server import StreamServer

import xml.etree.ElementTree as ET
import socket
import xmltodict
import urllib3
import gevent
import gevent.queue
import sys
import string
#ret = urllib2.urlopen('https://enabledns.com/ip')
IP = ""#ret.read()
print(IP)
current_arctic_chars = {}

class ArcticMessage():
    def __init__(self, cmd, payload):
        self.cmd = cmd
        self.payload = payload

    def __str__(self):
        return "<msg><cmd>%s</cmd><payload>%s</payload></msg>\r\n" % (self.cmd, self.payload)

# Reads from a socket and writes it into a queue
#Writer Greenlet - this requires a queue.
class ArcticChar(gevent.Greenlet):
    def __init__(self, client_socket, address):
        super(ArcticChar, self).__init__()
        self.client_socket = client_socket
        self.address = address
        self.charData = None
        self.queue = gevent.queue.Queue()
        self.running = False
    
    def update(self, payload):
        self.charData = dict(xmltodict.parse(ET.tostring(payload.find('chardata')))['chardata'])
        print(self.charData)

    def send(self, message):
        if self.running == False:
            raise "Not running anymore, must remove client"
        print("Enqueuing message: %s for %s" % (message, self.charData))
        self.queue.put(message)
        return True

    def _run(self):
        self.running = True
        while self.running:
            msg = self.queue.get()    # block call
            print("Sending message: %s for %s" % (msg, self.charData))
            self.client_socket.sendall(str(msg))
        self.running = False

    def __str__(self): 
        return "address:" + str(self.address) + ",charData:" + str(self.charData)

class ArcticCommand(object):
    def __init__(self, command, tag):
        self.command = command
        self.tag = tag

    def execute(self, payload, current_arctic_chars):
        print("Do nothing")

class ArcticSingleTargetCommand(ArcticCommand):
    def __init__(self, command, tag):
        super(ArcticSingleTargetCommand, self).__init__(command, tag)

    def execute(self, payload, arctic_chars):
        target = payload.find('target')
        if target != None and target.text in arctic_chars:
            print("targeting %s" % target.text)
            message = string.replace(payload.find(self.tag).text, '***', ';')
            arctic_chars[target.text].send(
                ArcticMessage(self.command,message))
        else:
            print("No such character found: %s", target)

class ArcticAllTargetsCommand(ArcticCommand):
    def __init__(self, command, tag):
        super(ArcticAllTargetsCommand, self).__init__(command, tag)

    def execute(self, payload, arctic_chars, exclude=None):
        message = ""
        if self.tag != None:
            message = payload.find(self.tag).text
        else:
            message = payload.text
        message = string.replace(message, '***', ';')
        for arctic_char in arctic_chars.values():
            arctic_char.send(
                ArcticMessage(self.command, message))

commands = {
    "NOOP" : ArcticCommand("NOOP","message"),
    "NOTIFY" : ArcticSingleTargetCommand("NOTIFY", "message"),
    "NOTIFYALL" : ArcticAllTargetsCommand("NOTIFY", "message"),
    "COMMAND" : ArcticSingleTargetCommand("EXECUTE", "execute"),
    "COMMANDALL" : ArcticAllTargetsCommand("EXECUTE", None),
}

def parse_message(client_message):
    try:
        tree = ET.fromstring(client_message)
        cmd = tree.find('cmd').text
        payload = None
        try:
            payload = tree.find('payload')
        except:
            print( "No payload found")
        print("COMMAND: %s Payload: %s "% (cmd, ET.tostring(payload)))
        return cmd, payload
    except (IOError, e):
        print( "Unexpected error:", sys.exc_info()[0])
        return "NOOP", None

# this handler will be run for each incoming connection in a dedicated greenlet
# this will spawn a Writer Greenlet that will listen on a particular queue
def handle_new_client(socket, address):
    global current_arctic_chars
    print('New connection from %s', address)
    arcticChar = ArcticChar(socket, address)

    socket.sendall(str(ArcticMessage("NOTIFY", "Welcome to normstorm.com(" +
        IP + ")")))
    socket.sendall(str(ArcticMessage("NOTIFY", "Current Chars connected are(" +
         ",".join(current_arctic_chars.keys()) + ")")))
    socket.sendall(str(ArcticMessage("EXECUTE", "score")))
    rfileobj = socket.makefile(mode='rb')
    try:
        while True:
            line = rfileobj.readline()
            if not line:
                print("client disconnected")
                break
            print("received %r" % line)
            (cmd, payload) = parse_message(line)
            if cmd == "CHARDATA":
                arcticChar.update(payload)
                # destroy the previous char
                if arcticChar.charData['@name'] in current_arctic_chars:
                    previousArcticChar = current_arctic_chars[arcticChar.charData['@name']]
                    if previousArcticChar != arcticChar:
                        previousArcticChar.kill()
                        previousArcticChar.join()
                current_arctic_chars[arcticChar.charData['@name']] = arcticChar
                #socket.sendall(str(ArcticMessage("NOTIFY", "Received CharData: " + str(arcticChar.charData))))
                print("FOUND CHARDATA for %s" % arcticChar.charData['@name'])
                arcticChar.start()
            else:
                temp_current_arctic_chars = current_arctic_chars.copy()
                if cmd != "NOTIFYALL" and cmd != "NOTIFY" and arcticChar.charData != None:
                    del temp_current_arctic_chars[arcticChar.charData['@name']]
                commands[cmd].execute(payload, temp_current_arctic_chars)
    finally:
        rfileobj.close()
        print("CLOSING CONNECTION FOR %s" % str(arcticChar))
        if arcticChar.charData != None and '@name' in arcticChar.charData:
            del current_arctic_chars[arcticChar.charData['@name']]
            arcticChar.kill()
            arcticChar.join()

if __name__ == '__main__':
    # to make the server use SSL, pass certfile and keyfile arguments to the constructor
    server = StreamServer(('0.0.0.0', 3000), handle_new_client)
    # to start the server asynchronously, use its start() method;
    # we use blocking serve_forever() here because we have no other jobs
    print('Starting server on port 3000')
    server.serve_forever()
