import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ------------------------------------
# Dashboard Title and Description
# ------------------------------------
st.set_page_config(page_title="Booking Latency Dashboard", layout="wide")
st.title("🐲 Booking Latency Dashboard")
st.markdown("""
This dashboard visualizes and analyzes booking latency data (A→B→C).

- **A→B:** Latency from booking received to booking pushed  
- **B→C:** Latency from booking creation to invoice creation  
- **A→C:** Total latency from booking received to invoice creation

Use this dashboard to identify latency issues and breach statistics.
""")

# ------------------------------------
# Helper Functions
# ------------------------------------
def parse_timedelta_safe(value):
    """
    Safely convert various time strings into a pandas Timedelta.
    
    First, try pd.to_timedelta. If that fails (common for strings like 
    "0 years 0 mons 0 days 0 hours 0 mins 12 secs"), we attempt a custom regex.
    
    Assumptions:
      - Years = 365 days, Months = 30 days.
    """
    if pd.isna(value):
        return pd.Timedelta(0)
    
    s = str(value).strip()
    # Try standard conversion first
    try:
        return pd.to_timedelta(s)
    except Exception:
        pass
    
    # Custom regex for format like: "0 years 0 mons 0 days 0 hours 0 mins 12 secs"
    pattern = re.compile(
        r'^(?P<years>\d+)\s+years?\s+(?P<mons>\d+)\s+mons?\s+(?P<days>\d+)\s+days?\s+'
        r'(?P<hours>\d+)\s+hours?\s+(?P<minutes>\d+)\s+mins?\s+(?P<seconds>\d+(\.\d+)?)\s+secs$'
    )
    match = pattern.search(s)
    if match:
        years = int(match.group("years"))
        mons = int(match.group("mons"))
        days = int(match.group("days"))
        hours = int(match.group("hours"))
        minutes = int(match.group("minutes"))
        seconds = float(match.group("seconds"))
        total_days = years * 365 + mons * 30 + days
        total_sec = total_days * 86400 + hours * 3600 + minutes * 60 + seconds
        return pd.Timedelta(seconds=total_sec)
    return pd.Timedelta(0)

def format_timedelta_dhms(td: pd.Timedelta) -> str:
    """
    Converts a pandas Timedelta into a human-readable string.
    Example: '14 days 23 hours 37 minutes 46 seconds'
    """
    if pd.isna(td) or td == pd.Timedelta(0):
        return "0 days 0 hours 0 minutes 0 seconds"
    days = td.days
    hours = td.components.hours
    minutes = td.components.minutes
    seconds = td.components.seconds
    return f"{days} days {hours} hours {minutes} minutes {seconds} seconds"

def categorize_breach(breach):
    """
    Map the 'breach_percentage' values from final.py into consistent labels.
    If a value doesn't match any known category, label it as 'Missing Data'.
    """
    if breach is None or pd.isna(breach):
        return "Missing Data"
    breach_val_str = str(breach).strip()
    if breach_val_str in ["Within Threshold", "<=50th percentile"]:
        return breach_val_str
    elif '50-60th' in breach_val_str:
        return '50-60th percentile'
    elif '60-70th' in breach_val_str:
        return '60-70th percentile'
    elif '70-80th' in breach_val_str:
        return '70-80th percentile'
    elif '80-90th' in breach_val_str:
        return '80-90th percentile'
    elif '90-100th' in breach_val_str:
        return '90-100th percentile'
    else:
        return "Missing Data"

# ------------------------------------
# Load Data from Excel File
# ------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("final_latency.xlsx")
    return df

data = load_data()

# ------------------------------------
# Calculate Summary Metrics
# ------------------------------------
total_bookings = data.shape[0]

def is_breach(label):
    if not isinstance(label, str):
        return False
    return label.strip() != "Within Threshold"

breach_count = data[data['breach_percentage'].apply(is_breach)].shape[0]
breach_percentage_total = (breach_count / total_bookings) * 100
avg_total_latency = data['total_latency'].apply(pd.to_timedelta).mean()

# ------------------------------------
# Display Summary Metrics
# ------------------------------------
st.subheader("Summary Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 Avg Total Latency", str(avg_total_latency).split('.')[0])
col2.metric("🔖 Total Bookings", total_bookings)
col3.metric("⚠️ Total Breaches", breach_count)
col4.metric("🚨 Breach %", f"{breach_percentage_total:.2f}%")

# =============================================================================
# BAR CHART: Total Latency per Booking (A→C)
# =============================================================================
st.subheader("Total Latency per Booking (A→C)")
data['total_latency_minutes'] = data['total_latency'].apply(lambda x: parse_timedelta_safe(x).total_seconds() / 60)
data['total_latency_minutes_rounded'] = data['total_latency_minutes'].apply(lambda m: round(m))
data['latency_a_to_b_human'] = data['latency_a_to_b'].apply(lambda x: format_timedelta_dhms(parse_timedelta_safe(x)))
data['latency_b_to_c_human'] = data['latency_b_to_c'].apply(lambda x: format_timedelta_dhms(parse_timedelta_safe(x)))
data['total_latency_human'] = data['total_latency'].apply(lambda x: format_timedelta_dhms(parse_timedelta_safe(x)))

# Non-editable sort order via radio
sort_order = st.radio("Sort Order for Total Latency (Minutes)", ["Ascending", "Descending"])
if sort_order == "Ascending":
    data_sorted = data.sort_values(by="total_latency_minutes_rounded", ascending=True)
else:
    data_sorted = data.sort_values(by="total_latency_minutes_rounded", ascending=False)
data_sorted = data_sorted.reset_index(drop=True)

fig_latency = px.bar(
    data_sorted,
    x=data_sorted.index,
    y="total_latency_minutes_rounded",
    labels={"x": "Booking #", "total_latency_minutes_rounded": "Total Latency (Minutes)"},
    custom_data=["booking_code", "latency_a_to_b_human", "latency_b_to_c_human", "total_latency_human"],
    color_discrete_sequence=["purple"]
)
fig_latency.update_traces(
    hovertemplate=(
        "<b>Booking #:</b> %{x}<br>"
        "<b>Booking Code:</b> %{customdata[0]}<br>"
        "<b>Total Latency:</b> %{y} min<br>"
        "<b>A→B (Booking Received → Booking Pushed):</b> %{customdata[1]}<br>"
        "<b>B→C (Booking Pushed → Invoice Created):</b> %{customdata[2]}<br>"
        "<b>A→C (Booking Received → Invoice Created):</b> %{customdata[3]}<extra></extra>"
    )
)
fig_latency.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig_latency, use_container_width=True)

# =============================================================================
# PIE CHART: Breach Percentage Distribution
# =============================================================================
st.subheader("Breach Percentage Distribution")
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

# =============================================================================
# SCATTER PLOT: A→B vs. B→C Latencies
# =============================================================================
st.subheader("Booking Latencies: A→B vs. B→C")
st.markdown("""
This scatter plot compares:
- **X-axis:** Time from Booking Received → Booking Pushed (A→B) in minutes  
- **Y-axis:** Time from Booking Pushed → Invoice Created (B→C) in minutes  

Each point represents a booking. Colors indicate the breach category.
""")
data['latency_a_to_b_min'] = data['latency_a_to_b'].apply(lambda x: parse_timedelta_safe(x).total_seconds() / 60)
data['latency_b_to_c_min'] = data['latency_b_to_c'].apply(lambda x: parse_timedelta_safe(x).total_seconds() / 60)

fig_scatter = px.scatter(
    data,
    x="latency_a_to_b_min",
    y="latency_b_to_c_min",
    color="breach_category",
    size="total_latency_minutes_rounded",
    hover_data=["booking_code", "total_latency_minutes_rounded"],
    labels={
        "latency_a_to_b_min": "A→B Latency (min)",
        "latency_b_to_c_min": "B→C Latency (min)",
        "breach_category": "Breach Category",
        "total_latency_minutes_rounded": "Total Latency (min)"
    },
    title="Scatter Plot: A→B vs. B→C Latencies",
    color_discrete_sequence=px.colors.qualitative.Plotly
)
fig_scatter.update_traces(marker=dict(size=12, opacity=0.8),
    hovertemplate=(
        "<b>Booking Code:</b> %{customdata[0]}<br>"
        "<b>A→B Latency:</b> %{x:.2f} min<br>"
        "<b>B→C Latency:</b> %{y:.2f} min<br>"
        "<b>Total Latency:</b> %{customdata[1]} min<extra></extra>"
    )
)
st.plotly_chart(fig_scatter, use_container_width=True)

# =============================================================================
# TREND OF AVERAGE TOTAL LATENCY OVER TIME (Line Chart)
# =============================================================================
st.subheader("Trend of Average Total Latency Over Time")
data['booking_received_at'] = pd.to_datetime(data['booking_received_at'], errors='coerce')

df_line = data.dropna(subset=['booking_received_at']).copy()
df_line['latency_minutes'] = df_line['total_latency'].apply(lambda x: parse_timedelta_safe(x).total_seconds() / 60)

# Group by date to get both average latency and total bookings
agg_line = (
    df_line.groupby(df_line['booking_received_at'].dt.date)['latency_minutes']
    .agg(['mean', 'count'])
    .reset_index()
)
agg_line.columns = ['Date', 'Avg Total Latency (Minutes)', 'Bookings Completed']

fig_line = px.line(
    agg_line,
    x="Date",
    y="Avg Total Latency (Minutes)",
    markers=True,
    title="Average Total Latency Over Time",
    color_discrete_sequence=["purple"],
    hover_data=["Bookings Completed"]
)
st.plotly_chart(fig_line, use_container_width=True)

# =============================================================================
# FUNNEL CHART: Booking Funnel (A→B→C) - LAST
# =============================================================================
st.subheader("Booking Funnel: A→B→C")
st.markdown("""
This funnel chart shows the progression of bookings through the stages:
- **Booking Received**  
- **Booking Pushed**  
- **Invoice Created**

The chart displays counts along with average latency (in minutes) for the transition stages.
""")
count_received = data.shape[0]
count_pushed = data['booking_pushed_at'].notna().sum()
count_invoiced = data['invoice_created_at'].notna().sum()

avg_a_to_b = data['latency_a_to_b'].apply(lambda x: parse_timedelta_safe(x).total_seconds()/60).mean()
avg_a_to_c = data['total_latency_minutes'].mean()

within_threshold_count = data[data['breach_category'] == 'Within Threshold'].shape[0]
exceed_threshold_count = count_received - within_threshold_count

df_funnel = pd.DataFrame({
    'Stage': ['Booking Received', 'Booking Pushed', 'Invoice Created'],
    'Count': [count_received, count_pushed, count_invoiced],
    'Avg Latency (min)': [0, round(avg_a_to_b, 2), round(avg_a_to_c, 2)],
    'Breach Breakdown': [
        f"Total: {count_received}",
        f"Total: {count_pushed}",
        f"Within: {within_threshold_count} | Exceed: {exceed_threshold_count}"
    ]
})

fig_funnel = go.Figure()
colors = ['#636EFA', '#EF553B', '#00CC96']

for idx, row in df_funnel.iterrows():
    fig_funnel.add_trace(go.Funnel(
        name=row['Stage'],
        y=[row['Stage']],
        x=[row['Count']],
        text=[f"Count: {row['Count']}<br>Avg Latency: {row['Avg Latency (min)']} min<br>{row['Breach Breakdown']}"],
        textposition="inside",
        marker={"color": colors[idx]},
        hoverinfo="text"
    ))

fig_funnel.update_layout(
    title="Booking Funnel: A→B→C (Enhanced)",
    funnelmode="stack",
    font=dict(size=14),
    height=400
)
st.plotly_chart(fig_funnel, use_container_width=True)

# =============================================================================
# DASHBOARD OVERVIEW AND TECHNICAL FLOW (Bigger Font)
# =============================================================================
st.markdown("""
---
<div style="font-size:18px; line-height:1.6;">
<h2>🚀 <strong>Dashboard Overview</strong></h2>
<p>This dashboard provides an end-to-end visualization of latency across different stages of the booking and invoicing lifecycle. It helps operations teams identify bottlenecks and assess performance against SLAs.</p>

<h2>🛠️ <strong>Technical Flow</strong></h2>
<ol>
    <li><strong>Data Extraction:</strong> 
        <ul>
            <li>Bookings Received → <code>bookings_master.createdAt</code></li>
            <li>Bookings Pushed → <code>sync_master.createdAt</code></li>
            <li>Invoice Created → <code>gms_finance.invoices.created_at</code></li>
        </ul>
    </li>
    <li><strong>Latency Calculation:</strong> 
        <ul>
            <li>Merge A→B and B→C CSVs using <code>booking_code</code></li>
            <li>Convert latency strings to seconds using regex</li>
            <li>Compute total latency: A→C = A→B + B→C</li>
        </ul>
    </li>
    <li><strong>Breach Calculation:</strong> 
        <ul>
            <li>Compare total latency against 1800 seconds (30 min SLA)</li>
            <li>Compute breach percentage and categorize accordingly</li>
        </ul>
    </li>
    <li><strong>Visualization:</strong> 
        <ul>
            <li>Bar Chart, Pie Chart, Scatter Plot, Funnel Chart, Trend Line, and interactive filters</li>
        </ul>
    </li>
    <li><strong>Deployment:</strong> 
        <ul>
            <li>Hosted on Streamlit Cloud via GitHub integration</li>
        </ul>
    </li>
</ol>

<p><strong>🎯 Objective:</strong><br>
Enable real-time monitoring of latency performance, visualize SLA breaches, and improve operational response.</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Q&A Section with Larger Font & Emojis
# =============================================================================
st.markdown("""
---
<div style="font-size:18px; line-height:1.6;">
<h2>❓ <strong>Frequently Asked Questions</strong></h2>

<h3>1️⃣ Why are we not analyzing all bookings?</h3>
<p><strong>A:</strong> We are focusing our analysis on bookings that successfully complete the entire process—from booking received to invoice creation. A significant portion of bookings failed at the "Booking Pushed" stage, so we filter those out. Moving forward, we will analyze data from fresh, successfully processed bookings on a <em>bi-weekly</em> basis to ensure our insights accurately reflect current performance.</p>

<h3>2️⃣ What improvements will we be implementing going forward?</h3>
<p><strong>A:</strong> We plan to <strong>automate</strong> the data monitoring process to continuously track key metrics such as breach percentages. Additionally, we'll enhance our <strong>visualization</strong> and <strong>alert</strong> systems to promptly identify bottlenecks. Future improvements include integrating <strong>predictive analytics</strong> to forecast trends and further optimize our booking and invoicing workflow.</p>
</div>
""", unsafe_allow_html=True)
