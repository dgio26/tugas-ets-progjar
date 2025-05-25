import os
import argparse

def create_binary_file(file_path, megabytes):
    total_bytes = megabytes * 1024 * 1024
    with open(file_path, "wb") as binary_file:
        binary_file.write(os.urandom(total_bytes))
    print(f"Generated: {file_path} ({megabytes} MB)")

def main():
    parser = argparse.ArgumentParser(description="Create binary files filled with random data.")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[10, 50, 100],
        help="List of file sizes to generate in megabytes (default: 10 50 100)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="random",
        help="Filename prefix for generated files (default: 'random')"
    )
    args = parser.parse_args()

    os.makedirs("files", exist_ok=True)

    for mb_size in args.sizes:
        file_name = f"files/{args.prefix}_{mb_size}mb.bin"
        create_binary_file(file_name, mb_size)

if __name__ == "__main__":
    main()
