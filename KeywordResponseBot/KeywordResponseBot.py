import os
from threading import Thread
from time import sleep, time

import praw
from praw.exceptions import RedditAPIException
from psaw import PushshiftAPI


# TODO Write comments methods (brief description)
# TODO Write loggers and corresponding files (maybe a folder for errors, info, etc. one for each day)

class KeywordResponseBot:
    KEYWORDS = ["69", "nice"]
    SEARCH_QUERY = "69"
    TIME_SINCE_COMMENT_CREATED = "6h"
    USERNAME = os.environ.get('USERNAME')
    MSG = "Nice ( ͡° ͜ʖ ͡°)\n" \
          "&nbsp;\n\n" \
          "&nbsp;\n\n" \
          "___\n" \
          "^Down ^vote ^for ^me ^to ^remove ^myself. ^(ಥ ͜ʖಥ)"

    def __init__(self, clean_mode):
        self.clean_mode = clean_mode
        self.reddit = praw.Reddit(client_id=os.environ.get('CLIENT_ID'),
                                  client_secret=os.environ.get('CLIENT_SECRET'),
                                  user_agent='NiceBot v1.0',
                                  username=self.USERNAME,
                                  password=os.environ.get('PASSWORD'))
        self.api = PushshiftAPI(self.reddit)
        self.ids = []
        self.ignore_list = []
        self.blacklisted_subreddits = []
        self.current_comment = None
        self.timed_out_message = None

    def get_ids(self):
        print("Loading Stored Comment Ids...")
        with open('ids.txt', 'r') as id_file:
            for line in id_file.readlines():
                self.ids.append(line.strip())

    def get_ignore_list(self):
        print("Loading Comment Author Ignore List...")
        with open('ignore.txt', 'r') as ignore_file:
            for line in ignore_file:
                self.ignore_list.append(line.strip())

    def get_blacklisted_subreddits(self):
        print("Loading Blacklisted Subreddits...")
        with open("subreddit_blacklist.txt", 'r') as black_list_file:
            for line in black_list_file:
                self.blacklisted_subreddits.append(line.strip())

    def write_id_to_file(self):
        with open('ids.txt', 'a') as id_file:
            id_file.write(self.current_comment.id + "\n")

    def wait_to_post(self):
        # Only for new accounts that need comment karma to post more often
        s = self.timed_out_message.split(" ")
        if "minute" in s[len(s) - 1]:
            wait_time = int(s[len(s) - 2]) * 60
        else:
            wait_time = int(s[len(s) - 2])
        print("waiting {} seconds".format(wait_time))
        sleep(wait_time)

    def search_comments(self):
        for comment in self.api.search_comments(q=self.SEARCH_QUERY, after=self.TIME_SINCE_COMMENT_CREATED):
            self.current_comment = comment
            if self.current_comment.id not in self.ids:
                if self.current_comment.subreddit not in self.blacklisted_subreddits \
                        and self.current_comment.author not in self.ignore_list:
                    self.process_comment()
                else:
                    self.write_id_to_file()
                    self.ids.append(self.current_comment.id)

    def process_comment(self):
        text = self.current_comment.body
        if all(kw in text.lower() for kw in self.KEYWORDS) and len(text) < 75:
            self.ids.append(self.current_comment.id)
            self.write_id_to_file()
            self.current_comment.upvote()
            print("Comment meets requirements")
            print("reddit.com" + self.current_comment.permalink)
            print(text)
            print("=========")
            # self.current_comment.reply(self.MSG)

    def check_downvoted_comments(self):
        print("Checking Downvoted Comments")
        for account_comment in self.reddit.redditor(self.USERNAME).comments.new(limit=100):
            if account_comment.score <= (1 if self.clean_mode else 0):
                print("Deleting comment - id: {} | Sub: {} | Parent-Link: {}".format(account_comment.id,
                                                                                     account_comment.subreddit,
                                                                                     account_comment.parent().permalink))
                account_comment.delete()

    def print_comment_karma(self):
        comment_karma = self.reddit.redditor(self.USERNAME).comment_karma
        print(f"Comment Karma -- {comment_karma}")

    def run_bot(self):
        self.get_ids()
        self.get_ignore_list()
        self.get_blacklisted_subreddits()
        print("Clean Mode: {}\n"
              "Search: {}".format("ON" if self.clean_mode else "OFF",
                                  "OFF" if self.clean_mode else "ON"))
        start_time = time()
        while True:
            end_time = time()
            seconds = end_time - start_time
            try:
                # Fix the cleaning logic
                if not self.clean_mode:
                    self.search_comments()
                if seconds >= 600:
                    start_time = time()
                    self.print_comment_karma()
                    comment_check = Thread(target=self.check_downvoted_comments)
                    comment_check.start()
            except RedditAPIException as e:
                error_type = e.error_type
                if error_type == "THREAD_LOCKED":
                    print("Thread is locked, cannot reply")
                    continue
                self.timed_out_message = e.message
                self.wait_to_post()
            except TypeError as e:
                seconds_to_sleep = 60
                print(e.message)
                print(f"Sleeping for {seconds_to_sleep} seconds")
                sleep(seconds_to_sleep)


if __name__ == '__main__':
    keyword_response_bot = KeywordResponseBot(False)
    print("Starting NiceBot...")
    keyword_response_bot.run_bot()
