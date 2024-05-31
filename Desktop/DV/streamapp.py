import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px

# Title
st.title("Violent Crime Rate in California")

# Load Dataset
@st.cache_data
def load_data():
    file_path = r'C:\Users\ankit\Downloads\trimmed_crime_data.xlsx'
    data = pd.read_excel(file_path)
    return data

data = load_data()

# Filter year
years = sorted(data['reportyear'].unique())
selected_year = st.selectbox("Select Year", years)

# Filter data for the selected year
data_selected = data[data['reportyear'] == selected_year]

# Select necessary columns
columns_to_keep = ['reportyear', 'county_name', 'rate']
data_selected = data_selected[columns_to_keep]

# Handle NaN values
data_selected = data_selected.dropna(subset=['rate'])

# Load California GeoJSON data
@st.cache_data
def load_geojson():
    geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/california-counties.geojson"
    geojson_data = gpd.read_file(geojson_url)
    return geojson_data

geojson_data = load_geojson()

# Merge crime data with GeoJSON
merged_data = geojson_data.merge(data_selected, left_on='name', right_on='county_name')

# Simplify geometry to reduce size
merged_data['geometry'] = merged_data['geometry'].simplify(tolerance=0.01)

# Define the color scale
color_scale = px.colors.sequential.OrRd

# Find the minimum and maximum rates
min_rate = merged_data['rate'].min()
max_rate = merged_data['rate'].max()

# Apply color mapping
# Apply color mapping
merged_data['color'] = merged_data['rate'].apply(lambda x: px.colors.sample_colorscale(color_scale, (x - min_rate) / (max_rate - min_rate))[0])
# merged_data['color'] = merged_data['rate'].apply(lambda x: px.colors.sample_colorscale(color_scale, x / max_rate)[0])

# Create Heatmap
fig = px.choropleth_mapbox(
    merged_data,
    geojson=merged_data.geometry,
    locations=merged_data.index,
    color='color',
    mapbox_style="carto-positron",
    zoom=4.5,
    center={"lat": 37.0, "lon": -120.0},
    opacity=0.6,
    labels={'color': 'Crime Rate'},
    title=f"Violent Crime Rate in California ({selected_year})",
    hover_name='name',
    hover_data=['rate']
)
fig.update_geos(fitbounds="locations")
fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0}, coloraxis_showscale=False)  # Adjust top margin for title, remove color scale
st.plotly_chart(fig)

# Display minimum and maximum rates
st.write(f"Minimum Rate: {min_rate:.2f}")
st.write(f"Maximum Rate: {max_rate:.2f}")