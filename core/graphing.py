import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import datetime as dt
import numpy as np
import pandas as pd
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


#chill function
def FunChill(temp, aC = 3.13, bC=10, cC=10.93, dC=2.10, eC = 3.10):
    try:
        chill = aC * (((temp + bC)/cC)**dC) * np.exp(-(((temp + bC)/cC)**eC))
    except:
        chill = np.nan
    if chill > 1:
        chill = 1
    if (temp <= -20 or temp >= 16):
        chill = 0
    return chill

#force function
def FunForce(temp, aF = 4.49, bF = -0.63):
    force = 1 / (1 + np.exp(aF + bF*temp))
    return force

def plot_model(model, x_range, color='green'):
    """
    This function graphs a model
    """
    x = np.array(x_range)
    y = model(x)
    return x, y

def pull_stations(token):
    """
    This function pulls a list of NOAA weather stations situated in the northwest
    """
    current_date = dt.datetime.now()
    # test which november to start on
    if current_date.month >= 11:
        # if month is november or december the year should be the same year
        start_date = '{year}-11-01'.format(year=current_date.year)
    else:
        # if not take the previous november
        start_date = '{year}-11-01'.format(year=current_date.year - 1)

    url = 'https://www.ncdc.noaa.gov/cdo-web/api/v2/stations?datasetid=GHCND&' \
          'limit=1000&' \
          'datacategoryid=TEMP&' \
          'offset=1000&' \
          'datatypeid=TAVG&'\
          'extent=42.047165,-124.378791,48.955117,-117.148889'

    #set token. this token is available by signing up on the noaa website https://www.ncdc.noaa.gov/cdo-web/token

    headers = {'token': token}

    #get a json list of stations

    try:
        http_response = requests.get(url, headers=headers)
    except:
        pass

    #dump into python list of dicts
    stations = http_response.json()

    #convert to dataframe to make sure station has data for the right time period
    stations_df = pd.DataFrame(stations['results'])

    #filter stations that only have temp data in the correct range then convert back to dictionary
    stations_dict = stations_df[stations_df['maxdate'] >= start_date].T.to_dict().values()

    return stations_dict


def get_weather_data(station_id, token, start_date, end_date, offset):
    #api noaa token can be found here:
    #https://www.ncdc.noaa.gov/cdo-web/token
    noaa_token = token #'zYKUphEjBWILVGlSxQOHxzGFRFNKaQdj'
    #this url provides a list of stations
    #url = 'https://www.ncdc.noaa.gov/cdo-web/api/v2/stations?datasetid=GHCND&limit=1000&datacategoryid=TEMP&offset=1000&extent=42.047165,-124.378791,48.955117,-117.148889'
    url = 'http://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=GHCND'\
          '&datacategoryid=TEMP'\
          '&stationid={}'\
          '&startdate={}'\
          '&enddate={}'\
          '&offset={}'\
          '&limit=1000'.format(station_id, start_date, end_date, offset)
    # token as required by NOAA feed, you have to register for this
    headers = {'token': token}
    #send query string and header payload
    http_response = requests.get(url, headers = headers)
    #dump json into python dictionary
    return http_response.json()



def generate_graph(station_id, token):
    """
    This function pulls temperature data down from selected noaa station and generates
    forceing days and chilling days graph with model
    """

    current_date = dt.datetime.now()
    # test which november to start on
    if current_date.month >= 11:
        # if month is november or december the year should be the same year
        start_date = '{year}-11-01'.format(year=current_date.year)
    else:
        # if not take the previous november
        start_date = '{year}-11-01'.format(year=current_date.year - 1)
    end_date = current_date.strftime('%Y-%m-%d')

    # loop to pull entire weather data set, NOAA api only allows 1000 rows at a time
    offset = 0
    # some insurance if the weatherset isn't complete
    data = pd.DataFrame()


    while True:
        print(offset)
        weather_data = get_weather_data(station_id, token, start_date, end_date, offset)
        #if no data exit the loop
        if not weather_data:
            break
        last_weather_date = dt.datetime.strptime(weather_data['results'][-1]['date'], '%Y-%m-%dT%H:%M:%S').date()
        # increment by 1000 records
        offset += 1000
        # check if current date is available in the dataset, if it is append it to a dataframe
        # if not stay in the loop
        if last_weather_date == current_date.date():
            break
        # appends dataframe
        data = data.append(pd.DataFrame(weather_data['results']))

    # filter results down to daily average
    data = data[data['datatype'].isin(['TMAX', 'TMIN'])]

    # pivot
    data = data[['date', 'datatype', 'value']]
    data = data.pivot(index='date', columns='datatype', values='value').reset_index().rename_axis(None, 1)

    # create column with average temperature
    data['value'] = (data['TMAX'] + data['TMIN']) / 2

    # temperature data from feed given in 10ths degrees C, divide by 10 to give whole degrees
    data['value'] = data['value'] / 10

    # apply the chill function and force function to the temperate
    data['FunChill'] = data['value'].apply(FunChill)
    data['FunForce'] = data['value'].apply(FunForce)

    # cumulative sum for the calculated chill and force columns
    data['FunChill.cumsum'] = data['FunChill'].cumsum()
    data['Force.cumsum'] = data['FunForce'].cumsum()

    #create series related to the model, and confidence intervals
    model_x, model_y = plot_model(lambda x: 114.4-(0.776 * x), range(0, 140))
    model_conhigh_x, model_conhigh_y = plot_model(lambda x: 121.67 - (0.776 * x), range(0, 140))
    model_conlow_x, model_conlow_y = plot_model(lambda x: 107.13 - (0.776 * x), range(0, 140))

    #import seaborn styling
    sns.set_style("darkgrid")

    #create matplotlib figure with one axis
    fig, ax = plt.subplots(figsize=(6, 6))

    #plot the chill, forcing days
    ax.plot(data['FunChill.cumsum'], data['Force.cumsum'], alpha=0.4)

    #plot the model
    ax.plot(model_x, model_y, alpha=0.4)

    #plot confidence intervals
    ax.plot(model_conhigh_x, model_conhigh_y, alpha=0.4, linestyle='--', color='black')
    ax.plot(model_conlow_x, model_conlow_y, alpha=0.4, linestyle='--', color='black')

    #label axes
    ax.set_xlabel('Chilling days', fontsize=16)
    ax.set_ylabel('Forcing days', fontsize=16)
    ax.set_title('Chilling and forcing accumulations from {} through {}'.format(start_date, end_date), fontsize=12)

    #convert to binary to serve to webpage
    canvas = FigureCanvas(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)

    return png_output




