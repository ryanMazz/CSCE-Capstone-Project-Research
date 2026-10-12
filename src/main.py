#menu interactions

import os
import scheduleViewer

def option_one():
    scheduleViewer.runViewer(True)

def option_two():
    scheduleViewer.runViewer()

def main():
    actions = {
        "1": option_one,
        "2": option_two
    }

    while True:
        print("=== Schedule Manager Demo ===")
        print("Enter a command:")
        print("1. Create new schedule")
        print("2. Load saved schedule")
        print("3. Exit")

        choice = input("\n> ").strip()

        if choice == "3":
            break
        elif choice in actions:
            os.system('cls' if os.name == 'nt' else 'clear')
            actions[choice]()
        else:
            print("Invalid choice, please try again.\n")


if __name__ == "__main__":
    main()