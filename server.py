from flask import Flask, make_response, request, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from os import urandom
from binascii import hexlify
from random import choice as choose_random, shuffle as shuffle_list
from time import time, strftime as format_time
from hashlib import sha512 as sha512_encode
from json import loads as load_json, dumps as export_json
from requests import post, patch

##### Begin Options #####
TO = "test@test.com"
FROM = "Game Info <test@test.com>"
MG_APIKEY = "key"
GH_API = "username:key"
GH_ID = "id"
POSSIBLE_COMPLETED = 4
ADDRESS = "127.0.0.1"
PORT = 5000
DEBUG = False
TESTING = False
DEV = ""
DOMAIN = "test.com"
DATABASE_HOST = "ip"
DATABASE_PORT = "port"
DATABASE_USER = "username"
DATABASE_PASS = "password"
DATABASE_DATABASE = "game"
DATABASE_OPTIONS = ""
##### End Options #####

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://" + DATABASE_USER + ":" + DATABASE_PASS + "@" + DATABASE_HOST + ":" + DATABASE_PORT + "/" + DATABASE_DATABASE + "?" + DATABASE_OPTIONS
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
STATISTICS = {"Players": 0, "Completions": 0, "Tamper Attempts": 0,
              "Finishers": [], "Highscore": ["Alex Krantz", 168], "Tamperers": []}


# Name: Finishers
# Purpose: access finishers table
class Finishers(db.Model):
    # Define columns
    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(128), nullable=False)


# Name: Puzzles
# Purpose: access puzzles table
class Puzzles(db.Model):
    # Define columns
    id = db.Column(db.String(32), primary_key=True)
    completions = db.Column(db.Integer, nullable=False, default=0)
    solution = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(64), nullable=False)
    prompt = db.Column(db.Text, nullable=False)


# Name: UserData
# Purpose: access user_data table
class UserData(db.Model):
    # Define columns
    id = db.Column(db.String(32), primary_key=True)
    pages = db.Column(db.Text, nullable=False)
    current = db.Column(db.String(32), nullable=False)
    complete = db.Column(db.Integer, nullable=False, default=0)
    start = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False, default=0)
    tampered = db.Column(db.Integer, nullable=False, default=0)


# Name: Send
# Purpose: send emails to specified address
class Send(object):
    # Name: stats
    # Purpose: send the game statistics
    # Inputs:
    # Outputs: dict
    @staticmethod
    def stats():
        # Format finishers
        finishers = "# Finishers\n###### Updated On: " + format_time("%m-%d-%Y %H:%M:%S") + \
                    "\n\nNumber | Name | Email | Time\n------ | ---- | ----- | ----\n"
        for i, finisher in enumerate(STATISTICS["Finishers"]):
            finishers += str(i + 1) + " | "
            finishers += finisher["name"] + " | "
            finishers += finisher["email"] + " | "
            finishers += str(finisher["time"]) + "\n"

        # Format tamperers
        tamperers = "# Tamperers\n###### Updated On: " + format_time("%m-%d-%Y %H:%M:%S") + \
                    "\n\nNumber | Name | Email\n------ | ---- | -----\n"
        for i, tamperer in enumerate(STATISTICS["Tamperers"]):
            tamperers += str(i + 1) + " | "
            tamperers += tamperer["name"] + " | "
            tamperers += tamperer["email"] + "\n"

        generic = "# Generic Stats\n###### Updated on: " + format_time("%m-%d-%Y %H:%M:%S") + \
            "\n\nTotal Players: " + str(STATISTICS["Players"]) + \
            "\n\nTotal Completions: " + str(STATISTICS["Completions"]) + \
            "\n\nAttempted Tampers: " + str(STATISTICS["Tamper Attempts"]) + \
            "\n\nHighscore Holder:\n* Name: " + STATISTICS["Highscore"][0] + \
            "\n* Time: " + str(STATISTICS["Highscore"][1]) + " seconds\n"

        data = {
            "description": "Krantz's Challenge Play Statistics",
            "files": {
                "generic.md": {
                    "content": generic
                },
                "finishers.md": {
                    "content": finishers
                },
                "tamperers.md": {
                    "content": tamperers
                }
            }
        }

        return data

    # Name: finisher
    # Purpose: send stats of new finisher
    # Inputs: hs as boolean
    # Outputs: status code
    @staticmethod
    def finisher(player, hs=False):
        # Get puzzles
        puzzles = ""
        for i, p in enumerate(load_json(player[1])):
            puzzles += "\t\t" + str(i + 1) + ": " + p + "\n"

        body = "New Finisher on " + format_time("%m-%d-%Y %H:%M:%S") + \
            ":\n\tName: " + STATISTICS["Finishers"][len(STATISTICS["Finishers"]) - 1]["name"] + ",\n" + \
            "\tEmail: " + STATISTICS["Finishers"][len(STATISTICS["Finishers"]) - 1]["email"] + ",\n" + \
            "\tTime: " + str(STATISTICS["Finishers"][len(STATISTICS["Finishers"]) - 1]["time"]) + " seconds\n" + \
            "\tAssigned Puzzles: " + puzzles

        if hs:
            body += "New Highscore! Contact them & give them their reward."

        a = ("api", MG_APIKEY)
        d = {"from": FROM,
             "to": TO,
             "subject": "Krantz's Challenge: New Finisher",
             "text": body
             }
        return post("https://api.mailgun.net/v3/" + DOMAIN + "/messages", auth=a, data=d)

    # Name: tamperer
    # Purpose: send stats of new tamperer
    # Inputs:
    # Outputs: status code
    @staticmethod
    def tamperer():
        body = "New Tamperer on " + format_time("%m-%d-%Y %H:%M:%S") + \
            ":\n\tName: " + STATISTICS["Tamperers"][len(STATISTICS["Tamperers"]) - 1]["name"] + ",\n" + \
            "\tEmail: " + STATISTICS["Tamperers"][len(STATISTICS["Tamperers"]) - 1]["email"] + ",\n" + \
            "Contact this person to find out the bug."
        a = ("api", MG_APIKEY)
        d = {"from": FROM,
             "to": TO,
             "subject": "Krantz's Challenge: New Tamperer",
             "text": body
             }
        return post("https://api.mailgun.net/v3/" + DOMAIN + "/messages", auth=a, data=d)


# Name: gen_puzzles
# Purpose: generate a set of puzzles
# Inputs:
# Outputs: list of puzzle ids
def gen_puzzles():
    all_ids = [puzzle.id for puzzle in Puzzles.query.all()]
    pids = []

    while len(pids) != POSSIBLE_COMPLETED:
        pid = choose_random(all_ids)
        if pid not in pids:
            pids.append(pid)
        shuffle_list(all_ids)

    return pids


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
    # Post play statistics
    patch("https://api.github.com/gists/" + GH_ID,
                json=Send.stats(), auth=tuple(GH_API.split(":")))

    # Verify uid not tampered w/
    if sha512_encode(cookie[0].encode()).hexdigest() != cookie[1]:
        return False

    # Verify uid matches on in database
    if not UserData.query.filter_by(id=cookie[0]).first():
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
    pids = gen_puzzles()

    # Set start time
    time_start = int(time())

    # Set current puzzle to first puzzle in pages list
    c_pid = pids[0]

    # Save to database
    user = UserData(id=uid, pages=export_json(pids), current=c_pid, start=time_start)
    db.session.add(user)
    db.session.commit()

    # Return string to go in cookie
    return uid + "." + sha512_encode(uid.encode()).hexdigest()


# Name: index
# Purpose: listen for get requests, redirect to home
# Inputs:
# Outputs: redirect
@app.route("/")
def index():
    return redirect(url_for("home"))


# Name: home
# Purpose: listen for get requests, render main page
# Inputs:
# Outputs: rendered html
@app.route("/home")
def home():
    return render_template("index" + DEV + ".html", name=STATISTICS["Highscore"][0], time=STATISTICS["Highscore"][1])


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

            resp = make_response(render_template("tamperer" + DEV + ".html"))
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
        return render_template("tamperer" + DEV + ".html")

    # Get cookie data
    cookie = get_data_from_cookie()
    played = request.cookies.get("pstatus")

    # Validate data
    if not verify_data(cookie):
        # Update tamper statistics
        STATISTICS["Tamper Attempts"] += 1

        # Remove data cookie
        resp = make_response(render_template("tamperer" + DEV + ".html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    if request.method == "GET":
        c = Finishers.query.filter_by(id=cookie[0]).first()
        u = UserData.query.filter_by(id=cookie[0]).first()
        if u.complete != POSSIBLE_COMPLETED:
            return redirect(url_for("puzzle"))

        if c:
            return render_template("finish" + DEV + ".html", name=c.name, time=c.time)

        return render_template("pre-finish" + DEV + ".html")

    # Get form data
    name = request.form.get("name")
    email = request.form.get("email")

    # Insert into finishers database
    player = UserData.query.filter_by(id=cookie[0]).first
    if player.tampered != 1:
        finisher = Finishers(id=cookie[0], name=name, email=email, time=(player.end - player.start))
        db.session.add(finisher)
        db.session.commit()

    # Update completions & finishers
    STATISTICS["Completions"] += 1
    STATISTICS["Finishers"].append({"name": name, "email": email, "time": (player.end - player.start)})

    # Check if user got highscore
    prev = None
    if STATISTICS["Highscore"][1] > (player.end-player.start):
        prev = STATISTICS["Highscore"]
        STATISTICS["Highscore"] = [name, (player.end-player.start)]

    # Check if tampered
    if player.tampered == 1:
        # Remove from completions,finishers,highscore & add to tamperers
        STATISTICS["Completions"] -= 1
        STATISTICS["Tamperers"].append(STATISTICS["Finishers"].pop(len(STATISTICS["Finishers"]) - 1))
        if STATISTICS["Highscore"][0] == name:
            STATISTICS["Highscore"] = prev

        # Notify new Tamperer
        Send.tamperer()

        # Load tamper data
        tamper = [POSSIBLE_COMPLETED, player.complete, load_json(player.pages).index(player.current) + 1]

        # Render 'finish'
        resp = make_response(render_template("finish" + DEV + ".html", name=name,
                                             time=(player.end - player.start), tamperer=tamper))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Check if already played
    if played:
        # Check if has highscore
        if STATISTICS["Highscore"][0] == name:
            # Notify new highscore
            Send.finisher(player, True)

            resp = make_response(render_template("finish" + DEV + ".html", name=name, time=(player.end - player.start),
                                                 played=played, hs=[prev[1], (prev[1] - (player.end-player.start))]))
            resp.set_cookie("data", "", expires=0)
            return resp

        # Notify new finisher
        Send.finisher(player)

        # Return basic played finish
        resp = make_response(render_template("finish" + DEV + ".html", name=name,
                                             time=(player.end - player.start), played=played))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Check if user got highscore
    if STATISTICS["Highscore"][0] == name:
        # Notify new highscore
        Send.finisher(player, True)

        resp = make_response(render_template("finish" + DEV + ".html", name=name, time=(player.end - player.start),
                                             hs=[prev[1], (prev[1] - (player.end-player.start))]))
        resp.set_cookie("pstatus", "1", expires=(time() + 316000000))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Notify new finisher
    Send.finisher(player)

    # Render finish
    resp = make_response(render_template("finish" + DEV + ".html", name=name, time=(player.end - player.start)))
    resp.set_cookie("pstatus", "1", expires=(time() + 316000000))
    resp.set_cookie("data", "", expires=0)
    return resp


# Name: puzzle
# Purpose: listen for get requests, view a given puzzle
# Inputs:
# Outputs: rendered html
@app.route("/puzzle")
def puzzle():
    # Check user has started
    if not request.cookies.get("data"):
        return render_template("tamperer" + DEV + ".html")

    # Get cookie data
    cookie = get_data_from_cookie()

    # Validate data
    if not verify_data(cookie):
        # Update tamper statistics
        STATISTICS["Tamper Attempts"] += 1

        # Remove data cookie
        resp = make_response(render_template("tamperer" + DEV + ".html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Select & return current puzzle's html
    player = UserData.query.filter_by(id=cookie[0]).first()
    data = Puzzles.query.filter_by(id=player.current).first()
    return render_template("puzzle" + DEV + ".html", title=data.title, prompt=data.prompt,
                           number=load_json(player.pages).index(player.current) + 1)


# Name: check
# Purpose: listen for get & post requests, check answer for puzzle
# Inputs:
# Outputs: redirection
@app.route("/check", methods=["GET", "POST"])
def check():
    # Check if user has started
    if not request.cookies.get("data"):
        return render_template("tamperer" + DEV + ".html")

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
        resp = make_response(render_template("tamperer" + DEV + ".html"))
        resp.set_cookie("data", "", expires=0)
        return resp

    # Get other data
    player = UserData.query.filter_by(id=cookie[0]).first()
    solution = Puzzles.query.filter_by(id=player.current).first()
    response = request.form.get("response")

    # Check if testing
    if TESTING and response == "override":
        # Update player's puzzle completions
        UserData.update(cookie[0], complete=player[3] + 1)
        player = UserData.query(cookie[0])

        # Check if finished
        if load_json(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] == POSSIBLE_COMPLETED:
            # Set end time & redirect to end page
            UserData.update(cookie[0], time_end=int(time()))
            return redirect(url_for("finish"))

        # Update player's current puzzle
        curr_puzzle = load_json(player[1])[load_json(player[1]).index(player[2]) + 1]
        UserData.update(cookie[0], current=curr_puzzle)

        # Redirect to new puzzle
        return redirect(url_for("puzzle"))

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

    # Check if value mismatch
    if (load_json(player[1])[POSSIBLE_COMPLETED - 1] != player[2] and player[3] == POSSIBLE_COMPLETED) \
            or (load_json(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] != POSSIBLE_COMPLETED):
        # Update tampered value
        UserData.update(cookie[0], tampered=1)

        if player[3] >= POSSIBLE_COMPLETED:
            # Set end time & redirect to end page
            UserData.update(cookie[0], time_end=int(time()))
            return redirect(url_for("finish"))

    # Check if finished
    elif load_json(player[1])[POSSIBLE_COMPLETED - 1] == player[2] and player[3] == POSSIBLE_COMPLETED:
        # Set end time & redirect to end page
        UserData.update(cookie[0], time_end=int(time()))
        return redirect(url_for("finish"))

    # Update player's current puzzle
    curr_puzzle = load_json(player[1])[load_json(player[1]).index(player[2]) + 1]
    UserData.update(cookie[0], current=curr_puzzle)

    # Redirect to next puzzle
    return redirect(url_for("puzzle"))


# Name: page
# Purpose: listen for get requests, handle 404 errors
# Inputs:
# Outputs: rendered html
@app.route("/<path:path>")
def page(path):
    return render_template("404" + DEV + ".html", page=path)


if __name__ == "__main__":
    # Run main app
    app.run(host=ADDRESS, port=PORT, debug=DEBUG)
