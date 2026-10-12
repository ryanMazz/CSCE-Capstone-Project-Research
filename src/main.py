#menu interactions

import os
import scheduleViewer

def option_one():
    scheduleViewer.runViewer(True)


def option_two():
    scheduleViewer.runViewer()


def option_three():
    print("TODO")


def main():
    actions = {
        "1": option_one,
        "2": option_two,
        "3": option_three,
    }

    while True:
        print("=== Schedule Manager Demo ===")
        print("Enter a command:")
        print("1. Create new schedule")
        print("2. Load saved schedule")
        print("3. View available classes")
        print("4. Exit")

        choice = input("\n> ").strip()

        if choice == "4":
            break
        elif choice in actions:
            os.system('cls' if os.name == 'nt' else 'clear')
            actions[choice]()
        else:
            print("Invalid choice, please try again.\n")


if __name__ == "__main__":
    main()