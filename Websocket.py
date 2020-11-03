from flask import *

app = Flask(__name__)


@app.route('/')
def hello_world():
    return render_template("sock.html")


if __name__ == '__main__':
    app.run(host="0.0.0.0",port=80,debug=True)
