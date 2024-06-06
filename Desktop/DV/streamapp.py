import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objs as go
from matplotlib.colors import LinearSegmentedColormap, to_hex
import requests
from io import BytesIO
import json
from streamlit_chat import message

# Title
st.title("Violent Crime Rate in California")

# Create tabs
tab1, tab2 , tab3= st.tabs(["Heatmap", "Crime Rate Over Time", "CalCrime Bot"])

# Load Dataset
@st.cache_data
def load_data():
    file_path = r'/Users/aishwaryagupta/Downloads/scu-dataviz-main/DV/crime_dataset.csv'
    data = pd.read_csv(file_path)
    return data

data = load_data()

with tab1:
    # Filter year
    years = sorted(data['reportyear'].unique())
    selected_year = st.selectbox("Select Year", years)

    # Filter data for the selected year
    data_selected = data[(data['reportyear'] == selected_year) & (data['strata_level_name'] == 'Violent crime total')]

    # Select necessary columns
    columns_to_keep = ['reportyear', 'geoname', 'rate', 'numerator']
    data_selected = data_selected[columns_to_keep]

    # Handle NaN values
    data_selected = data_selected.dropna(subset=['rate'])

    # Convert rate to numeric
    data_selected['rate'] = pd.to_numeric(data_selected['rate'], errors='coerce')

    # Handle NaN values after conversion
    data_selected = data_selected.dropna(subset=['rate'])

    # Load California GeoJSON data
    @st.cache_data
    def load_geojson():
        geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/california-counties.geojson"
        geojson_data = gpd.read_file("california-counties.geojson")
        print("GeoJSON loaded:", geojson_data.head()) 
        return geojson_data

    geojson_data = load_geojson()

    # Merge crime data with GeoJSON
    merged_data = geojson_data.merge(data_selected, left_on='name', right_on='geoname')

    # Simplify geometry to reduce size
    merged_data['geometry'] = merged_data['geometry'].simplify(tolerance=0.01)

    # Define the custom color scale using LinearSegmentedColormap
    color_scale = LinearSegmentedColormap.from_list("custom_scale", ["white", "lightgrey", "grey", "darkred"])

    # Find the minimum and maximum rates
    min_rate = merged_data['rate'].min()
    max_rate = merged_data['rate'].max()

    # Apply color mapping
    def get_color(value, min_val, max_val):
        norm_value = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
        return to_hex(color_scale(norm_value))

    merged_data['color'] = merged_data['rate'].apply(lambda x: get_color(x, min_rate, max_rate))

    # Get detailed crime statistics for hover information
    def get_crime_details(row):
        violent_crime_total = row['numerator']
        agg_assault = data[(data['reportyear'] == selected_year) & (data['geoname'] == row['geoname']) & (data['strata_level_name'] == 'Aggravated assault')]['numerator'].values[0]
        forcible_rape = data[(data['reportyear'] == selected_year) & (data['geoname'] == row['geoname']) & (data['strata_level_name'] == 'Forcible rape')]['numerator'].values[0]
        murder_manslaughter = data[(data['reportyear'] == selected_year) & (data['geoname'] == row['geoname']) & (data['strata_level_name'] == 'Murder and non-negligent manslaughter')]['numerator'].values[0]
        robbery = data[(data['reportyear'] == selected_year) & (data['geoname'] == row['geoname']) & (data['strata_level_name'] == 'Robbery')]['numerator'].values[0]
        return f"""
        Total Violent Crime: {violent_crime_total}<br>
        Aggravated assault: {agg_assault}<br>
        Forcible Rape: {forcible_rape}<br>
        Murder and Manslaughter: {murder_manslaughter}<br>
        Robbery: {robbery}
        """

    merged_data['crime_details'] = merged_data.apply(get_crime_details, axis=1)

    # Create Heatmap
    fig = go.Figure(go.Choroplethmapbox(
        geojson=merged_data.geometry.__geo_interface__,
        locations=merged_data.index,
        z=merged_data['rate'],
        colorscale="Reds",
        marker_opacity=0.6,
        marker_line_width=0,
        text=merged_data['crime_details'],  # hover text
        hoverinfo='text'
    ))

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=4.5,
        mapbox_center={"lat": 37.0, "lon": -120.0},
        margin={"r":0,"t":30,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title="Crime Rate"
        )
    )
    st.plotly_chart(fig)

with tab2:
    st.header("Crime Rate Over Time")

    # Get list of counties
    counties = sorted(data['geoname'].unique())
    selected_county = st.selectbox("Select County", counties, index=counties.index("Santa Clara"), key='selected_county')

    # Filter data for 'Violent crime total'
    data_total = data[data['strata_level_name'] == 'Violent crime total']
    
    # Function to create the initial chart
    def create_chart(county):
        data_county = data_total[data_total['geoname'] == county]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=data_county['reportyear'], y=data_county['rate'], mode='lines', line=dict(color='magenta')))
        fig2.update_layout(
            title=f"Crime Rate in {county} County",
            xaxis=dict(tickmode='linear', tick0=2000, dtick=1, range=[2000, 2013]),
            yaxis=dict(title='Crime Rate'),
            transition={'duration': 300}
        )
        return fig2

    # Initial chart rendering
    fig2 = create_chart(selected_county)
    chart = st.plotly_chart(fig2, use_container_width=True)

    # Function to update the chart
    def update_chart():
        county = st.session_state.selected_county
        fig2 = create_chart(county)
        chart.plotly_chart(fig2, use_container_width=True)
    
    # Update the chart on selection change
    update_chart()

with tab3:
    st.header("CalCrime Bot")

    API_URL = "http://127.0.0.1:5002/ask"
    headers = {'Content-Type': 'application/json'}


    if 'generated' not in st.session_state:
        st.session_state['generated'] = []

    if 'past' not in st.session_state:
        st.session_state['past'] = []

    def query(payload):
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        return response.text

    def get_text():
        input_text = st.text_input("You: ","Ask Questions about Crime in California", key="input")
        return input_text 


    user_input = get_text()
    if user_input:
        output = query({
            "prompt": user_input
        }) 
        print(output)
        st.session_state.past.append(user_input)
        st.session_state.generated.append(output)

    if st.session_state['generated']:

        for i in range(len(st.session_state['generated'])-1, -1, -1):
            message(st.session_state["generated"][i], key=str(i))
            message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')


