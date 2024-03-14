from pathlib import Path
from subprocess import Popen


def main():
    while True:
        try:
            command = input("> ")
            for project in Path.cwd().glob("packages/*"):
                popen = Popen(command, shell=True, cwd=project)
                popen.wait()
        except KeyboardInterrupt:
            break
    print("Goodbye!")


if __name__ == "__main__":
    main()
