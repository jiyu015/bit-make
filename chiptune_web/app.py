import sys
import os
from flask import Flask

# appを定義
app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>Chiptune Converter is Online</h1>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
