from flask import Flask, make_response, request, redirect, url_for, render_template
from os import urandom
from binascii import hexlify
from random import choice, shuffle
from datetime import datetime
from time import gmtime, strftime
from hashlib import sha512
import json
import sqlite3
import requests

app = Flask(__name__)
STATISTICS = {"Players": 0, "Completions": 0, "Tamper Attempts": 0, "Finishers": {}}
POSSIBLE_COMPLETED = 4
ADDRESS = "127.0.0.1"
PORT = 5000
DEBUG = True


# Name: Finishers
# Purpose: access finishers table in data.db
class Finishers(object):
    # Name: query
    # Purpose: query the table based off of inputs
    # Inputs: uid as string (default: None), name as string (default: None), time as integer (default: None)
    # Outputs: list of returned objects
    @staticmethod
    def query(uid):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Get data
        data = connection.execute("SELECT * FROM finishers WHERE id = ?", [uid]).fetchall()

        # Close and return data
        connection.close()
        return data

    # Name: insert
    # Purpose: insert a row into the table
    # Inputs: uid as string, name as string, time as integer
    # Outputs:
    @staticmethod
    def insert(uid, name, time):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Insert into table
        connection.execute("INSERT INTO finishers VALUES (?, ?, ?)", [uid, name, time])

        # Close connection
        connection.commit()
        connection.close()


# Name: Puzzles
# Purpose: access puzzles table in data.db
class Puzzles(object):
    # Name: query
    # Purpose: query the table based off of inputs
    # Inputs: pid as string
    # Outputs: list of returned lists
    @staticmethod
    def query(pid):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Get data
        data = connection.execute("SELECT * FROM puzzles WHERE id = ?", [pid]).fetchall()

        # Close and return data
        connection.close()
        return data

    # Name: update
    # Purpose: update a row in the table
    # Inputs: pid as string
    # Outputs:
    @staticmethod
    def update(pid):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Update completions
        prev = connection.execute("SELECT completions FROM puzzles WHERE id = ?", [pid]).fetchall()[0][0]
        connection.execute("UPDATE puzzles SET completions = ? WHERE id = ?", [prev + 1, pid])

        # Close and commit
        connection.commit()
        connection.close()

    # Name: html
    # Purpose: get html for specific puzzle
    # Inputs: pid as string
    # Outputs:
    @staticmethod
    def html(pid):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Get html for given puzzle id
        html = connection.execute("SELECT html FROM puzzles WHERE id = ?", [pid]).fetchall()[0][0]

        # Close and return data
        connection.close()
        return html

    # Name: set
    # Purpose: get random set of puzzles
    # Inputs:
    # Outputs: list of puzzle ids
    @staticmethod
    def set():
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Get all ids
        pids = []
        for pid in connection.execute("SELECT id FROM puzzles").fetchall():
            pids.append(pid[0])

        # Close connection
        connection.close()

        # Get num ids
        selected = []
        for i in range(POSSIBLE_COMPLETED):
            shuffle(pids)
            c = choice(pids)
            # Check not already chosen
            while c in selected:
                c = choice(pids)
            selected.append(c)

        # Return selected ids
        return selected


# Name: UserData
# Purpose: access user_data table in data.db
class UserData(object):
    # Name: query
    # Purpose: query the table based off of inputs
    # Inputs: uid as string
    # Outputs: list of returned objects
    @staticmethod
    def query(uid):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Get user
        user = connection.execute("SELECT * FROM user_data WHERE id = ?", [uid]).fetchall()[0]

        # Close and return user
        connection.close()
        return user

    # Name: insert
    # Purpose: insert a row into the table
    # Inputs: uid as string, pages as string, current as string time_start as integer
    # Outputs:
    @staticmethod
    def insert(uid, pages, current, time_start):
        # Connect to database
        connection = sqlite3.connect("data.db")

        # Insert into table
        connection.execute("INSERT INTO user_data (id, pages, current, start) VALUES (?, ?, ?, ?)",
                           [uid, pages, current, time_start])

        # Commit and close connection
        connection.commit()
        connection.close()

    # Name: update
    # Purpose: update a row in the table
    # Inputs: uid as string, complete as integer (default: None), end as integer (default: None), tampered as boolean (default: None)
    # Outputs:
    @staticmethod
    def update(uid, complete=None, time_end=None, tampered=None):
        # Check if user exists
        if len(UserData.query(uid)) == 0:
            return

        # Set to previous value if not passed
        if not complete:
            complete = UserData.query(uid)[2]
        if not time_end:
            time_end = UserData.query(uid)[4]
        if not tampered:
            tampered = UserData.query(uid)[5]

        # Connect to database
        connection = sqlite3.connect("data.db")

        # Update row
        connection.execute("UPDATE user_data SET complete = ?, end = ?, tampered = ? WHERE id = ?",
                           [complete, time_end, tampered, uid])

        # Commit and close connection
        connection.commit()
        connection.close()


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
# Outputs: list w/ all data
def get_data_from_cookie():
    # Get and decode data in cookie
    cookie = request.cookies.get("data").split(".")
    cookie = [cookie[0], "".join((cookie[1], cookie[2]))]
    # Return cookie dictionary
    return cookie


# Name: verify_data
# Purpose: check if all data checks out
# Inputs: cookie as list
# Outputs: boolean
def verify_data(cookie):
    # Verify uid not tampered w/
    if sha512(cookie[0].encode()).hexdigest() != cookie[1]:
        return False

    # Verify uid matches on in database
    if len(UserData.query(cookie[0])) == 0:
        return False

    # If no error, return true
    return True


# Name: create_user
# Purpose: create a users data
# Inputs:
# Outputs: jwt string
def create_user():
    # Create id and default data
    uid = hexlify(urandom(16)).decode()

    # Give user random set of 4 puzzles
    pids = Puzzles.set()

    # Set start time
    time_start = gmtime()

    # Set current puzzle to first puzzle in pages list
    c_pid = pids[0]

    # Save to database
    UserData.insert(uid, json.dumps(pids), c_pid, time_start)

    # Return string to go in cookie
    return uid + "." + sha512(uid.encode()).hexdigest()[64:] + "." + sha512(uid.encode()).hexdigest()[:64]


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
# Inputs:
# Outputs: rendered html
@app.route("/")
def index():
    return render_template("index.html")


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
            resp = make_response(render_template("tamperer.html"))
            # Remove data cookie
            resp.set_cookie("data", "", expires=0)
            return resp

        # Redirect to puzzle working on
        return redirect(url_for("puzzle"))

    resp = make_response(redirect(url_for("puzzle")))
    resp.set_cookie("data", create_user())
    return resp


# Name: finish
# Purpose: listen for post requests, finish user's challenge
# Inputs:
# Outputs: redirects
@app.route("/finish", methods=["GET", "POST"])
def finish():
    # Get cookie data
    cookie = get_data_from_cookie()

    # Validate data
    if not verify_data(cookie):
        # Remove data cookie
        resp = make_response(render_template("tamperer.html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    if request.method == "GET":
        return render_template("pre-finish.html")

    # Get form data
    name = request.form.get("name")

    # Insert into finishers database
    player = UserData.query(cookie[0])
    Finishers.insert(cookie[0], name, player[5])

    # Render finish
    return render_template("finish.html", name=name, time=player[5])


# Name: puzzle
# Purpose: listen for get requests, view a given puzzle
# Inputs:
# Outputs: rendered html
@app.route("/puzzle")
def puzzle():
    # Get cookie data
    cookie = get_data_from_cookie()

    # Validate data
    if not verify_data(cookie):
        # Remove data cookie
        resp = make_response(render_template("tamperer.html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Check if finished
    player = UserData.query(cookie[0])
    if json.loads(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] == POSSIBLE_COMPLETED:
        # Set end time & redirect to end page
        UserData.update(cookie[0], time_end=gmtime())
        return redirect(url_for("finish"))

    # Select & return current puzzle's html
    return Puzzles.html(player[2])


if __name__ == "__main__":
    app.run(host=ADDRESS, port=PORT, debug=DEBUG)
