import os

import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import altair as alt
import geopandas as gpd
import pandas as pd
from datetime import datetime, date

import json

import plotly.express as px

# As there is only 1 callback function allowed to map to each output,
# we use this to check which value got updated and updating the plots
# accordingly
def is_updated(key, new_value):
    return ((prev_vals[key] is None and new_value is not None)
        or (prev_vals[key] is not None and prev_vals[key] != new_value))

def calculate_continent_daywise(countries_daywise_df):
    return calculate_continent_statistics(countries_daywise_df, 'Date')

def calculate_continent_statistics(countries_df, group_col):
    continents_df = countries_df.drop(drop_cols, axis=1).groupby([group_col, 'WHO Region']).agg('mean').reset_index()
    continents_df['Country/Region'] = 'All'
    continents_df['Population'] = population_data['Population'].sum()

    return continents_df

def calculate_world_daywise(countries_daywise_df):
    return calculate_world_statistics(countries_daywise_df, 'Date')

def calculate_world_statistics(countries_df, group_col):
    world_df = countries_df.drop(drop_cols, axis=1).groupby(group_col).agg('mean').reset_index()
    world_df['Country/Region'] = 'All'
    world_df['WHO Region'] = 'All'
    world_df['Population'] = population_data['Population'].sum()

    return world_df

def generate_map(data):
    return px.choropleth(data, locations="country_code",
                    color="Confirmed",
                    hover_name="Country/Region",
                    color_continuous_scale='Reds')

def load_daily_data():
    return pd.read_csv(os.path.join('data', 'raw', 'full_grouped.csv'))

def load_population_data():
    return  pd.read_csv(os.path.join('data', 'raw', 'worldometer_data.csv'),
        usecols = ['Country/Region','Population'])

def load_country_code_data():
    shapefile = os.path.join('data', 'ne_110m_admin_0_countries.shp')

    gdf = gpd.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
    gdf.columns = ['country', 'country_code', 'geometry']

    return gdf

def join_population_data(daily_data, population_data):
    return daily_data.merge(population_data, how = 'left', on = 'Country/Region')

def join_country_code_data(daily_data, country_code_data):
    #new columns: country, country_code, geometry
    return country_code_data.merge(daily_data, left_on = 'country', right_on = 'Country/Region').drop(['country'], axis=1)

alt.data_transformers.disable_max_rows()

prev_vals = {'country': None, 'continent': None}
drop_cols = ['Country/Region', 'Population', 'country_code', 'geometry']

metrics = {
    'Population': 'first',
    'Confirmed': 'mean',
    'Deaths': 'mean',
    'Recovered': 'mean',
    'Active': 'mean',
    'New cases': 'mean',
    'New deaths': 'mean',
    'New recovered': 'mean',
    'WHO Region': 'first'
}

month_data = load_daily_data()
population_data = load_population_data()
country_code_data = load_country_code_data()

countries_daywise_df = join_population_data(month_data, population_data)
countries_daywise_df = join_country_code_data(countries_daywise_df, country_code_data)

continents_daywise_df = calculate_continent_daywise(countries_daywise_df)
world_daywise_df = calculate_world_daywise(countries_daywise_df)

countries = ['All'] + list(set(countries_daywise_df['Country/Region'].tolist()))
continents = ['All'] + list(set(countries_daywise_df['WHO Region'].tolist()))
countries.sort()
continents.sort()

continent_selection = html.Label([
    'Continent Selection',
    dcc.Dropdown(
        id='continent_filter',
        value='All',  # REQUIRED to show the plot on the first page load
        options=[{'label': continent, 'value': continent} for continent in continents])
])

country_selection = html.Label([
    'Country Selection',
    dcc.Dropdown(
        id='country_filter',
        value='All',  # REQUIRED to show the plot on the first page load
        options=[{'label': country, 'value': country} for country in countries])
])

date_range_selection = html.Label([
    'Date range selection',
    dcc.DatePickerRange(
        id='date_selection_range',
        min_date_allowed=date(2020, 1, 22),
        max_date_allowed=date(2020, 7, 27),
        initial_visible_month=date(2020, 1, 22),
        start_date=date(2020, 1, 22),
        end_date=date(2020, 7, 27)
    )
])

total_cases_linechart = html.Iframe(
    id='line_totalcases',
    style={'border-width': '0', 'width': '100%', 'height': '500px'}
)

total_death_linechart = html.Iframe(
    id='line_totaldeaths',
    style={'border-width': '0', 'width': '100%', 'height': '500px'}
)

total_recovered_linechart = html.Iframe(
    id='line_totalrecovered',
    style={'border-width': '0', 'width': '100%', 'height': '500px'}
)

map = dcc.Graph(
    id='world_map',
    figure=generate_map(countries_daywise_df)
)
                                
# Setup app and layout/frontend
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1('COVID-19'),
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    continent_selection
                    ])]),
            dbc.Row([
                dbc.Col([
                    country_selection
                    ])]),
            dbc.Row([
                dbc.Col([
                    date_range_selection
                ])
            ])],
            md=4),
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    map
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    total_cases_linechart
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    total_death_linechart
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    total_recovered_linechart
                ])
            ])],
            md=8)
        ])])

# Set up callbacks/backend
@app.callback(
    Output('line_totalcases', 'srcDoc'),
    Output('line_totaldeaths', 'srcDoc'),
    Output('line_totalrecovered', 'srcDoc'),
    Output('world_map', 'figure'),
    Input('country_filter', 'value'),
    Input('continent_filter', 'value'),
    Input('date_selection_range', 'start_date'),
    Input('date_selection_range', 'end_date'))
def filter_plot(country, continent, start_date, end_date):
    data = world_daywise_df
    plot_data = countries_daywise_df

    if is_updated('continent', continent):
        prev_vals['continent'] = continent
        if continent != 'All':
            data = continents_daywise_df[continents_daywise_df['WHO Region'] == continent]
            plot_data = countries_daywise_df[countries_daywise_df['WHO Region'] == continent]
    elif is_updated('country', country):
        prev_vals['country'] = country
        if country != 'All':
            data = countries_daywise_df[countries_daywise_df['Country/Region'] == country]
            plot_data = data
    
    data = data.query('Date >= @start_date & Date <= @end_date')
    plot_data = plot_data.query('Date >= @start_date & Date <= @end_date')

    print("Plot data shape is:", plot_data.shape)

    # fix error when groupby geometry or put it in the aggregate column
    temp = plot_data.drop(['geometry', 'country_code', 'Date'], axis=1).groupby(['Country/Region']).agg(metrics).reset_index()
    plot_data = join_country_code_data(temp, country_code_data)

    return plot(data, 'Confirmed', 'the number of confirmed cases'), plot(data, 'Deaths', 'the number of confirmed deaths'), plot(data, 'Recovered', 'the number of recoveries'),  generate_map(plot_data)

def plot(data, metric, metric_name):
    chart = alt.Chart(data, title=f'How {metric_name} changes over time').mark_line().encode(
        x=alt.X('month(Date):T', title="Month"),
        y=alt.Y(f'mean({metric}):Q', title=f'Average of {metric_name}')) 
        
    return (chart + chart.mark_point()).interactive(bind_x=True).to_html()

if __name__ == '__main__':
    app.run_server(debug=True)