from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def homePage():
    return "Home Page :)"

@app.route("/fetch-file", methods = ["GET", "POST"])
def fetchFilePage():
    return "Fetch File :)"

@app.route("/past-paper-checker")
def pastPaperCheckerPage():
    return "Past Paper Checker Page :)"

@app.route("/past-paper-checker/submit", methods = ['POST'])
def pastPaperCheckerSubmit():
    return jsonify(
        {
            "status": "nothing"
        }
    )

@app.route("/api/grade-question", methods = ["POST"])
def apiGradeQuestion():
    return jsonify(
        {
            "status": "everything"
        }
    )

if __name__ == "__main__":
    app.run(debug=True)