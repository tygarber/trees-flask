from flask import Flask, render_template, request, make_response
from core import graphing
from config import google_maps_api_token, noaa_api_token

app = Flask(__name__)


@app.route('/')
def main():

    return render_template('index.html', stations=graphing.pull_stations(noaa_api_token), google_maps_api_token=google_maps_api_token)

@app.route('/graph.png')
def graph():
    station_id = request.args.get('station_id')
    graph = graphing.generate_graph(station_id, noaa_api_token)

    response = make_response(graph.getvalue())
    response.headers['Content-Type'] = 'image/png'

    return response


if __name__ == '__main__':
    app.run()
