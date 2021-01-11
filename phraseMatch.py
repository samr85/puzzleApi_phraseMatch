from collections import deque
import math
import operator
import re
from typing import Any, List, NamedTuple, Optional, Tuple
# Take the already loaded wordlist from regexWordList

from ..listRegex.regexWordList import MATCH_LISTS

def DEBUG_PRINT (_:Any):
    pass
#DEBUG_PRINT = print

# Superfluous short words really mess this up
# So removing any which aren't really valid words in common usage
#SHORT_WORDS = ["a", "i", "am", "an", "as", "at", "by", "do", "go", "he", "hi", "if", "in", "is", "it", "me", "my", "no", "oh", "ok", "on", "or", "ox", "oy", "pi", "re", "to", "we"]
# Cut down to this many routes for each length based on heighest weight
MAX_ROUTES_PER_LEN=30
MAX_MATCHES_PER_POSITION=100000
MAX_ROUTE_LEN=6
MAX_END_ROUTES=50

class Entry(NamedTuple):
    word: str
    # The length of the word is used many times, so best to save it off than keep recalculating
    wordLen: int
    weight: float

WEIGHTED_WORD_LIST: List[Entry]  = []
def makeWeightedWordList():
    for (word, weight) in MATCH_LISTS["commonWords"][1]:
        # Reweight so longer words are worth more than shorter ones

        wLen = len(word)
        # Remove single letter "words" from the list - they aren't valid words
        if wLen == 1 and word not in ("a", "i"):
            continue

        #WEIGHTED_WORD_LIST.append(Entry(word, int() * math.sqrt(wLen)))
        #WEIGHTED_WORD_LIST.append(Entry(word, wLen, math.sqrt(int(weight)) * wLen * wLen))
        WEIGHTED_WORD_LIST.append(Entry(word, wLen, math.log(int(weight)) * wLen * wLen))
        #WEIGHTED_WORD_LIST.append(Entry(word, wLen, math.log(int(weight)) * wLen))
    WEIGHTED_WORD_LIST.sort(key=operator.itemgetter(2), reverse=True)
    
    """
    print(WEIGHTED_WORD_LIST[:50])
    for i, (name, weight) in enumerate(WEIGHTED_WORD_LIST):
        if name == "a":
            print("a at: %d with weight: %d"%(i, weight))
            break
    """

# Initial setup to create the wordlist that this later searches
makeWeightedWordList()

class Route(NamedTuple):
    entry: Entry
    maxWeight: float
    maxWeightCount: int
    # Any is actually Route - mypy can't cope with recursive types
    subRoute: Optional[List[Any]] = []

def findWords(regexInput: List[str]) -> List[Entry]:
    remainingLen = len(regexInput)
    regexList: List[re.Pattern] = []
    for i in range(remainingLen + 1):
        regexList.append(re.compile("".join(regexInput[:i]))) 

    matches: List[Entry] = []

    for match in WEIGHTED_WORD_LIST:
        if match.wordLen > remainingLen:
            continue
        if regexList[match.wordLen].fullmatch(match.word):
            matches.append(match)
            if len(matches) == MAX_MATCHES_PER_POSITION:
                break

    return matches

def flattenRoute(route: Route, curWords: Tuple[str, ...], curWeight: Tuple[float, ...], allRoutes: List[Tuple[Tuple[str, ...], float, Tuple[float, ...]]], minWeight: List[float]):
    newWords = curWords + (route.entry.word, )
    newWeights = curWeight + (route.entry.weight, )
    if not route.subRoute:
        avW = sum(newWeights) / len(newWeights)
        # Are we better than the worst currently stored?
        if avW < minWeight[0]:
            return
        
        storeRoute = (newWords, avW, newWeights)
        allRoutes.append(storeRoute)
        allRoutes.sort(key=operator.itemgetter(1), reverse=True)
        if len(allRoutes) > MAX_END_ROUTES:
            del allRoutes[-1]
            minWeight[0] = allRoutes[-1][1]
    else:
        if len(newWords) == MAX_ROUTE_LEN:
            return
        futureRoute: Route
        for futureRoute in route.subRoute:
            if minWeight[0]:
                # Does this route stand a chance of beeting the worst match we've found so far?
                maxRouteWeight = (futureRoute.maxWeight * futureRoute.maxWeightCount + sum(newWeights))/(futureRoute.maxWeightCount + len(newWeights))
                if maxRouteWeight < minWeight[0]:
                    continue
            flattenRoute(futureRoute, newWords, newWeights, allRoutes, minWeight)

def calcRollingAverage(new, old, oldCount):
    return ((old * oldCount) + new) / oldCount + 1

def findPhrases(regexInput: List[str]):
    import datetime
    start = datetime.datetime.now()

    inputLen = len(regexInput)
    # Start by finding any words that match at any position
    posMatches:List[List[Entry]] = []
    for i in range(inputLen):
        posMatches.append(findWords(regexInput[i:]))

    regexDone = datetime.datetime.now()
    DEBUG_PRINT("found matches: %s"%(regexDone - start))

    routes: List[List[Route]] = [[]] * inputLen
    # Now find routes through the lists
    for i in range(inputLen - 1, -1, -1):
        newRoutes: List[Route] = []
        for match in posMatches[i]:
            if match.wordLen == inputLen - i:
                newRoutes.append(Route(match, match.weight, 1, None))
            else:
                diff = i + match.wordLen
                if len(routes[diff]):
                    bestWeight = max([
                        (calcRollingAverage(match.weight, subRoute.maxWeight, subRoute.maxWeightCount), subRoute.maxWeightCount + 1) for subRoute in routes[diff]
                        ])
                    newRoutes.append(Route(match, bestWeight[0], bestWeight[1], routes[diff]))
                # else: dead match, ignore
        newRoutes.sort(key=operator.itemgetter(1), reverse=True)
        DEBUG_PRINT("length for %d: %d"%(i, len(newRoutes)))
        routes[i] = newRoutes[:MAX_ROUTES_PER_LEN]

    routesFound = datetime.datetime.now()
    DEBUG_PRINT("Routes found: %s"%(routesFound - regexDone))

    allRoutes: List[Tuple[Tuple[str, ...], float, Tuple[float, ...]]] = []
    # We now have all of the valid routes through the regex, flatten and sort by weight
    # Weight should be the average weight of all the words
    route: Route
    minWeight = [0.0]
    for route in routes[0]:
        curWords = (route.entry.word, )
        curWeight = (route.entry.weight, )
        if route.subRoute:
            for futureRoute in route.subRoute:
                flattenRoute(futureRoute, curWords, curWeight, allRoutes, minWeight)
        else:
            allRoutes.append((curWords, route.entry.weight, curWeight))
    allRoutes.sort(key=operator.itemgetter(1), reverse=True)
    DEBUG_PRINT("Found routes: %s"%(len(allRoutes)))
    for i in range(min(50, len(allRoutes))):
        DEBUG_PRINT(allRoutes[i])

    flattenDone = datetime.datetime.now()
    DEBUG_PRINT("Flattening: %s\nTotal: %s"%(flattenDone - routesFound, flattenDone - start))
    return {"Matches": [{"Words": route[0], "Weight": route[1], "AllWeights": route[2]} for route in allRoutes]}

def test():
    # Test match: operabarrelbath
    # test input: op.rabar.elb[ae]th
    # split test input: "o p . r a b a r . e l b [ae] t h"
    input = "o p . r a . a . . e l a r e b [ae] . h".split(" ")
    foundRoutes = findPhrases(input)
    for i, route in enumerate(foundRoutes["Matches"]):
        print(route)
        if i == 50:
            break