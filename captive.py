import socket
import network
import time
import machine
import neopixel

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="NeoPixel WIFI!", authmode=1)

np = neopixel.NeoPixel(machine.Pin(4), 1) #one neopixel on port 4
np[0] = (255, 1, 1) #init value
np.write()

print('starting')

CONTENT = b"""\
HTTP/1.0 200 OK

<!DOCTYPE html>
<html>
    <head>
        <title>MicroPython Captive LED Portal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta charset="utf8">
    </head>
    <body>
        <h1>Change the NeoPixel Color</h1>
        <br />
            <form action="/led">
            <input type="number" name="red" min="0" max="255"> Red <br>
            <input type="number" name="green" min="0" max="255"> Green <br>
            <input type="number" name="blue" min="0" max="255"> Blue <br>
            <input type="submit" value="change">
        </form>
        <script>
        </script>
    </body>
</html>
"""

class DNSQuery:
  def __init__(self, data):
    self.data=data
    self.dominio=''

    print("Reading datagram data...")
    m = data[2] # ord(data[2])
    tipo = (m >> 3) & 15   # Opcode bits
    if tipo == 0:                     # Standard query
      ini=12
      lon=data[ini] # ord(data[ini])
      while lon != 0:
        self.dominio+=data[ini+1:ini+lon+1].decode("utf-8") +'.'
        ini+=lon+1
        lon=data[ini] #ord(data[ini])

  def respuesta(self, ip):
    packet=b''
    print("Resposta {} == {}".format(self.dominio, ip))
    if self.dominio:
      packet+=self.data[:2] + b"\x81\x80"
      packet+=self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'   # Questions and Answers Counts
      packet+=self.data[12:]                                         # Original Domain Name Question
      packet+= b'\xc0\x0c'                                             # Pointer to domain name
      packet+= b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
      packet+=bytes(map(int,ip.split('.'))) # 4 bytes of IP
    return packet

def start():

    # DNS Server
    ip=ap.ifconfig()[0]
    print('DNS Server: dom.query. 60 IN A {:s}'.format(ip))

    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.setblocking(False)
    udps.bind(('',53))

    # Web Server
    s = socket.socket()
    ai = socket.getaddrinfo(ip, 80)
    print("Web Server: Bind address info:", ai)
    addr = ai[0][-1]

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    s.settimeout(2)
    print("Web Server: Listening http://{}:80/".format(ip))

    try:
        while 1:

            # DNS Loop
            print("Before DNS...")
            try:
                data, addr = udps.recvfrom(1024)
                print("incomming datagram...")
                p=DNSQuery(data)
                udps.sendto(p.respuesta(ip), addr)
                print('Replying: {:s} -> {:s}'.format(p.dominio, ip))
            except:
                print("No dgram")

            # Web loop
            print("before accept...")
            try:
                res = s.accept()
                client_sock = res[0]
                client_addr = res[1]
                #print("Client address:", client_addr)
                #print("Client socket:", client_sock)

                client_stream = client_sock

                print("Request:")
                req = client_stream.readline()
                print(req)
                while True:
                    h = client_stream.readline()
                    if h == b"" or h == b"\r\n" or h == None:
                        break
                    print(h)


                request_url = req[4:-11]
                api = request_url[:5]
                print(api)
                d = {}
                if api == b'/led?':
                    params = request_url[5:]
                    print(params)


                    try:
                        d = {key: value for (key, value) in [x.split(b'=') for x in params.split(b'&')]}
                    except:
                        d = {}

                    if b'red' in d.keys(): #check if color present
                        print('CHANGING COLOR')
                        r = int(d[b'red'])
                        g = int(d[b'green'])
                        b = int(d[b'blue'])
                        np[0] = (r, g, b)
                        np.write()
                        time.sleep_ms(1000)

                client_stream.write(CONTENT)
                client_stream.close()

            except:
                print("timeout for web... moving on...")
            print("loop")
            time.sleep_ms(100)
    except KeyboardInterrupt:
        print('Closing')
    udps.close()
