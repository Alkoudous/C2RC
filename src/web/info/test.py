from flask import Flask
app = Flask('CivCleaner')


@app.route('/')
def get_data():
    return 'Hello, World !z!'

