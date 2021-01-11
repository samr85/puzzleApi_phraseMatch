from re import split
import tornado.web

from . import phraseMatch

class PhraseMatchWeb(tornado.web.RequestHandler):
    def get(self):
        self.post()

    def post(self):
        joinedRegex = self.get_argument("splitRegex", "")

        # Check regex looks valid-ish
        if any(badChar in joinedRegex for badChar in "+?*"):
            raise tornado.web.HTTPError(400, "Invalid regex requested: Each group must match 1 character - no + ? or *")
    
        splitRegex = joinedRegex.split(" ")
        if len(splitRegex) < 3 or len(splitRegex) > 30:
            raise tornado.web.HTTPError(400, "Invalid regex requested: This should be a list of space separated single character matches, between 3 and 30 groups long")

        matches = phraseMatch.findPhrases(splitRegex)

        self.write(matches)

INDEX_HTML = """
<h1>Search for a sequence of words matching a word-split regex</h1>
<p>Search using: /phraseMatch/?splitRegex={wordListName}</p>
<p>Example regex to search: "g a l [^m] e r y u n i . g i r a f [efg] e"  This will return "gallery unit giraffe"</p>
<form method='get' action="/phraseMatch/">
split regex to search: <input type="text" name="splitRegex" value="g a l [^m] e r y u n i . g i r a f [efg] e"></input>
</form>
"""

requests = [
    (r"/phraseMatch/", PhraseMatchWeb),
]

indexItems = [
    INDEX_HTML,
]

