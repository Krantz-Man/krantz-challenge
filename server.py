from flask import Flask, make_response, request, redirect, url_for, render_template
from os import urandom
from binascii import hexlify
from random import choice, shuffle
from time import time, strftime
from hashlib import sha512
import json
import sqlite3
import requests

app = Flask(__name__)
STATISTICS = {"Players": 0, "Completions": 0, "Tamper Attempts": 0,
              "Finishers": [], "Highscore": ["None", 0], "Tamperers": []}
POSSIBLE_COMPLETED = 4
ADDRESS = "127.0.0.1"
PORT = 5000
DEBUG = True
DATABASE = "data.db"


# Name: Finishers
# Purpose: access finishers table in data.db
class Finishers(object):
    # Name: query
    # Purpose: query the table based off of inputs
    # Inputs: uid as string
    # Outputs: list of returned objects
    @staticmethod
    def query(uid):
        # Connect to database
        connection = sqlite3.connect(DATABASE)

        # Get data
        data = connection.execute("SELECT * FROM finishers WHERE id = ?", [uid]).fetchone()
        if not data:
            data = None

        # Close and return data
        connection.close()
        return data

    # Name: insert
    # Purpose: insert a row into the table
    # Inputs: uid as string, name as string, email as string, total_time as integer
    # Outputs:
    @staticmethod
    def insert(uid, name, email, total_time):
        # Connect to database
        connection = sqlite3.connect(DATABASE)

        # Insert into table
        connection.execute("INSERT INTO finishers VALUES (?, ?, ?, ?)", [uid, name, email, total_time])

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
        connection = sqlite3.connect(DATABASE)

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
        connection = sqlite3.connect(DATABASE)

        # Update completions
        prev = connection.execute("SELECT completions FROM puzzles WHERE id = ?", [pid]).fetchone()
        if not prev:
            return
        else:
            prev = prev[0]
        connection.execute("UPDATE puzzles SET completions = ? WHERE id = ?", [prev + 1, pid])

        # Close and commit
        connection.commit()
        connection.close()

    # Name: solution
    # Purpose: get solution for given puzzle
    # Inputs: pid as string
    # Outputs: solution as string
    @staticmethod
    def solution(pid):
        # Connect to database
        connection = sqlite3.connect(DATABASE)

        # Get solution from table
        sol = connection.execute("SELECT solution FROM puzzles WHERE id = ?", [pid]).fetchone()
        if not sol:
            sol = None
        else:
            sol = sol[0]

        # Close connection & return data
        connection.close()
        return sol

    # Name: html
    # Purpose: get data for specific puzzle
    # Inputs: pid as string
    # Outputs: tuple of title and prompt
    @staticmethod
    def data(pid):
        # Connect to database
        connection = sqlite3.connect(DATABASE)

        # Get html for given puzzle id
        data = connection.execute("SELECT title, prompt FROM puzzles WHERE id = ?", [pid]).fetchone()
        if not data:
            data = None

        # Close and return data
        connection.close()
        return data

    # Name: set
    # Purpose: get random set of puzzles
    # Inputs:
    # Outputs: list of puzzle ids
    @staticmethod
    def set():
        # Connect to database
        connection = sqlite3.connect(DATABASE)

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
        connection = sqlite3.connect(DATABASE)

        # Get user
        user = connection.execute("SELECT * FROM user_data WHERE id = ?", [uid]).fetchone()

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
        connection = sqlite3.connect(DATABASE)

        # Insert into table
        connection.execute("INSERT INTO user_data (id, pages, current, start) VALUES (?, ?, ?, ?)",
                           (uid, pages, current, time_start))

        # Commit and close connection
        connection.commit()
        connection.close()

    # Name: update
    # Purpose: update a row in the table
    # Inputs: uid as string, complete as integer (default: None), time_end as integer (default: None),
    #           tampered as boolean (default: None), current as string (default: None)
    # Outputs:
    @staticmethod
    def update(uid, complete=None, time_end=None, tampered=None, current=None):
        # Check if user exists
        if len(UserData.query(uid)) == 0:
            return

        # Set to previous value if not passed
        if not complete:
            complete = UserData.query(uid)[3]
        if not time_end:
            time_end = UserData.query(uid)[5]
        if not tampered:
            tampered = UserData.query(uid)[6]
        if not current:
            current = UserData.query(uid)[2]

        # Connect to database
        connection = sqlite3.connect(DATABASE)

        # Update row
        connection.execute("UPDATE user_data SET complete = ?, end = ?, tampered = ?, current = ? WHERE id = ?",
                           [complete, time_end, tampered, current, uid])

        # Commit and close connection
        connection.commit()
        connection.close()


# Name: send_stats
# Purpose: send overall game statistics
# Inputs:
# Outputs: status code
def send_stats():
    # Format finishers
    finishers = ""
    for i, finisher in enumerate(STATISTICS["Finishers"]):
        finishers += "\t" + str(i + 1) + ": "
        finishers += "Name: " + finisher["name"] + ", "
        finishers += "Email: " + finisher["email"] + ", "
        finishers += "Time: " + str(finisher["time"]) + " seconds\n"

    # Format tamperers
    tamperers = ""
    for i, tamperer in enumerate(STATISTICS["Tamperers"]):
        tamperers += "\t" + str(i + 1) + ": "
        tamperers += "Name: " + tamperer["name"] + ", "
        tamperers += "Email: " + tamperer["email"] + "\n"

    body = "Sent on: " + strftime("%m-%d-%Y %H:%M:%S") + "\n\n" + \
           "\nPlay Statistics:\n\tPlayers: " + str(STATISTICS["Players"]) + \
           "\n\tCompletions: " + str(STATISTICS["Completions"]) + \
           "\n\tAttempted Tampers: " + str(STATISTICS["Tamper Attempts"]) + \
           "\n\tHighscore Holder: " + str(STATISTICS["Highscore"][0]) + \
           " with a time of " + str(STATISTICS["Highscore"][1]) + " seconds" + \
           "\n\nFinishers:\n" + finishers + \
           "\n\nTamperers:\n" + tamperers
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
    # Return cookie list
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
    if not UserData.query(cookie[0]):
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
    time_start = int(time())

    # Set current puzzle to first puzzle in pages list
    c_pid = pids[0]

    # Save to database
    UserData.insert(uid, json.dumps(pids), c_pid, time_start)

    # Return string to go in cookie
    return uid + "." + sha512(uid.encode()).hexdigest()


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
    return render_template("index.dev.html")


# Name: start
# Purpose: listen for get requests, begin user's challenge
# Inputs:
# Outputs: redirect to starting page
@app.route("/start")
def start():
    # Check user has not started
    if request.cookies.get("data"):
        # Get cookie data
        cookie = get_data_from_cookie()

        # Check if tampered
        if not verify_data(cookie):
            # Update tamper statistics
            STATISTICS["Tamper Attempts"] += 1

            resp = make_response(render_template("tamperer.dev.html"))
            # Remove data cookie
            resp.set_cookie("data", "", expires=0)
            return resp

        # Redirect to puzzle working on
        return redirect(url_for("puzzle"))

    # Update statistics
    STATISTICS["Players"] += 1

    # Create response w/ cookie
    resp = make_response(redirect(url_for("puzzle")))
    resp.set_cookie("data", create_user(), expires=(time() + 316000000))
    return resp


# Name: finish
# Purpose: listen for get & post requests, finish user's challenge
# Inputs:
# Outputs: redirects
@app.route("/finish", methods=["GET", "POST"])
def finish():
    # Check user has started
    if not request.cookies.get("data"):
        return render_template("tamperer.dev.html")

    # Get cookie data
    cookie = get_data_from_cookie()
    played = request.cookies.get("pstatus")

    # Validate data
    if not verify_data(cookie):
        # Update tamper statistics
        STATISTICS["Tamper Attempts"] += 1

        # Remove data cookie
        resp = make_response(render_template("tamperer.dev.html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    if request.method == "GET":
        c = Finishers.query(cookie[0])
        if c:
            return render_template("finish.dev.html", name=c[1], time=c[2])

        return render_template("pre-finish.dev.html")

    # Get form data
    name = request.form.get("name")
    email = request.form.get("email")

    # Insert into finishers database
    player = UserData.query(cookie[0])
    if player[6] != 1:
        Finishers.insert(cookie[0], name, email, player[5])

    # Update completions & finishers
    STATISTICS["Completions"] += 1
    STATISTICS["Finishers"].append({"name": name, "email": email, "time": (player[5] - player[4])})

    # Check if already played
    if played:
        return render_template("finish.dev.html", name=name, time=(player[5] - player[4]), played=played)

    # Check if tampered
    if player[6] == 1:
        # Remove from completions/finishers & add to tamperers
        STATISTICS["Completions"] -= 1
        STATISTICS["Tamperers"].append(STATISTICS["Finishers"].pop(len(STATISTICS["Finishers"]) - 1))

        # Load tamper data
        tamper = [POSSIBLE_COMPLETED, player[3], json.loads(player[1]).index(player[2]) + 1]

        # Render 'finish'
        return render_template("finish.dev.html", name=name, time=(player[5] - player[4]), tamperer=tamper)

    # Render finish
    resp = make_response(render_template("finish.dev.html", name=name, time=(player[5] - player[4])))
    resp.set_cookie("pstatus", "1", expires=(time() + 316000000))
    return resp


# Name: puzzle
# Purpose: listen for get requests, view a given puzzle
# Inputs:
# Outputs: rendered html
@app.route("/puzzle")
def puzzle():
    # Check user has started
    if not request.cookies.get("data"):
        return render_template("tamperer.dev.html")

    # Get cookie data
    cookie = get_data_from_cookie()

    # Validate data
    if not verify_data(cookie):
        # Update tamper statistics
        STATISTICS["Tamper Attempts"] += 1

        # Remove data cookie
        resp = make_response(render_template("tamperer.dev.html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Select & return current puzzle's html
    player = UserData.query(cookie[0])
    data = Puzzles.data(player[2])
    return render_template("puzzle.dev.html", title=data[0], prompt=data[1])


# Name: check
# Purpose: listen for get & post requests, check answer for puzzle
# Inputs:
# Outputs: redirection
@app.route("/check", methods=["GET", "POST"])
def check():
    # Check if user has started
    if not request.cookies.get("data"):
        return render_template("tamperer.dev.html")

    # Redirect to puzzle if get request
    if request.method == "GET":
        return redirect(url_for("puzzle"))

    # Get cookie data
    cookie = get_data_from_cookie()
    # Validate data
    if not verify_data(cookie):
        # Update tamper statistics
        STATISTICS["Tamper Attempts"] += 1

        # Remove data cookie
        resp = make_response(render_template("tamperer.dev.html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Get other data
    player = UserData.query(cookie[0])
    solution = Puzzles.solution(player[2])
    response = request.form.get("response")

    # Validate response for strings, ints & booleans
    try:
        # Create true and false values
        true_values = ["True", "true", "T", "t"]
        false_values = ["False", "false", "F", "f"]
        # Check strings
        if type(solution) == str and response.lower() != solution:
            return redirect(url_for("puzzle"))
        # Check integers
        elif type(solution) == int and ("." in str(response) or int(response) != solution):
            return redirect(url_for("puzzle"))
        # Check floats
        elif type(solution) == float and float(response) != solution:
            return redirect(url_for("puzzle"))
        # Check booleans
        elif type(solution) == bool and solution is True and response not in true_values:
            return redirect(url_for("puzzle"))
        elif type(solution) == bool and solution is False and response not in false_values:
            return redirect(url_for("puzzle"))
    # Catch any errors
    except AttributeError:
        return redirect(url_for("puzzle"))
    except ValueError:
        return redirect(url_for("puzzle"))

    # Update puzzle completions
    Puzzles.update(player[2])

    # Update player's puzzle completions
    UserData.update(cookie[0], complete=player[3] + 1)
    player = UserData.query(cookie[0])

    # Check if finished
    if json.loads(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] == POSSIBLE_COMPLETED:
        # Set end time & redirect to end page
        UserData.update(cookie[0], time_end=int(time()))
        return redirect(url_for("finish"))

    # Check if value mismatch
    elif (json.loads(player[1])[POSSIBLE_COMPLETED - 1] != player[2] and player[3] == POSSIBLE_COMPLETED) \
            or (json.loads(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] != POSSIBLE_COMPLETED):
        # Update tampered value
        UserData.update(cookie[0], tampered=1)

        if player[3] >= POSSIBLE_COMPLETED:
            # Set end time & redirect to end page
            UserData.update(cookie[0], time_end=int(time()))
            return redirect(url_for("finish"))

    # Update player's current puzzle
    curr_puzzle = json.loads(player[1])[json.loads(player[1]).index(player[2]) + 1]
    UserData.update(cookie[0], current=curr_puzzle)

    # Redirect to next puzzle
    return redirect(url_for("puzzle"))


if __name__ == "__main__":
    app.run(host=ADDRESS, port=PORT, debug=DEBUG)
