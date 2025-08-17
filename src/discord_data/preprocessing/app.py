"""
Streamlit app for evaluating Discord message classification results.
Provides interactive visualization and analysis of JSONL classification output.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
from typing import List, Dict, Any
import os

st.set_page_config(
    page_title="Discord Classification Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_jsonl_data(file_path: str) -> pd.DataFrame:
    """Load and parse JSONL classification results"""
    data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    data.append(record)
                except json.JSONDecodeError:
                    st.warning(f"Skipped invalid JSON on line {line_num}")
                    continue
    except FileNotFoundError:
        st.error(f"File not found: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()
    
    if not data:
        st.warning("No valid data found in file")
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Convert timestamp to datetime if present
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    return df

def create_overview_metrics(df: pd.DataFrame):
    """Display overview metrics in columns"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Messages", len(df))
    
    with col2:
        avg_confidence = df['confidence'].mean() if 'confidence' in df.columns else 0
        st.metric("Avg Confidence", f"{avg_confidence:.3f}")
    
    with col3:
        high_conf = (df['confidence'] > 0.8).sum() if 'confidence' in df.columns else 0
        st.metric("High Confidence (>0.8)", high_conf)
    
    with col4:
        unique_authors = df['author'].nunique() if 'author' in df.columns else 0
        st.metric("Unique Authors", unique_authors)
    
    with col5:
        unique_channels = df['channel'].nunique() if 'channel' in df.columns else 0
        st.metric("Unique Channels", unique_channels)

def create_classification_distribution(df: pd.DataFrame):
    """Create classification type distribution chart"""
    if 'type' not in df.columns:
        st.warning("No 'type' column found for classification distribution")
        return
    
    type_counts = df['type'].value_counts()
    
    fig = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        title="Classification Distribution",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)

def create_confidence_distribution(df: pd.DataFrame):
    """Create confidence score distribution"""
    if 'confidence' not in df.columns:
        st.warning("No 'confidence' column found")
        return
    
    fig = px.histogram(
        df,
        x='confidence',
        nbins=30,
        title="Confidence Score Distribution",
        labels={'confidence': 'Confidence Score', 'count': 'Number of Messages'}
    )
    
    fig.add_vline(x=0.8, line_dash="dash", line_color="red", 
                  annotation_text="High Confidence Threshold")
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def create_timeline_analysis(df: pd.DataFrame):
    """Create timeline analysis if timestamp is available"""
    if 'timestamp' not in df.columns or df['timestamp'].isna().all():
        st.info("No timestamp data available for timeline analysis")
        return
    
    # Group by date and type
    df['date'] = df['timestamp'].dt.date
    timeline_data = df.groupby(['date', 'type']).size().reset_index(name='count')
    
    fig = px.line(
        timeline_data,
        x='date',
        y='count',
        color='type',
        title="Message Classification Over Time",
        labels={'count': 'Number of Messages', 'date': 'Date'}
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def create_confidence_by_type(df: pd.DataFrame):
    """Create confidence distribution by classification type"""
    if 'confidence' not in df.columns or 'type' not in df.columns:
        return
    
    fig = px.box(
        df,
        x='type',
        y='confidence',
        title="Confidence Distribution by Classification Type",
        labels={'confidence': 'Confidence Score', 'type': 'Classification Type'}
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def create_author_analysis(df: pd.DataFrame):
    """Create author-based analysis"""
    if 'author' not in df.columns:
        return
    
    # Top authors by message count
    author_counts = df['author'].value_counts().head(10)
    
    fig = px.bar(
        x=author_counts.values,
        y=author_counts.index,
        orientation='h',
        title="Top 10 Authors by Message Count",
        labels={'x': 'Number of Messages', 'y': 'Author'}
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("📊 Discord Classification Evaluator")
    st.markdown("Analyze and evaluate Discord message classification results")
    
    # Sidebar for file selection
    st.sidebar.header("Data Loading")
    
    # File uploader
    uploaded_file = st.sidebar.file_uploader(
        "Upload JSONL file",
        type=['jsonl'],
        help="Upload your classified messages JSONL file"
    )
    
    # Alternative: file path input
    st.sidebar.markdown("**Or enter file path:**")
    file_path = st.sidebar.text_input(
        "File path",
        placeholder="/path/to/your/classified_messages.jsonl"
    )
    
    # Load data
    df = pd.DataFrame()
    
    if uploaded_file is not None:
        # Save uploaded file temporarily and load
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        df = load_jsonl_data(temp_path)
        os.unlink(temp_path)  # Clean up
        
    elif file_path and os.path.exists(file_path):
        df = load_jsonl_data(file_path)
    
    if df.empty:
        st.info("Please upload a JSONL file or enter a valid file path to get started.")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Classification type filter
    if 'type' in df.columns:
        selected_types = st.sidebar.multiselect(
            "Classification Types",
            options=df['type'].unique(),
            default=df['type'].unique()
        )
        df = df[df['type'].isin(selected_types)]
    
    # Confidence threshold
    if 'confidence' in df.columns:
        min_confidence = st.sidebar.slider(
            "Minimum Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05
        )
        df = df[df['confidence'] >= min_confidence]
    
    # Author filter
    if 'author' in df.columns:
        selected_authors = st.sidebar.multiselect(
            "Authors",
            options=sorted(df['author'].unique()),
            default=[]
        )
        if selected_authors:
            df = df[df['author'].isin(selected_authors)]
    
    if df.empty:
        st.warning("No data matches the selected filters.")
        return
    
    # Main content
    st.header("📈 Overview")
    create_overview_metrics(df)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        create_classification_distribution(df)
    
    with col2:
        create_confidence_distribution(df)
    
    st.header("📊 Detailed Analysis")
    
    col3, col4 = st.columns(2)
    
    with col3:
        create_confidence_by_type(df)
    
    with col4:
        create_author_analysis(df)
    
    # Timeline analysis
    st.header("⏰ Timeline Analysis")
    create_timeline_analysis(df)
    
    # Data table
    st.header("📋 Raw Data")
    
    # Search functionality
    search_term = st.text_input("Search in content:", placeholder="Enter search term...")
    if search_term:
        mask = df['content'].str.contains(search_term, case=False, na=False)
        filtered_df = df[mask]
        st.write(f"Found {len(filtered_df)} messages matching '{search_term}'")
    else:
        filtered_df = df
    
    # Display options
    col_display1, col_display2 = st.columns(2)
    with col_display1:
        show_rows = st.selectbox("Rows to display", [10, 25, 50, 100], index=1)
    with col_display2:
        sort_by = st.selectbox(
            "Sort by",
            ['confidence', 'timestamp', 'type', 'author'] if 'confidence' in df.columns else ['type', 'author'],
            index=0
        )
    
    # Display filtered and sorted data
    display_df = filtered_df.sort_values(sort_by, ascending=False).head(show_rows)
    
    # Select columns to display
    available_columns = list(display_df.columns)
    selected_columns = st.multiselect(
        "Select columns to display",
        available_columns,
        default=['type', 'confidence', 'author', 'content'][:len(available_columns)]
    )
    
    if selected_columns:
        st.dataframe(
            display_df[selected_columns],
            use_container_width=True,
            hide_index=True
        )
    
    # Export functionality
    st.header("💾 Export")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("Download Filtered Data as CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"filtered_classifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col_export2:
        if st.button("Download Summary Report"):
            summary = {
                "total_messages": len(filtered_df),
                "classification_distribution": filtered_df['type'].value_counts().to_dict() if 'type' in filtered_df.columns else {},
                "average_confidence": filtered_df['confidence'].mean() if 'confidence' in filtered_df.columns else None,
                "high_confidence_count": (filtered_df['confidence'] > 0.8).sum() if 'confidence' in filtered_df.columns else None,
                "unique_authors": filtered_df['author'].nunique() if 'author' in filtered_df.columns else None,
                "date_range": {
                    "start": filtered_df['timestamp'].min().isoformat() if 'timestamp' in filtered_df.columns and not filtered_df['timestamp'].isna().all() else None,
                    "end": filtered_df['timestamp'].max().isoformat() if 'timestamp' in filtered_df.columns and not filtered_df['timestamp'].isna().all() else None
                }
            }
            
            summary_json = json.dumps(summary, indent=2, default=str)
            st.download_button(
                label="Download JSON Report",
                data=summary_json,
                file_name=f"classification_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()