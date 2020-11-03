from socket import *
import json, time, threading
from urllib import request

config = {
    'HOST': '0.0.0.0',
    'PORT': 11011,
    'LISTEN_CLIENT': 50,
    'KEY': '391f10fadc339e9ec5fa15af60030ac1',
    'SIZE': 2048,
    'TIME_OUT': 1000,
    'HEART_TIME': 5,
    'MAGIC_STRING': '258EAFA5-E914-47DA-95CA-C5AB0DC85B11',
    'HANDSHAKE_STRING': "HTTP/1.1 101 Switching Protocols\r\n" \
                        "Upgrade:websocket\r\n" \
                        "Connection: Upgrade\r\n" \
                        "Sec-WebSocket-Accept: {1}\r\n" \
                        "WebSocket-Location: ws://{2}/chat\r\n" \
                        "WebSocket-Protocol:chat\r\n\r\n"
}

def get_robot_reply(input_text):
    data = {
        "reqType":0,
        "perception": {
            "inputText": {
                "text": input_text
            },
        },
        "userInfo": {
            "apiKey": "cc8c863cfa2b42ecb1e6ae9d4f2c5f36",
            "userId": "339745"
        }
    }
    data = json.dumps(data, ensure_ascii=False).encode("utf-8")
    # data = parse.urlencode(data).encode("utf-8")
    # print(data)
    url = request.Request("http://openapi.tuling123.com/openapi/api/v2", data=data, method="POST")
    res = request.urlopen(url).read()

    return json.loads(res.decode("utf-8"))["results"][0]["values"]["text"]
class Server():
    """
    服务端基类
    """

    def __init__(self):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.bind((config['HOST'], config['PORT']))  # 监听端口
        self.sock.listen(config['LISTEN_CLIENT'])  # 监听客户端数量

        # 所有监听的客户端
        self.clients = {}
        self.thrs = {}
        self.users = {}
        self.stops = []

    # 监听客户端连接
    def listen_client(self):
        while 1:
            # 循环监听
            tcpClientSock, addr = self.sock.accept()
            address = addr[0] + ':' + str(addr[1])  # ip:port

            # 握手
            topInfo = tcpClientSock.recv(1024)
            headers = {}
            if not topInfo:
                tcpClientSock.close()
                continue

            header, data = topInfo.decode().split('\r\n\r\n', 1)

            try:
                getInfo = header.split('\r\n')[0].split(' ')[1].split('/')[1:]
                if getInfo[0] == 'name':
                    self.users[address] = str(getInfo[1])
                else:
                    self.users[address] = '匿名用户'
            except:
                self.users[address] = '匿名用户'

            for line in header.split('\r\n')[1:]:
                key, val = line.split(': ', 1)
                headers[key] = val

            if 'Sec-WebSocket-Key' not in headers:
                tcpClientSock.close()
                continue

            import hashlib, base64
            sec_key = headers['Sec-WebSocket-Key']
            res_key = base64.b64encode(hashlib.sha1((sec_key + config['MAGIC_STRING']).encode()).digest())

            str_handshake = config['HANDSHAKE_STRING'].replace('{1}', res_key.decode()).replace('{2}',
                                                                                       config['HOST'] + ':' + str(
                                                                                           config['PORT']))
            tcpClientSock.send(str_handshake.encode())

            # 握手成功 分配线程进行监听
            print(address + '进来了')

            self.clients[address] = tcpClientSock
            self.thrs[address] = threading.Thread(target=self.readMsg, args=[address])
            self.thrs[address].start()
            # print(self.clients)

    def readMsg(self, address):
        # print(self.clients)
        print("我被执行了")
        client = self.clients[address]
        print("我也被执行了")
        i = 0
        while 1:
            #try:
            info = client.recv(2024)
            # except:
            #     self.close_client(address)
            #     break
            if not info:
                continue


            # code_len = ord(info[1]) & 127
            # if code_len == 126:
            #     masks = info[4:8]
            #     data = info[8:]
            # elif code_len == 127:
            #     masks = info[10:14]
            #     data = info[14:]
            # else:
            #     masks = info[2:6]
            #     data = info[6:]
            # i = 0
            # raw_str = ""
            # for d in data:
            #     # print(masks, masks[i % 4])
            #     raw_str += chr(ord(d) ^ ord(masks[i % 4]))
            #     # print(raw_str)
            #     i += 1

            # 获取到输入的数据 向所有的客户端发送
            # 开启线程记录
            code_len = info[1] & 0x7f
            if code_len == 0x7e:
                extend_payload_len = info[2:4]
                mask = info[4:8]
                decoded = info[8:]
            elif code_len == 0x7f:
                extend_payload_len = info[2:10]
                mask = info[10:14]
                decoded = info[14:]
            else:
                extend_payload_len = None
                mask = info[2:6]
                decoded = info[6:]
            bytes_list = bytearray()
            for i in range(len(decoded)):
                chunk = decoded[i] ^ mask[i % 4]
                bytes_list.append(chunk)
            raw_str = bytes_list.decode("utf-8","ignore")
            if raw_str == 'quit':
                print("???????????????????")
                self.close_client(address)

                break
            i+=1
            self.send_data(raw_str, address)

            self.send_data(get_robot_reply(raw_str), address,False)


    def send_data(self, data, address,huif=True):

        import struct
        from urllib.parse import unquote
        try:
            username = unquote(self.users[address])
        except:
            username = '匿名用户'
        if data:
            if huif:
                data = str('【' + username + '说】' + data)
            else:
                data = str('【' + '二狗' + '说】' + data)
        else:
            return False
        token = b'\x81'
        length = len(data.encode())
        if length <= 125:
            token += struct.pack('B', length)
        elif length <= 0xFFFF:
            token += struct.pack('!BH', 126, length)
        else:
            token += struct.pack('!BQ', 127, length)
        data = token + data.encode()
        # try:
        for key, val in self.clients.items():
            client = val
            try:
                client.send(data)
                print("没错")
            except:
                self.close_client(key)
        # except:
        #     print("出错了")
        #     pass

    def close_client(self, address):
        try:
            client = self.clients.pop(address)
            self.stops.append(address)
            client.close()
            del self.users[address]
        except:
            pass

        print(address + u'已经退出')


if __name__ == '__main__':
    c = Server()
    c.listen_client()


