class Message:
    def __init__(self, content, author, slack_channel, ts=None):
        self.content = content
        self.author = author
        self.slack_channel = slack_channel
        self.ts = ts