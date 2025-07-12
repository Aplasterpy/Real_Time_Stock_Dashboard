import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ----------------------------
# Utility Functions
# ----------------------------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(series, window=20):
    sma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return sma, upper, lower

# ----------------------------
# Streamlit Config
# ----------------------------
st.set_page_config(page_title="📈 Real-Time Stock Dashboard", layout="wide")
st.title("📊 Real-Time Stock Market Dashboard")

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.header("📌 Stock Parameters")
ticker_dict = {
    "Apple Inc. (AAPL)": "AAPL",
    "Microsoft Corp. (MSFT)": "MSFT",
    "Amazon.com Inc. (AMZN)": "AMZN",
    "Alphabet Inc. (GOOGL)": "GOOGL",
    "Meta Platforms (META)": "META",
    "Tesla Inc. (TSLA)": "TSLA",
    "NVIDIA Corporation (NVDA)": "NVDA",
    "Netflix Inc. (NFLX)": "NFLX",
    "JPMorgan Chase (JPM)": "JPM",
    "Johnson & Johnson (JNJ)": "JNJ",
    "Walmart Inc. (WMT)": "WMT",
    "Visa Inc. (V)": "V"
}
selected_name = st.sidebar.selectbox("Choose a Stock", list(ticker_dict.keys()))
ticker = ticker_dict[selected_name]
start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=30))
end_date = st.sidebar.date_input("End Date", datetime.now())
interval = st.sidebar.selectbox("Interval", ['1d', '1h', '15m', '5m', '1wk'])

theme = st.sidebar.radio("Theme", ["Light", "Dark"])
plotly_template = "plotly_white" if theme == "Light" else "plotly_dark"

st.sidebar.header("📊 Visuals")
show_price = st.sidebar.checkbox("Price Chart + SMAs", True)
show_rsi = st.sidebar.checkbox("RSI", False)
show_macd = st.sidebar.checkbox("MACD", False)
show_returns = st.sidebar.checkbox("Daily Returns", True)

# ----------------------------
# Fetch Stock Data
# ----------------------------
@st.cache_data
def get_stock_data(ticker, start, end, interval):
    df = yf.download(ticker, start=start, end=end, interval=interval)
    df.reset_index(inplace=True)
    return df

try:
    df = get_stock_data(ticker, start_date, end_date, interval)
    if df.empty:
        st.warning("No data available.")
        st.stop()

    df['Time'] = df['Datetime'] if 'Datetime' in df.columns else df['Date']
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    df['MACD'], df['MACD_Signal'] = calculate_macd(df['Close'])
    df['BB_Mid'], df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])

    # ----------------------------
    # Recent Data Table
    # ----------------------------
    st.subheader(f"🗂️ Recent Data: {ticker}")
    st.dataframe(df.tail(10))

    # ----------------------------
    # Price Chart with SMAs & Volume
    # ----------------------------
    if show_price:
        st.subheader("📈 Candlestick Chart with SMA + Volume")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.1, row_heights=[0.7, 0.3],
                            specs=[[{"type": "candlestick"}], [{"type": "bar"}]])

        fig.add_trace(go.Candlestick(
            x=df['Time'],
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            increasing_line_color='green', decreasing_line_color='red',
            name="Candlestick"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df['Time'], y=df['SMA20'], name="SMA 20",
                                 line=dict(color='orange', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Time'], y=df['SMA50'], name="SMA 50",
                                 line=dict(color='blue', dash='dash')), row=1, col=1)

        fig.add_trace(go.Bar(x=df['Time'], y=df['Volume'], name="Volume",
                             marker_color='lightblue'), row=2, col=1)

        fig.update_layout(template=plotly_template, height=700,
                          xaxis_rangeslider_visible=False,
                          legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------
    # RSI
    # ----------------------------
    if show_rsi:
        st.subheader("📉 RSI (Relative Strength Index)")
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df['Time'], y=df['RSI'], name="RSI", line=dict(color='purple')))
        fig_rsi.update_layout(template=plotly_template, yaxis=dict(range=[0, 100]), height=300)
        st.plotly_chart(fig_rsi, use_container_width=True)

    # ----------------------------
    # MACD
    # ----------------------------
    if show_macd:
        st.subheader("📉 MACD")
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df['Time'], y=df['MACD'], name="MACD", line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=df['Time'], y=df['MACD_Signal'], name="Signal", line=dict(color='orange')))
        fig_macd.update_layout(template=plotly_template, height=300)
        st.plotly_chart(fig_macd, use_container_width=True)

    # ----------------------------
    # Daily Returns
    # ----------------------------
    if show_returns:
        st.subheader("📊 Daily Returns (%)")
        df['Daily Return'] = df['Close'].pct_change() * 100
        fig_return = go.Figure()
        fig_return.add_trace(go.Bar(
            x=df['Time'], y=df['Daily Return'],
            marker_color=['green' if val >= 0 else 'red' for val in df['Daily Return']],
            name="Daily Return"
        ))
        fig_return.update_layout(template=plotly_template, height=400, yaxis_title="Return (%)")
        st.plotly_chart(fig_return, use_container_width=True)

    # ----------------------------
    # Financial Summary
    # ----------------------------
    st.subheader("📌 Financial Metrics")
    try:
        latest_close = float(df['Close'].iloc[-1])
        day_high = float(df['High'].iloc[-1])
        day_low = float(df['Low'].iloc[-1])
        volume = int(df['Volume'].iloc[-1])
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latest Close", f"${latest_close:.2f}")
        col2.metric("Daily High", f"${day_high:.2f}")
        col3.metric("Daily Low", f"${day_low:.2f}")
        col4.metric("Volume", f"{volume:,}")
    except:
        st.warning("⚠️ Could not load metrics.")

    # ----------------------------
    # Business Snapshot
    # ----------------------------
    st.subheader("💼 Business Snapshot")
    try:
        info = yf.Ticker(ticker).info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Market Cap:** ${info.get('marketCap', 0):,}")
            st.markdown(f"**PE Ratio:** {info.get('trailingPE', 'N/A')}")
            st.markdown(f"**EPS (TTM):** {info.get('trailingEps', 'N/A')}")
            st.markdown(f"**Forward P/E:** {info.get('forwardPE', 'N/A')}")
        with col2:
            div_yield = info.get('dividendYield')
            st.markdown(f"**Dividend Yield:** {div_yield * 100:.2f}%" if div_yield else "N/A")
            st.markdown(f"**Revenue:** ${info.get('totalRevenue', 0):,}")
            gross = info.get('grossMargins')
            st.markdown(f"**Gross Margin:** {gross * 100:.2f}%" if gross else "N/A")
            st.markdown(f"**Beta:** {info.get('beta', 'N/A')}")
    except Exception as e:
        st.warning(f"Could not load business snapshot: {e}")

    # ----------------------------
    # ---------------- Market Cap Donut Chart ----------------
    st.subheader("📊 Market Cap Share (Top S&P 500 Peers)")

    try:
        # Load S&P 500 data
        sp500_df = pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv")
        top_peers = sp500_df['Symbol'].tolist()[:30]  # Use top 30 for performance

        peer_market_caps = {}
        for symbol in top_peers:
            try:
                peer_info = yf.Ticker(symbol).info
                cap = peer_info.get('marketCap', 0)
                if cap and cap > 0:
                    peer_market_caps[symbol] = cap
            except:
                continue

        # Sort and take top 10
        sorted_peers = sorted(peer_market_caps.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [sym for sym, _ in sorted_peers]
        values = [cap for _, cap in sorted_peers]

        # Highlight selected company
        if ticker not in labels:
            labels.append(ticker)
            values.append(yf.Ticker(ticker).info.get('marketCap', 0))

        fig_donut = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.5,
            textinfo='label+percent',
            marker=dict(line=dict(color='#000000', width=1))
        )])
        fig_donut.update_layout(template=plotly_template, height=500)
        st.plotly_chart(fig_donut, use_container_width=True)

    except Exception as e:
        st.warning(f"Could not generate donut chart: {e}")

    # ----------------------------
    # Download CSV
    # ----------------------------
    st.subheader("📥 Download Data")
    st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'),
                       f"{ticker}_data.csv", "text/csv")

except Exception as e:
    st.error(f"❌ Error: {e}")
