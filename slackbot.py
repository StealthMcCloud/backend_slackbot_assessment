#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A slackbot that responds to commands.
This uses the Slack RTM (Real Time Messaging) API.
Required environment variables (example only, these are not real tokens).
Get these from the Slack account settings that you are connecting to.
   BOT_USER_ID = 'U20981S736'
   BOT_USER_TOKEN = 'xoxb-106076235608-AbacukynpGahsicJqugKZC'
"""

__author__ = 'Clinton Johnson & Jen Browning'

import os
import time
import re
import requests
import logging
import signal
from slackclient import SlackClient
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = 'Wally'
BOT_CHAN = '#general'
welcome_message = "Wally is online and awaiting instructions!"
# On location of... his testicles!
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
BOT_USER_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
exit_flag = False

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
logger = logging.getLogger(__name__)

bot_commands = {
    'help': 'Inform user to use help_list to see list of commands',
    'ping': 'shows uptime of bot',
    'exit': 'terminates current running bot program',
    'raise': 'Raises an exception',
    'get quote': 'Displays a random breaking bad quote'
}

def formatted_dict(d, k_header='Keys', v_header='Values'):
    """Renders contents of a dict into a preformatted string"""
    if d:
        lines = []
        # find the longest key entry in d or the key header string
        width = max(map(len, d))
        width = max(width, len(k_header))
        lines.extend(['{k:<{w}} : {v}'.format(k=k_header, v=v_header, w=width)])
        lines.extend(['-'*width + '   ' + '-'*len(v_header)])
        lines.extend('{k:<{w}} : {v}'.format(k=k, v=v, w=width) for k, v in d.items())
        return '\n'.join(lines)
    return "<empty>"

help_text = formatted_dict(bot_commands, k_header="My cmds", v_header='What they do')

def config_logger():
    """Setup logging configuration"""
    global logger
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s:%(message)s')
    file_handler = logging.FileHandler("filelog.log")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def command_loop(bot):
    """Process incoming bot commands"""
    command, channel = bot.parse_bot_commands(bot.slack_client.rtm_read())
    if command:
        if command == "help":
            bot.help(channel)
        elif command == "exit":
            bot.__exit__(channel)
        elif command == "ping":
            bot.ping(channel)
        elif command == "raise":
            bot.raise_(channel)
        elif command == "get quote":
            bot.get_bb_quote(channel)
        else:
            message = "Invalid command.  Please use 'help' to see available commands"
            slack_client.api_call(
            "chat.postMessage",
            channel=BOT_CHAN,
            text=message
        )

def signal_handler(sig_num, frame):
    global logger
    logger.info(f"signal number: {sig_num}")
    if sig_num == 2:
        global exit_flag
        exit_flag = True


class SlackBot:

    def __init__(self, bot_user_token, bot_id=None):
        """Create a client instance"""
        self.slack_client = SlackClient(bot_user_token)
        self.name = BOT_NAME
        self.bot_start = None
        self.start_time = time.time()
        if self.slack_client.rtm_connect(with_team_state=False):
            logger.info(f"{self.name} connected and running!")
            self.bot_id = slack_client.api_call('auth.test')['user_id']

    def __repr__(self):
        pass

    def __str__(self):
        pass

    def __enter__(self):
        """Implement this method to make this a context manager"""
        pass

    def help(self, channel):
        self.post_message("```" + help_text + "```", channel)

    def get_bb_quote(self, channel):
        URL = 'https://breaking-bad-quotes.herokuapp.com/v1/quotes'
        r = requests.get(URL).json()
        message = r[0]['quote']
        self.post_message(message, channel)

    def raise_(self, channel):
        message = "Oh you are giving me a raise?"
        self.post_message(message, channel)
        time.sleep(2)
        raise Exception("I am an unhandled disgruntled exception")

    def ping(self, channel):
        stime = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)
            )
        message = f"{self.name} has been running since {stime}."
        self.post_message(message, channel)

    def __exit__(self, channel):
        self.post_message(f'{self.name} is heading to the tavern to grab a drink.', channel)
        global exit_flag
        exit_flag = True

    def post_message(self, message, chan=BOT_CHAN):
        """Sends a message to a Slack Channel"""
        self.slack_client.api_call(
            "chat.postMessage",
            channel=BOT_CHAN,
            text=message
        )

    def parse_bot_commands(self, slack_events):
        for event in slack_events:
            if event.get("type") == "message" and "subtype" not in event:
                user_id, message = self.parse_direct_mention(event.get("text"))
                if user_id == self.bot_id:
                    return message, event.get("channel")
        return None, None

    def parse_direct_mention(self, message_text):
        matches = re.search(MENTION_REGEX, message_text)
        if matches:
            return matches.group(1), matches.group(2).strip()
        else:
            return (None, None)


def main():
    config_logger()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    bot = SlackBot(BOT_USER_TOKEN)
    bot.post_message(f"{bot.name} ready for your command.", BOT_CHAN)
    while exit_flag is False:
        try:
            command_loop(bot)
        except Exception as e:
            logger.error(str(e))
        time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")

if __name__ == "__main__":
    main()