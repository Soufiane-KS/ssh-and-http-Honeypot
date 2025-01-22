import logging
from logging.handlers import RotatingFileHandler
import socket
import paramiko
import paramiko.transport

logging_format = logging.Formatter('%(message)s')
SSH_BANNER = "SSH-2.0-MySSHServer_1.0"
host_key = 'server.key'


funnel_logger = logging.getLogger("FunnelLogger")
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler('audits.log',maxBytes=2000,backupCount=5) 
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)


creds_logger = logging.getLogger("CredsLogger")
creds_logger.setLevel(logging.INFO)
creds_handler = RotatingFileHandler('cmd_audits.log',maxBytes=2000,backupCount=5) 
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(creds_handler)


def emulated_shell(channel, client):
    channel.send(b'corporate-jumpbox$ ')
    command = b""
    while True:
        char = channel.recv(1)
        channel.send(char)
        if not char:
            channel.close()

        command += char

        if char == b'\r':
            if command.strip() == b'exit':
                response = b'\n Goodbye!\n'
                channel.close()
            elif command.strip() == b'pwd':
                response = b'\n' + b'\\usr\\local' + b'\r\n'
            elif command.strip() == b'whoami':
                response = b'\n' + b'Soufiane' + b'\r\n'
            elif command.strip() == b'ls':
                response = b'\n' + b'jumpbox1.conf' + b'\r\n'
            elif command.strip() == b'cat jumpbox1.conf':
                response = b'\n' +b'Go to testWebsite.com' + b'\r\n'
            else:
                response = b'\n' + bytes(command.strip()) +b'\r\n'

        channel.send(response)
        channel.send(b'corporate-jumpbox$ ')
        command=b''




class Server(paramiko.ServerInterface):

    def __init__(self,client_ip, input_username=None, input_password=None):
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password
    
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED

    def get_allowed_auths(self):
        return "password"

    def check_auth_password(self, username, password):
        if self.input_username is not None and self.input_password is not None:    
            if username == 'username' and password == 'password':
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
    
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
    def check_channel_exec_request(self, channel, command):
        command = str(command)

def client_handel(client, addr, username, password):
    client_ip = addr[0]
    print(f"{client_ip} has connected to the server.")

    try:
        transport = paramiko.Transport()
        transport.local_version = SSH_BANNER
        server = Server(client_ip=client_ip, input_username=username, input_password=password)

        transport.add_server_key(host_key)

        transport.start_server(server=server)

        channel = transport.accept(100)
        if channel == None:
            print('no channel was opened. ')

        standard_banner = "Welcome to Ubuntu 22.04 LTS (Jammy Jellyfish)!\r\n\r\n"
        channel.send(standard_banner)
        emulated_shell(channel,client_ip=client_ip)
    except Exception as error:
        print(error)
        print("!!! Something went wrong !!!")
    finally:
        try:
            transport.close()
        except Exception as error:
            print(error)
            print("something went wrong in the second try block")
        client.close()