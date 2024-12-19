import pandas as pd
import plotly.express as px
import streamlit as st

# Load the dataset
# data = pd.read_csv(r"./PaymentDataPH.csv", encoding='latin1')  # Adjust for encoding issues
data = pd.read_csv(r"./PaymentDataPH.zip", compression='zip', encoding='latin1')

# Ensure 'CreatedAt' column is in datetime format
data['CreatedAt'] = pd.to_datetime(data['CreatedAt'], errors='coerce', dayfirst=True)

# Add 'Mode', 'IsCollectionBusiness', and 'IsRecipientBusiness' columns if not already present
if 'Mode' not in data.columns:
    data['Mode'] = None  # Assign None or default values as appropriate
if 'IsCollectionBusiness' not in data.columns:
    data['IsCollectionBusiness'] = False  # Assign default values (e.g., False)
if 'IsRecipientBusiness' not in data.columns:
    data['IsRecipientBusiness'] = False  # Assign default values (e.g., False)

# Create Date and Hour columns for easier filtering (without splitting 'CreatedAt')
data['Date'] = pd.to_datetime(data['CreatedAt'].dt.date)  # Ensure Date is in datetime format
data['Hour'] = data['CreatedAt'].dt.hour
data['Time'] = data['CreatedAt'].dt.time

# Sidebar Filters
st.sidebar.header("Filters")

# Hidden 'Brand' filter - Default to 'All'
selected_brand = 'All'

# Apply brand filter to update other filters
filtered_data = data if selected_brand == 'All' else data[data['Brand'] == selected_brand]

# 1. Date Range Filter
min_date = filtered_data['Date'].min()
max_date = filtered_data['Date'].max()
date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

# 2. Hour Range Filter
hour_range = st.sidebar.slider("Select Hour Range", 0, 23, (0, 23))

# 3. Amount Range Filter
min_amount, max_amount = float(filtered_data['Amount'].min()), float(filtered_data['Amount'].max())
amount_range = st.sidebar.slider("Select Amount Range", min_amount, max_amount, (min_amount, max_amount))

# 4. Mode Filter with "All" option
modes = list(filtered_data['Mode'].dropna().unique())  # Remove 'All' option for modes
modes = ['All'] + modes  # Add 'All' option
selected_modes = st.sidebar.multiselect("Select Modes", modes, default=modes)

# 5. IsCollectionBusiness Filter
selected_is_collection_business = st.sidebar.multiselect(
    "Select IsCollectionBusiness", [True, False], default=[True, False])

# 6. IsRecipientBusiness Filter
selected_is_recipient_business = st.sidebar.multiselect(
    "Select IsRecipientBusiness", [True, False], default=[True, False])

# 7. Carrier Filter with "All" option
carriers = ['All'] + list(filtered_data['Carrier'].unique())  # Add 'All' option for carriers
selected_carriers = st.sidebar.multiselect("Select Carriers", carriers, default=carriers)

# 8. Service Filter with "All" option
carrier_services_dict = {
    carrier: filtered_data[filtered_data['Carrier'] == carrier]['ServiceType'].unique()
    for carrier in selected_carriers if carrier != 'All'
}
# Combine all services from selected carriers and add 'All' option
selected_services = []
if selected_carriers != ['All']:  # Only show services if specific carriers are selected
    all_services = []
    for carrier in selected_carriers:
        if carrier != 'All':
            all_services.extend(carrier_services_dict.get(carrier, []))
    all_services = list(set(all_services))  # Remove duplicates
    selected_services = st.sidebar.multiselect(
        "Select Services",
        options=all_services,
        default=all_services
    )
else:
    selected_services = st.sidebar.multiselect(
        "Select Services",
        options=filtered_data['ServiceType'].unique(),
        default=filtered_data['ServiceType'].unique()
    )

# Apply filters for Mode, IsCollectionBusiness, IsRecipientBusiness, etc.
if 'All' not in selected_modes:
    filtered_data = filtered_data[filtered_data['Mode'].isin(selected_modes)]
if 'All' not in selected_carriers:
    filtered_data = filtered_data[filtered_data['Carrier'].isin(selected_carriers)]
if 'All' not in selected_services:
    filtered_data = filtered_data[filtered_data['ServiceType'].isin(selected_services)]

# Apply other filters (IsCollectionBusiness, IsRecipientBusiness, etc.)
filtered_data = filtered_data[filtered_data['IsCollectionBusiness'].isin(selected_is_collection_business)]
filtered_data = filtered_data[filtered_data['IsRecipientBusiness'].isin(selected_is_recipient_business)]

# Apply the date range, hour range, and amount range filters
filtered_data = filtered_data[(
    filtered_data['Date'].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))) &
    (filtered_data['Hour'].between(hour_range[0], hour_range[1])) &
    (filtered_data['Amount'].between(*amount_range))
]

# Display filtered data preview
# st.write("Filtered Dataset Preview:") 
# st.dataframe(filtered_data.head())

# Line Graph Across Time (counting rows instead of summing Amount)
st.header("Purchases across a period of time")

# Calculate the difference between the dates in days
date_diff = (pd.to_datetime(date_range[1]) - pd.to_datetime(date_range[0])).days

# Select time interval filter
interval = st.selectbox(
    "Select time interval - only when the selected range is less than 30 days:",
    ["10T", "15T", "30T", "1H", "2H"],
    index=3  # Default to "1H"
)

# Adjust the interval based on the date range
if date_diff > 60:
    interval = "2D"  # 2-day intervals if more than 60 days selected
elif 30 <= date_diff <= 60:
    interval = "1D"  # 1-day intervals if between 30-60 days
# Otherwise, keep the interval as the user-selected option for less than 30 days

if not filtered_data.empty:
    # Ensure 'CreatedAt' column exists in filtered_data for resampling
    resampled = filtered_data.set_index('CreatedAt').resample(interval).size()

    # Create the line plot
    fig = px.line(resampled, x=resampled.index, y=resampled.values,
                  title=f"Number of Purchases Over Time ({interval})")
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Number of Purchases"
    )
    st.plotly_chart(fig)
else:
    st.warning("No data available for the selected filters.")

# --- Start of the Second Graph: Average Purchases per 15-Min Interval ---
st.header("Average purchases during selected weekday")

# Allow the user to select a specific weekday
weekdays_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
day = st.selectbox("Select day of the week:", weekdays_ordered)

# Filter data by the selected weekday (and the common date range filter)
filtered_day_data = filtered_data[filtered_data['Date'].dt.day_name() == day]

if not filtered_day_data.empty:
    # Group by 15-minute intervals and calculate average number of purchases
    filtered_day_data['TimeSlot'] = filtered_day_data['CreatedAt'].dt.floor('15T')
    avg_purchases = filtered_day_data.groupby(filtered_day_data['TimeSlot'].dt.time).size().reset_index(name='Average Purchases')

    # Create the line plot for average purchases per 15-minute time slot
    fig = px.line(avg_purchases, x='TimeSlot', y='Average Purchases',
                  title=f"Average Purchases on {day}s ({date_range[0]} to {date_range[1]})")

    # Reducing x-axis tick labels to avoid crowding by selecting a few time intervals
    tick_step = 2  # Step for displaying ticks (show every second time slot)

    fig.update_layout(
        xaxis_title="Time of Day (15-minute intervals)",
        yaxis_title="Average Purchases",
        xaxis=dict(
            tickformat="%H:%M",  # Format x-axis as time
            tickmode="array",
            tickvals=avg_purchases['TimeSlot'][::tick_step],  # Show every second time slot
            ticktext=avg_purchases['TimeSlot'][::tick_step].astype(str)  # Format the tick labels as time strings
        )
    )
    st.plotly_chart(fig)
else:
    st.warning(f"No data available for {day}s within the selected date range.")
