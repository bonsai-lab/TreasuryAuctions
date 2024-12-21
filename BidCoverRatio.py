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




# Force reset index to ensure no conflicts
df = df.reset_index(drop=True)

# Convert columns to appropriate types
df['auction_date'] = pd.to_datetime(df['auction_date'])
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')

# Get unique security terms
security_terms = df['security_term'].unique()


fig = go.Figure()

# Add a trace for each security_term 
for i, term in enumerate(security_terms):
    filtered_df = df[df['security_term'] == term].dropna(subset=['bid_to_cover_ratio'])
    filtered_df = filtered_df.sort_values(by='auction_date')  # Use 'by' explicitly
    
    
    fig.add_trace(
        go.Scatter(
            x=filtered_df['auction_date'],
            y=filtered_df['bid_to_cover_ratio'],
            mode='lines+markers',
            name=f"{term} (Bid-to-Cover Ratio)",
            line=dict(color='white'),
            visible=(i == 0)
        )
    )
    # Add moving average trace
    filtered_df['moving_avg'] = filtered_df['bid_to_cover_ratio'].rolling(window=10).mean()
    fig.add_trace(
        go.Scatter(
            x=filtered_df['auction_date'],
            y=filtered_df['moving_avg'],
            mode='lines',
            name=f"{term} (Moving Avg)",
            line=dict(dash='dot'),
            visible=(i == 0)  
        )
    )

# Create dropdown menu
dropdown_buttons = []
for i, term in enumerate(security_terms):
    visibility = [False] * len(fig.data)
    visibility[i * 2] = True      
    visibility[i * 2 + 1] = True   
    dropdown_buttons.append(
        dict(
            label=term,
            method="update",
            args=[{"visible": visibility},
                  {"title": f"Bid-to-Cover Ratio and Moving Average for {term}"}]
        )
    )


fig.update_layout(
    updatemenus=[dict(active=0, buttons=dropdown_buttons)],
    title=f"Bid-to-Cover Ratio and Moving Average for {security_terms[0]}",
    xaxis_title="Auction Date",
    yaxis_title="Bid-to-Cover Ratio",
    template="plotly_dark",
    font_family="Bloomberg",
)

# Show the figure
fig.show()


df.index = df['auction_date']
df['auction_date'] = pd.to_datetime(df['auction_date'])
df['maturity_date'] = pd.to_datetime(df['maturity_date'])
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')

# Create a new column for the week of the auction date (using the start of the week)
df['auction_week'] = df['auction_date'].dt.to_period('W')

# Sort by maturity_date to get the correct order for the bar plot
df = df.sort_values(by='maturity_date')


print(df)


# Remove rows where 'bid_to_cover_ratio' is NaN
df = df.dropna(subset=['bid_to_cover_ratio'])

# Sort by maturity_date to get the correct order for the line plot
df = df.sort_values(by='maturity_date')


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


start_date = "2000-01-01"
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
    color_discrete_sequence=["white"], 
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
