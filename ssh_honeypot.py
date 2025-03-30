import logging
from logging.handlers import RotatingFileHandler
import socket
import threading
import paramiko

logging_format = logging.Formatter('%(message)s')
SSH_BANNER = "SSH-2.0-MySSHServer_1.0"

host_key = paramiko.RSAKey.from_private_key_file('server.key')

# Logging configuration
funnel_logger = logging.getLogger("FunnelLogger")
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler('audits.log', maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

creds_logger = logging.getLogger("CredsLogger")
creds_logger.setLevel(logging.INFO)
creds_handler = RotatingFileHandler('cmd_audits.log', maxBytes=2000, backupCount=5)
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(creds_handler)


def emulated_shell(channel, client):
    channel.send(b'corporate-jumpbox$ ')
    command = b""

    while True:
        try:
            char = channel.recv(1)
            if not char:
                break  # Exit loop if connection is closed
            
            channel.send(char)
            command += char

            if char == b'\r':  # Enter key pressed
                channel.send(b'\n')

                if command.strip() == b'exit':
                    channel.send(b'Goodbye!\n')
                    break  # Exit loop to close connection

                responses = {
                    b'pwd': b'\\usr\\local',
                    b'whoami': b'Soufiane',
                    b'ls': b'jumpbox1.conf',
                    b'cat jumpbox1.conf': b'Go to testWebsite.com'
                }

                response = responses.get(command.strip(), command.strip())
                channel.send(response + b'\r\n')
                channel.send(b'corporate-jumpbox$ ')
                command = b''  # Reset command buffer
        except Exception as e:
            print(f"Error in shell: {e}")
            break

    channel.close()


class Server(paramiko.ServerInterface):
    def __init__(self, client_ip, input_username=None, input_password=None):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        if self.input_username and self.input_password:
            return paramiko.AUTH_SUCCESSFUL if username == self.input_username and password == self.input_password else paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True


def client_handle(client, addr, username, password):
    client_ip = addr[0]
    print(f"{client_ip} has connected to the server.")

    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        server = Server(client_ip=client_ip, input_username=username, input_password=password)
        transport.add_server_key(host_key)

        transport.start_server(server=server)

        channel = transport.accept()
        if channel is None:
            print("No channel was opened.")
            return

        banner = "Welcome to Ubuntu 22.04 LTS (Jammy Jellyfish)!\r\n\r\n"
        channel.send(banner.encode())
        emulated_shell(channel, client_ip)
    except Exception as error:
        print(f"Error: {error}")
    finally:
        transport.close()
        client.close()


def honeypot(address, port, username, password):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((address, port))
    sock.listen(100)

    print(f"SSH honeypot is listening on {address}:{port}")

    while True:
        try:
            client, addr = sock.accept()
            ssh_thread = threading.Thread(target=client_handle, args=(client, addr, username, password))
            ssh_thread.start()
        except Exception as error:
            print(f"Error in honeypot: {error}")


honeypot('127.0.0.1', 2233, 'username', 'password')
