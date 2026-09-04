import re

def callback(message):
    message = re.sub(
        rb'\n?Co-authored-by: Cursor <cursoragent@cursor.com>\s*',
        b'\n',
        message
    )
    return message