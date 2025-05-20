import subprocess
import sys

def main():
    """Run Black and flake8 to format and lint the codebase."""
    print("Running Black...")
    subprocess.run(["poetry", "run", "black", "."], check=True)
    print("Running flake8...")
    subprocess.run(["poetry", "run", "flake8", ".", "--max-line-length=120"], check=True)
    print("Formatting and linting complete.")

if __name__ == "__main__":
    main() 