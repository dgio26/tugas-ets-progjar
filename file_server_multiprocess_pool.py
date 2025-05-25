from socket import *
import socket
import logging
import time
import sys
from concurrent.futures import ProcessPoolExecutor

from file_protocol import FileProtocol

def init_worker():
    global fp
    fp = FileProtocol()

def handle_client(connection, client_address):
    buffer = ""
    try:
        while True:
            data = connection.recv(1024 * 1024)
            if not data:
                break
            buffer += data.decode()
            while "\r\n\r\n" in buffer:
                command_str, buffer = buffer.split("\r\n\r\n", 1)
                logging.warning(f"[{client_address}] Received: {command_str[:50]}...")
                hasil = fp.proses_string(command_str)
                response = hasil + "\r\n\r\n"
                connection.sendall(response.encode())
    except Exception as e:
        logging.error(f"Error handling client {client_address}: {e}")
    finally:
        connection.close()
        logging.warning(f"Connection closed for {client_address}")

class Server:
    def __init__(self, ipaddress="0.0.0.0", port=7778, pool_size=5):
        self.ipinfo = (ipaddress, port)
        self.pool_size = pool_size
        self.process_pool = ProcessPoolExecutor(
            max_workers=pool_size,
            initializer=init_worker
        )
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def start(self):
        logging.warning(f"ProcessPool server running at {self.ipinfo} with pool size {self.pool_size}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(100)

        try:
            while self.running:
                try:
                    connection, client_address = self.my_socket.accept()
                    logging.warning(f"Connection from {client_address}")
                    self.process_pool.submit(handle_client, connection, client_address)
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            logging.warning("KeyboardInterrupt received, shutting down server...")
        finally:
            self.shutdown()

    def shutdown(self):
        self.running = False
        self.process_pool.shutdown(wait=True)
        self.my_socket.close()
        logging.warning("Server has been shut down.")

def main():
    pool_size = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
    server = Server(ipaddress="0.0.0.0", port=7778, pool_size=pool_size)
    server.start()

if __name__ == "__main__":
    main()
