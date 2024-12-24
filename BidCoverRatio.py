import requests
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go
import ipywidgets as widgets
from ipywidgets import interactive
import datetime
import plotly.express as px
from plotly.subplots import make_subplots



API_ENDPOINT = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"

# Parameters for filtering
params = {
    "fields": "record_date, cusip, security_type, security_term, auction_date, price_per100,maturity_date,allocation_pctage,bid_to_cover_ratio",  # Specify fields
    "sort": "-auction_date",  # Sort by auction_date descending (newest first)
    "page[number]": 1,  # Pagination - page number
    "page[size]": 10000  # Number of records per page (last 10 auctions)
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



# Function to convert security terms to years
def convert_security_term(term):
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


# Data cleaning
df['auction_date'] = pd.to_datetime(df['auction_date'], errors='coerce')
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')

# Drop rows with null values in critical columns
df.dropna(subset=['auction_date', 'bid_to_cover_ratio', 'security_term'], inplace=True)

# Convert 'security_term' to years for ordering
df['security_term_years'] = df['security_term'].apply(convert_security_term)

start_date = "2022-01-01"
end_date = "2024-12-31"

# Filter the DataFrame by auction date
filtered_df = df[(df['auction_date'] >= start_date) & (df['auction_date'] <= end_date)]

# Sort the filtered data by 'security_term_years' to ensure correct axis order
filtered_df.sort_values('security_term_years', inplace=True)

# Find the last 5 auction dates in the filtered data
last_5_auction_dates = filtered_df['auction_date'].sort_values(ascending=False).unique()[:5]

# Create the box plot
fig = px.box(
    filtered_df,
    x="security_term",
    y="bid_to_cover_ratio",
    title=f"Bid-to-Cover Ratios by Security Term ({start_date} to {end_date})",
    labels={"security_term": "Security Term", "bid_to_cover_ratio": "Bid-to-Cover Ratio"},
    color_discrete_sequence=["white"], 
)

# Add scatter points for the last 5 auctions with decreasing opacity
opacity_levels = [1.0, 0.9, 0.8, 0.7, 0.6]  # Define opacity levels for the auctions
for date, opacity in zip(last_5_auction_dates, opacity_levels):
    auction_df = filtered_df[filtered_df['auction_date'] == date]
    fig.add_trace(
        go.Scatter(
            x=auction_df['security_term'],
            y=auction_df['bid_to_cover_ratio'],
            mode='markers',
            marker=dict(size=10, opacity=opacity),
            name=f'Auction on {date.date()}'
        )
    )


fig.update_layout(
    xaxis_title="Security Term",
    yaxis_title="Bid-to-Cover Ratio",
    xaxis_tickangle=45,
    template="plotly_dark",
    font_family = "Bloomberg",
)

fig.show()


# Data preprocessing
df = df.reset_index(drop=True)
df['auction_date'] = pd.to_datetime(df['auction_date'])
df['bid_to_cover_ratio'] = pd.to_numeric(df['bid_to_cover_ratio'], errors='coerce')


df = df.dropna(subset=['bid_to_cover_ratio'])

# Get the last 5 auctions
df = df.sort_values(by='auction_date', ascending=False)
last_5_auctions = df.head(5)
last_5_terms = last_5_auctions['security_term'].unique()

# Calculate the max histogram frequency across all terms
max_hist_freq = 0
for term in last_5_terms:
    term_df = df[df['security_term'] == term]
    historical_data = term_df['bid_to_cover_ratio']
    hist_freq = np.histogram(historical_data, bins=30)[0].max()  # Get the max frequency of the histogram
    max_hist_freq = max(max_hist_freq, hist_freq)

# Create the subplot figure
fig = make_subplots(
    rows=1, 
    cols=len(last_5_terms), 
    shared_xaxes=True, 
    shared_yaxes=True, 
    subplot_titles=[f"{term}" for term in last_5_terms],
    vertical_spacing=0.1
)

# Add histograms and vertical lines to each subplot
for i, term in enumerate(last_5_terms):
    term_df = df[df['security_term'] == term]
    last_5_auctions_for_term = term_df.sort_values(by='auction_date', ascending=False).head(5)

    if last_5_auctions_for_term.empty:
        print(f"No data available for {term}.")
        continue

    historical_data = term_df['bid_to_cover_ratio']

    # Add histogram to the subplot
    fig.add_trace(
        go.Histogram(
            x=historical_data,
            nbinsx=30,
            name=f"{term} Historical Distribution",
            opacity=0.7
        ),
        row=1, col=i+1
    )

    # Add markers for the last 5 auction results
    for _, row in last_5_auctions_for_term.iterrows():
        auction_date = row['auction_date']
        bid_to_cover = row['bid_to_cover_ratio']

        fig.add_trace(
            go.Scatter(
                x=[bid_to_cover],
                y=[0],
                mode='markers',
                name=f"{term} on {auction_date.date()}: {bid_to_cover}",
                marker=dict(size=10, color='red', symbol='x')
            ),
            row=1, col=i+1
        )

    # Calculate Z-scores
    mean = historical_data.mean()
    std_dev = historical_data.std()
    for _, row in last_5_auctions_for_term.iterrows():
        bid_to_cover = row['bid_to_cover_ratio']
        z_score = (bid_to_cover - mean) / std_dev
        print(f"{term} auction on {row['auction_date'].date()}: Z-Score = {z_score:.2f}")

    # Add median as a vertical line (spanning the full height of the plot)
    median_bid_to_cover = historical_data.median()
    fig.add_trace(
        go.Scatter(
            x=[median_bid_to_cover, median_bid_to_cover],
            y=[0, max_hist_freq],  # Extend the line from y=0 to the max frequency of all histograms
            mode='lines',
            name=f"Median: {median_bid_to_cover:.2f}",
            line=dict(color='blue', dash='dot'),
            showlegend=True
        ),
        row=1, col=i+1
    )

    
    most_recent_auction = last_5_auctions_for_term.iloc[0]
    most_recent_bid_to_cover = most_recent_auction['bid_to_cover_ratio']
    fig.add_trace(
        go.Scatter(
            x=[most_recent_bid_to_cover, most_recent_bid_to_cover],
            y=[0, max_hist_freq],  # Extend the line from y=0 to the max frequency of all histograms
            mode='lines',
            name=f"Most Recent: {most_recent_bid_to_cover:.2f}",
            line=dict(color='red', dash='solid'),
            showlegend=True
        ),
        row=1, col=i+1
    )

# Update layout
fig.update_layout(
    title="Historical Distributions For Most Recent Auctions",
    xaxis_title="Bid-to-Cover Ratio",
    yaxis_title="Frequency",
    template="plotly_dark",
    font_family="Bloomberg",
    showlegend=False,
    height=500,  # Adjust the overall height to fit all subplots
)

# Show the figure
fig.show()
