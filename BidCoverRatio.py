import requests
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go
import ipywidgets as widgets
from ipywidgets import interactive
import datetime
import plotly.express as px



API_ENDPOINT = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"

# Parameters for filtering
params = {
    "fields": "record_date, cusip, security_type, security_term, auction_date, price_per100,maturity_date,allocation_pctage,bid_to_cover_ratio",  # Specify fields
    "sort": "-auction_date",  # Sort by auction_date descending (newest first)
    "page[number]": 1,  # Pagination - page number
    "page[size]": 5000  # Number of records per page (last 10 auctions)
}

# Make the API request
response = requests.get(API_ENDPOINT, params=params)

if response.status_code == 200:
    data = response.json()
    # Extract auction records
    records = data.get("data", [])
    # Convert to DataFrame for better readability
    df = pd.DataFrame(records)
    print(df)  
else:
    print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
    print(response.text)  # Print the error message


df.index = df['auction_date']
df['auction_date'] = pd.to_datetime(df['auction_date'])
df['maturity_date'] = pd.to_datetime(df['maturity_date'])
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')

# Create a new column for the week of the auction date (using the start of the week)
df['auction_week'] = df['auction_date'].dt.to_period('W')

# Sort by maturity_date to get the correct order for the bar plot
df = df.sort_values(by='maturity_date')

# Get the unique weeks
weeks = df['auction_week'].unique()


# Remove rows where 'bid_to_cover_ratio' is NaN
df = df.dropna(subset=['bid_to_cover_ratio'])
df['auction_date'] = pd.to_datetime(df['auction_date'])
df['maturity_date'] = pd.to_datetime(df['maturity_date'])
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')

# Create a new column for the week of the auction date (using the start of the week)
df['auction_week'] = df['auction_date'].dt.to_period('W')

# Sort by maturity_date to get the correct order for the line plot
df = df.sort_values(by='maturity_date')

# Get the unique weeks
weeks = df['auction_week'].unique()


# Select only the last 12 weeks
weeks = weeks[-12:]

# Convert periods to timestamps (start of the week)
week_start_dates = [week.start_time for week in weeks]

# Enhanced function to convert security_term to numerical values (in years)
def convert_security_term(term):
    # Regular expression to extract the number and unit (e.g., "4-Week", "1-Year 11-Months")
    term = term.replace(" ", "-")  # Normalize spaces to dashes for consistency
    matches = re.findall(r"(\d+)-([A-Za-z]+)", term)
    total_years = 0

    for value, unit in matches:
        value = float(value)
        if "Day" in unit:
            total_years += value / 365  # Convert days to years
        elif "Week" in unit:
            total_years += value / 52  # Convert weeks to years
        elif "Month" in unit:
            total_years += value / 12  # Convert months to years
        elif "Year" in unit:
            total_years += value  # Years remain as is

    return total_years


df['security_term_numeric'] = df['security_term'].apply(convert_security_term)
df = df.sort_values(by='security_term_numeric', ascending=True)
df['auction_date'] = pd.to_datetime(df['auction_date'])


start_date = "2022-01-01"
end_date = "2024-12-31"  

# Filter the DataFrame by auction date
filtered_df = df[(df['auction_date'] >= start_date) & (df['auction_date'] <= end_date)]

# Find the last auction date in the filtered data
last_auction_date = filtered_df['auction_date'].max()

# Filter for the last auction's data
last_auction_df = filtered_df[filtered_df['auction_date'] == last_auction_date]


fig = px.box(
    filtered_df,
    x="security_term",
    y="bid_to_cover_ratio",
    title=f"Bid-to-Cover Ratios by Security Term ({start_date} to {end_date})",
    labels={"security_term": "Security Term", "bid_to_cover_ratio": "Bid-to-Cover Ratio"},
)

# Add scatter points for the last auction in red
fig.add_trace(
    go.Scatter(
        x=last_auction_df['security_term'],
        y=last_auction_df['bid_to_cover_ratio'],
        mode='markers',
        marker=dict(color='red', size=10),
        name='Last Auction'
    )
)

# Customize layout
fig.update_layout(
    xaxis_title="Security Term",
    yaxis_title="Bid-to-Cover Ratio",
    xaxis_tickangle=45,
    template="plotly_dark",
    font_family="Bloomberg",
)

fig.show()
