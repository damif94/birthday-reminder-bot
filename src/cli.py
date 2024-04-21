import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.bot import bot, commands


def main():
    args = sys.argv[1:]
    if len(args) > 0 and args[0] == 'set-webhook':
        bot.remove_webhook()
        bot.set_webhook(url=args[1])

    elif len(args) > 0 and args[0] == 'set-commands':
        bot.set_my_commands(commands)
    else:
        print("Invalid command. Use 'set-webhook' or 'set-commands'")


if __name__ == '__main__':
    main()
