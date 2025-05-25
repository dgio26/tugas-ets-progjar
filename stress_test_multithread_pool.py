import os
import time
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from file_client_multithread_pool import FileClient

class StressTestRunner:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.test_data = []
        self.test_files = {
            'small': 'random_10mb.bin',
            'medium': 'random_50mb.bin',
            'large': 'random_100mb.bin'
        }

    def validate_files(self):
        for label, fname in self.test_files.items():
            if not os.path.isfile(fname):
                print(f"Missing required test file: {fname}")
                return False
        return True

    def execute_test(self, mode, filepath, client_count, server_pool):
        size_in_bytes = os.path.getsize(filepath)
        print(f"\n[{mode.upper()}] File: {filepath}, Size: {size_in_bytes / (1024**2):.2f} MB, Clients: {client_count}, Server Pool: {server_pool}")

        client = FileClient(self.server_ip, self.server_port)
        start = time.time()

        with ThreadPoolExecutor(max_workers=client_count) as executor:
            futures = [
                executor.submit(client.remote_upload if mode == "upload" else client.remote_get, filepath)
                for _ in range(client_count)
            ]
            responses = [f.result() for f in futures]

        elapsed = time.time() - start
        successful = [r for r in responses if r[0]]
        failed = client_count - len(successful)
        transferred_bytes = sum(r[2] for r in successful)
        throughput_mb = (transferred_bytes / elapsed) / (1024 * 1024) if elapsed > 0 else 0
        avg_latency = sum(r[1] for r in responses) / client_count if client_count > 0 else 0

        outcome = {
            'timestamp': datetime.now().isoformat(),
            'operation': mode,
            'volume': f"{size_in_bytes // (1024 * 1024)} MB",
            'client_workers': client_count,
            'server_workers': server_pool,
            'duration': round(elapsed, 2),
            'throughput': round(throughput_mb, 2),
            'client_success': len(successful),
            'client_fail': failed,
            'server_success': len(successful),
            'server_fail': failed
        }

        self.test_data.append(outcome)
        self.display_result(outcome)
        return outcome

    def display_result(self, outcome):
        print("\nTest Summary")
        print(f"Operation      : {outcome['operation'].upper()}")
        print(f"File Volume    : {outcome['volume']}")
        print(f"Client Workers : {outcome['client_workers']}")
        print(f"Server Workers : {outcome['server_workers']}")
        print(f"Total Time     : {outcome['duration']} s")
        print(f"Throughput     : {outcome['throughput']} MB/s")
        print(f"Client Success : {outcome['client_success']} / {outcome['client_workers']}")
        print(f"Client Fail    : {outcome['client_fail']}")
        print(f"Server Success : {outcome['server_success']} / {outcome['server_success']}")
        print(f"Server Fail    : {outcome['server_fail']}")

    def perform_all_tests(self):
        if not self.validate_files():
            return False

        modes = ['download', 'upload']
        sizes = ['small', 'medium', 'large']
        client_counts = [1, 5, 50]
        server_pool_sizes = [1]

        total = len(modes) * len(sizes) * len(client_counts) * len(server_pool_sizes)
        counter = 1

        for mode in modes:
            for size in sizes:
                for c_count in client_counts:
                    for s_count in server_pool_sizes:
                        print(f"\nInitiating test {counter} of {total}")
                        file_path = self.test_files[size]
                        self.execute_test(mode, file_path, c_count, s_count)
                        time.sleep(5)
                        counter += 1
        return True

    def export_results(self, filename="stress_results_thread.csv"):
        if not self.test_data:
            print("No data available for export.")
            return False

        headers = [
            'timestamp', 'operation', 'volume', 'client_workers', 'server_workers',
            'duration', 'throughput', 'client_success', 'client_fail',
            'server_success', 'server_fail'
        ]

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.test_data)
            print(f"\nResults successfully written to {filename}")
            return True
        except Exception as e:
            print(f"Failed to save results: {e}")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Automated Load Testing Tool for File Transfers")
    parser.add_argument("--server-ip", default="172.16.16.101")
    parser.add_argument("--server-port", type=int, default=7778)
    parser.add_argument("--single-test", action="store_true")
    parser.add_argument("--operation", choices=["upload", "download"])
    parser.add_argument("--file-size", choices=["small", "medium", "large"])
    parser.add_argument("--client-workers", type=int)
    parser.add_argument("--server-workers", type=int, default=1)
    parser.add_argument("--output", default="stress_results_thread.csv")

    args = parser.parse_args()
    runner = StressTestRunner(args.server_ip, args.server_port)

    if args.single_test:
        if not all([args.operation, args.file_size, args.client_workers]):
            print("Missing required arguments for single test mode.")
            exit(1)
        file_path = runner.test_files[args.file_size]
        runner.execute_test(args.operation, file_path, args.client_workers, args.server_workers)
    else:
        print("Executing comprehensive test matrix...")
        runner.perform_all_tests()

    runner.export_results(args.output)


if __name__ == "__main__":
    main()
    