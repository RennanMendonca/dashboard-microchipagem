import sys
from html.parser import HTMLParser


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void = {'meta', 'input', 'br', 'img', 'hr', 'link'}
        self.ok = True

    def handle_starttag(self, tag, attrs):
        if tag in self.void:
            return
        self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if not self.stack:
            self.ok = False
            return
        top, pos = self.stack[-1]
        if top == tag:
            self.stack.pop()
        else:
            self.ok = False
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break


html = open("index.html", encoding="utf-8").read()
body = html.split('<script>')[0]
c = Checker()
c.feed(body)
if not c.ok:
    print("HTML COM TAGS DESBALANCEADAS - abortando publicacao")
    sys.exit(1)
print("HTML OK")
