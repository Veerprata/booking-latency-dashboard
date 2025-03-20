# dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -------------------------------
# Dashboard Title and Description
# -------------------------------
st.set_page_config(page_title="Booking Latency Dashboard", layout="wide")
st.title("📊 Booking Latency Dashboard")
st.markdown("""
This dashboard visualizes and analyzes booking latency data (A→B→C).

- **A→B:** Latency from booking received to booking pushed
- **B→C:** Latency from booking creation to invoice creation
- **A→C:** Total latency from booking received to invoice creation

Use this dashboard to identify latency issues and breach statistics.
""")

# ------------------------------------
# Load Data from Excel File
# ------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("final_latency.xlsx")
    return df

# Load the data
data = load_data()

# ------------------------------------
# Calculate Metrics
# ------------------------------------
avg_total_latency = data['total_latency'].apply(pd.to_timedelta).mean()
total_bookings = data.shape[0]
breach_count = data[data['breach_percentage'].apply(lambda x: float(x.rstrip('%'))) > 100].shape[0]
breach_percentage_total = (breach_count / total_bookings) * 100

# ------------------------------------
# Summary Metrics
# ------------------------------------
st.subheader("Summary Metrics")
col1, col2, col3, col4 = st.columns(4)

col1.metric("📈 Avg Total Latency", str(avg_total_latency).split('.')[0])
col2.metric("🔖 Total Bookings", total_bookings)
col3.metric("⚠️ Total Breaches", breach_count)
col4.metric("🚨 Breach %", f"{breach_percentage_total:.2f}%")

# ------------------------------------
# Interactive Bar Chart: Total Latency per Booking
# ------------------------------------
st.subheader("Total Latency per Booking (A→C)")

fig_latency = px.bar(
    data,
    x="booking_code",
    y=data['total_latency'].apply(pd.to_timedelta).dt.total_seconds()/60,  # in minutes
    labels={"y": "Total Latency (Minutes)", "booking_code": "Booking Code"},
    hover_data=["latency_a_to_b", "latency_b_to_c", "total_latency"],
    color_discrete_sequence=["#4E79A7"]
)
fig_latency.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig_latency, use_container_width=True)

# ------------------------------------
# Pie Chart: Breach Percentage Distribution
# ------------------------------------
st.subheader("Breach Percentage Distribution")

# Categorize breaches
def categorize_breach(breach):
    breach_val = float(breach.rstrip('%'))
    if breach_val <= 100:
        return 'Within Threshold'
    elif breach_val <= 200:
        return '100-200% Breach'
    elif breach_val <= 500:
        return '200-500% Breach'
    else:
        return '>500% Breach'

data['breach_category'] = data['breach_percentage'].apply(categorize_breach)

breach_counts = data['breach_category'].value_counts().reset_index()
breach_counts.columns = ['Breach Category', 'Count']

fig_pie = px.pie(
    breach_counts,
    names='Breach Category',
    values='Count',
    color='Breach Category',
    color_discrete_sequence=px.colors.sequential.RdBu,
    hole=0.4
)
st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------
# Optional: Interactive Filtering by Breach Category
# ------------------------------------
st.subheader("🔍 Explore Bookings by Breach Category")
selected_category = st.selectbox("Select Breach Category", breach_counts['Breach Category'].unique())
filtered_data = data[data['breach_category'] == selected_category]
st.dataframe(filtered_data[[
    "booking_code",
    "booking_received_at",
    "booking_pushed_at",
    "invoice_created_at",
    "latency_a_to_b",
    "latency_b_to_c",
    "total_latency",
    "breach_percentage"
]])

# ------------------------------------
# Deployment Note:
# ------------------------------------

st.markdown("""
---

### 🚀 Deployment Instructions:

1. **Ensure your data file `final_latency.xlsx` is in the same directory as this Python script.**
2. **Install Streamlit and dependencies:**
```bash
pip install streamlit pandas openpyxl plotly
```

3. **Run the dashboard locally:**
```bash
streamlit run dashboard.py
```

4. **Deploy to the cloud for free:**
- [Streamlit Cloud](https://streamlit.io/cloud) allows easy deployment directly from a GitHub repository.

Once deployed, your dashboard will be accessible via a shareable URL.
""")
