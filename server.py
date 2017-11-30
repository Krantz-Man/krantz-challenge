from flask import Flask, make_response, request, redirect, url_for, render_template
from os import urandom
from binascii import hexlify
from random import choice, shuffle
from datetime import datetime
from time import gmtime, strftime
import requests

app = Flask(__name__)
PUZZLE_IDS = {"0702851a4492cb1de55ac59db87fce4e": 0,
              "7401aee89c2b8989cd35c99799794a15": 0,
              "30561bc7431486bee6780e9f844fc7b6": 0,
              "7316d2a7132b53c6b5d81d55a42a6c60": 0,
              "72b9f37d48677a429ba0c1db4eaf5f93": 0,
              "e3b4ded936b613bd9cfffcfeb34fa874": 0,
              "1739854f4d3ff2269274837a77ce0d75": 0,
              "7c045263775a5c306f16f442ccf25226": 0,
              "881b6f42d9cca3c08e361fe2dd5dcea8": 0,
              "d66dcec01318c9e87c2a5be246adfa53": 0,
              "fec66c8e8a47887eaea0bf7f5750fc85": 0,
              "8571d2129c74ca323d46f11d4c33ecbd": 0,
              "da3ffe61ad522cd3f897efd5f50620ac": 0,
              "0575ffd11831ac0adbd1ef499cf69d49": 0,
              "7da2b935a167ee54ff48c2377fc0b0a2": 0,
              "6a668de676f70f2f3c6e146c8009dd56": 0
              }
USER_DATA = {}  # "test": {"pages": ["1", "2", "3", "4"], "complete": 2}}  # <- Test set
STATISTICS = {"Players": 0, "Completions": 0, "Tamper Attempts": 0, "Finishers": {}}
POSSIBLE_COMPLETED = 4


# Name: send_stats
# Purpose: send overall game statistics
# Inputs:
# Outputs: status code
def send_stats():
    body = "Sent on: " + (datetime.now()).strftime("%m-%d-%Y %H:%M:%S") + \
            "\nPlay Statistics:\n\tPlayers: " + str(STATISTICS["Players"]) + \
            "\n\tCompletions: " + str(STATISTICS["Completions"]) + \
            "\n\tAttempted Tampers: " + str(STATISTICS["Tamper Attempts"]) + \
            "\n\tPeople to Complete: " + str(STATISTICS["Finishers"]).replace("{", "").replace("}", "").replace("'", "")
    a = ("api", "key-ad17fb62543c603f85282ff31b8c602d")
    d = {"from": "Game Info <mailgun@mg.alexkrantz.com>",
         "to": "krantzie124@gmail.com",
         "subject": "Krantz's Challenge Play Statistics",
         "text": body
         }
    return requests.post("https://api.mailgun.net/v3/mg.alexkrantz.com/messages", auth=a, data=d)


# Name: get_data_from_cookie
# Purpose: get the data from the data cookie
# Inputs:
# Outputs: dictionary w/ all data
def get_data_from_cookie():
    # Get and decode data in cookie
    cookie = request.cookies.get("data")
    cookie = jwt.decode(cookie, "959563cf6dc1dfdf2b3fef8efb82315b4493f178107b6ec79da877d789d9ae64")
    # Return cookie dictionary
    return cookie


# Name: verify_data
# Purpose: check if all data checks out
# Inputs: cookie as dict
# Outputs: boolean
def verify_data(cookie):
    try:
        # Check if not tampered w/
        if cookie["id"] in USER_DATA and cookie["pid"] in PUZZLE_IDS.keys() \
                and cookie["pid"] in USER_DATA[cookie["id"]]["pages"] \
                and cookie["pages"] == USER_DATA[cookie["id"]]["pages"] \
                and cookie["complete"] == USER_DATA[cookie["id"]]["complete"]:
            return True
        return False

    # If id invalid return invalid
    except KeyError:
        return False


# Name: create_user
# Purpose: create a users data
# Inputs:
# Outputs: jwt string
def create_user():
    # Create id and default data
    id = hexlify(urandom(16)).decode()
    USER_DATA[id] = {"complete": 0, "pages": [], "pid": None, "start": 0, "end": 0}

    # Give user random set of 4 puzzles
    for i in range(4):
        shuffle(PUZZLE_IDS)
        c = choice(PUZZLE_IDS)
        if c not in USER_DATA[id]["pages"]:
            USER_DATA[id]["pages"].append(c)

    # Set start time
    USER_DATA[id]["start"] = gmtime()

    # Set current puzzle to first puzzle in pages list
    USER_DATA[id]["pid"] = USER_DATA[id]["pages"][0]

    # Return jwt string to go in cookie
    return jwt.encode({"id": id, "pid": USER_DATA[id]["pid"], "pages": USER_DATA[id]["pages"], "complete": 0},
                      "959563cf6dc1dfdf2b3fef8efb82315b4493f178107b6ec79da877d789d9ae64").decode()




# Name: query
# Purpose: listen for post requests, send email w/ game statistics
# Inputs:
# Outputs: empty string
@app.route("/query", methods=["POST"])
def query():
    send_stats()
    return ""


# Name: index
# Purpose: listen for get requests, render main page
# Inputs: tamperer as integer (default: 0)
# Outputs: rendered html
@app.route("/")
@app.route("/<int:tamperer>")
def index(tamperer=0):
    return render_template("index.html", tamperer=tamperer)


# Name: start
# Purpose: listen for get requests, begin user's challenge
# Inputs:
# Outputs: redirect to starting page
@app.route("/start")
def start():
    if request.cookies.get("data"):
        # Get cookie data
        cookie = get_data_from_cookie()

        # Check if tampered
        if not verify_data(cookie):
            resp = make_response(redirect(url_for("index", tamperer=1)))
            # Remove data cookie
            resp.set_cookie("data", "", expires=0)
            return resp

        # Redirect to puzzle working on
        return redirect("/")

    resp = make_response(redirect("/"))
    resp.set_cookie("data", create_user())
    return resp


# Name: finish
# Purpose: listen for get requests, finish user's challenge
# Inputs:
# Outputs: rendered html
@app.route("/finish")
def finish():
    # Get cookie data
    cookie = get_data_from_cookie()

    # Validate data
    if not verify_data(cookie):
        # Remove data cookie
        resp = make_response(redirect(url_for("index", tamperer=1)))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Check if truly finished
    if cookie["completed"] != POSSIBLE_COMPLETED or cookie["pid"] != cookie["pages"][3]:
        return redirect("/")

    USER_DATA[cookie["id"]]["end"] = gmtime()