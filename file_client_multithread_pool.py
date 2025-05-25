import socket
import json
import base64
import logging
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

class FileClient:
    def __init__(self, ip, port):
        self.server_address = (ip, port)
        self.timeout = 300

    def send_command(self, command_str=""):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.server_address)
            sock.sendall((command_str + "\r\n\r\n").encode())
            data_received = ""
            while True:
                data = sock.recv(1024 * 1024)
                if data:
                    data_received += data.decode()
                    if "\r\n\r\n" in data_received:
                        break
                else:
                    break
            hasil = json.loads(data_received.split("\r\n\r\n")[0])
            return hasil
        except Exception as e:
            return {"status": "ERROR", "data": str(e)}
        finally:
            sock.close()

    def remote_list(self):
        hasil = self.send_command("LIST")
        if hasil['status'] == 'OK':
            return True, hasil['data']
        return False, hasil.get("data", "Unknown error")

    def remote_get(self, filename=""):
        start = time.time()
        hasil = self.send_command(f"GET {filename}")
        if hasil['status'] == 'OK':
            try:
                namafile = hasil['data_namafile']
                isifile = base64.b64decode(hasil['data_file'])
                with open(namafile, 'wb+') as fp:
                    fp.write(isifile)
                size = os.path.getsize(namafile)
                return True, time.time() - start, size
            except Exception as e:
                logging.error(f"Download failed for {filename}: {e}")
                return False, 0, 0
        else:
            return False, 0, 0

    def remote_upload(self, filepath=""):
        start = time.time()
        if not os.path.exists(filepath):
            return False, 0, 0
        try:
            with open(filepath, 'rb') as fp:
                file_bytes = fp.read()
            file_content = base64.b64encode(file_bytes).decode()
            base_filename = os.path.basename(filepath)
            hasil = self.send_command(f"UPLOAD {base_filename} {file_content}")
            if hasil['status'] == 'OK':
                size = os.path.getsize(filepath)
                return True, time.time() - start, size
            else:
                return False, 0, 0
        except Exception as e:
            logging.error(f"Upload failed for {filepath}: {e}")
            return False, 0, 0

def execute_task(ip, port, operation, filename=None):
    client = FileClient(ip, port)
    if operation == "download":
        return client.remote_get(filename)
    elif operation == "upload":
        return client.remote_upload(filename)
    elif operation == "list":
        status, _ = client.remote_list()
        return status, 0, 0
    else:
        return False, 0, 0

def run_stress_test(ip, port, operation, filename, num_workers):
    tasks = [(operation, filename) for _ in range(num_workers)]
    
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(execute_task, ip, port, op, fname) for op, fname in tasks]
        for future in as_completed(futures):
            results.append(future.result())

    duration = time.time() - start_time
    success_count = sum(1 for r in results if r[0])
    failure_count = num_workers - success_count

    total_bytes = sum(r[2] for r in results if r[0]) if operation in ["download", "upload"] else 0
    throughput = total_bytes / duration if duration > 0 else 0

    return {
        "operation": operation,
        "file_size": os.path.getsize(filename) if filename and os.path.exists(filename) else 0,
        "total_workers": num_workers,
        "total_time": duration,
        "throughput": throughput,
        "successes": success_count,
        "failures": failure_count
    }

def print_summary(result):
    print("\nStress Test Results:")
    print(f"Operation    : {result['operation']}")
    if result['operation'] in ["download", "upload"]:
        print(f"File Size    : {result['file_size']/1024/1024:.2f} MB")
        print(f"Throughput   : {result['throughput']/1024/1024:.2f} MB/s")
    print(f"Workers      : {result['total_workers']}")
    print(f"Total Time   : {result['total_time']:.2f} seconds")
    print(f"Successes    : {result['successes']}")
    print(f"Failures     : {result['failures']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-ip", default="172.16.16.101")
    parser.add_argument("--server-port", type=int, default=7777)
    parser.add_argument("--operation", choices=["download", "upload", "list"], required=True)
    parser.add_argument("--filename", help="Required for upload/download")
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    if args.operation in ["download", "upload"] and not args.filename:
        print("Error: Filename is required for upload/download operations.")
        exit(1)

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")

    result = run_stress_test(args.server_ip, args.server_port, args.operation, args.filename, args.workers)
    print_summary(result)

if __name__ == "__main__":
    main()
