"""
LLM Call Evaluation Dashboard

A comprehensive Streamlit application for analyzing and evaluating LLM API calls
recorded during Discord Knowledge Graph extraction.
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np

# Page config
st.set_page_config(
    page_title="LLM Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database path (relative to the dashboard location)
DEFAULT_DB_PATH = "../../discord_kg/extraction/llm_powered/bin/llm_evaluation/llm_calls.db"

@st.cache_data
def load_data(db_path: str):
    """Load and cache data from SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        
        query = """
        SELECT 
            call_id,
            timestamp,
            experiment_name,
            messages,
            message_types,
            batch_size,
            segment_id,
            system_prompt,
            user_prompt,
            template_type,
            template_name,
            provider,
            model_name,
            temperature,
            max_tokens,
            raw_response,
            parsed_triples,
            success,
            error_message,
            duration_seconds,
            input_tokens,
            output_tokens,
            total_tokens,
            cost_usd,
            workflow_step,
            node_name,
            workflow_state
        FROM llm_calls
        ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) == 0:
            return None
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Parse JSON fields safely
        def safe_json_parse(x):
            if pd.isna(x) or x == '' or x is None:
                return None
            try:
                return json.loads(x)
            except:
                return None
        
        df['messages_parsed'] = df['messages'].apply(safe_json_parse)
        df['message_types_parsed'] = df['message_types'].apply(safe_json_parse)
        df['parsed_triples_parsed'] = df['parsed_triples'].apply(safe_json_parse)
        
        # Calculate derived fields
        df['hour'] = df['timestamp'].dt.hour
        df['date'] = df['timestamp'].dt.date
        df['cost_per_token'] = df['cost_usd'] / df['total_tokens'].replace(0, np.nan)
        df['tokens_per_second'] = df['total_tokens'] / df['duration_seconds'].replace(0, np.nan)
        
        # Count triples extracted
        df['triples_count'] = df['parsed_triples_parsed'].apply(
            lambda x: len(x) if x and isinstance(x, list) else 0
        )
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def main():
    st.title("📊 LLM Call Evaluation Dashboard")
    st.markdown("Comprehensive analysis of LLM API calls for Discord Knowledge Graph extraction")
    
    # Sidebar for database selection and filters
    with st.sidebar:
        st.header("📁 Data Source")
        
        # Database path input
        db_path = st.text_input(
            "Database Path", 
            value=DEFAULT_DB_PATH,
            help="Path to the SQLite database file"
        )
        
        # Check if database exists
        if not Path(db_path).exists():
            st.error("❌ Database file not found!")
            st.info("Make sure you've run the extraction with recording enabled.")
            st.stop()
        
        # Load data
        with st.spinner("Loading data..."):
            df = load_data(db_path)
        
        if df is None:
            st.error("❌ No data found in database!")
            st.info("Run some extractions with ENABLE_LLM_RECORDING=true to generate data.")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} LLM calls")
        
        # Filters
        st.header("🔍 Filters")
        
        # Date range filter
        if len(df) > 0:
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()
            
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            # Filter by date range
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[
                    (df['timestamp'].dt.date >= start_date) & 
                    (df['timestamp'].dt.date <= end_date)
                ]
        
        # Experiment filter
        experiments = ['All'] + sorted(df['experiment_name'].dropna().unique().tolist())
        selected_experiment = st.selectbox("Experiment", experiments)
        if selected_experiment != 'All':
            df = df[df['experiment_name'] == selected_experiment]
        
        # Provider filter
        providers = ['All'] + sorted(df['provider'].unique().tolist())
        selected_provider = st.selectbox("Provider", providers)
        if selected_provider != 'All':
            df = df[df['provider'] == selected_provider]
        
        # Template type filter
        template_types = ['All'] + sorted(df['template_type'].dropna().unique().tolist())
        selected_template = st.selectbox("Template Type", template_types)
        if selected_template != 'All':
            df = df[df['template_type'] == selected_template]
        
        # Success filter
        success_filter = st.selectbox("Success Status", ['All', 'Successful Only', 'Failed Only'])
        if success_filter == 'Successful Only':
            df = df[df['success'] == 1]
        elif success_filter == 'Failed Only':
            df = df[df['success'] == 0]
    
    # Main dashboard
    if len(df) == 0:
        st.warning("No data matches the selected filters.")
        st.stop()
    
    # Overview metrics
    st.header("📈 Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Calls",
            f"{len(df):,}",
            help="Total number of LLM API calls"
        )
    
    with col2:
        success_rate = (df['success'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.metric(
            "Success Rate",
            f"{success_rate:.1f}%",
            help="Percentage of successful API calls"
        )
    
    with col3:
        total_cost = df['cost_usd'].sum()
        st.metric(
            "Total Cost",
            f"${total_cost:.4f}",
            help="Total cost of all API calls"
        )
    
    with col4:
        avg_duration = df['duration_seconds'].mean()
        st.metric(
            "Avg Duration",
            f"{avg_duration:.2f}s",
            help="Average API call duration"
        )
    
    with col5:
        total_tokens = df['total_tokens'].sum()
        st.metric(
            "Total Tokens",
            f"{total_tokens:,}",
            help="Total tokens processed"
        )
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Call Analytics", 
        "🎯 Template Performance", 
        "⚖️ Provider Comparison", 
        "💰 Cost Analysis", 
        "🕒 Time Analysis",
        "🔍 Call Details"
    ])
    
    with tab1:
        st.header("📊 Call Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Success rate by template type
            if 'template_type' in df.columns and not df['template_type'].isna().all():
                success_by_template = df.groupby('template_type').agg({
                    'success': ['count', 'sum']
                }).round(2)
                success_by_template.columns = ['Total', 'Successful']
                success_by_template['Success_Rate'] = (
                    success_by_template['Successful'] / success_by_template['Total'] * 100
                )
                
                fig = px.bar(
                    success_by_template.reset_index(),
                    x='template_type',
                    y='Success_Rate',
                    title='Success Rate by Template Type',
                    labels={'Success_Rate': 'Success Rate (%)', 'template_type': 'Template Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Token distribution
            if 'total_tokens' in df.columns:
                fig = px.histogram(
                    df,
                    x='total_tokens',
                    title='Token Usage Distribution',
                    nbins=20,
                    labels={'total_tokens': 'Total Tokens', 'count': 'Number of Calls'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Duration vs tokens scatter
        if 'duration_seconds' in df.columns and 'total_tokens' in df.columns:
            fig = px.scatter(
                df,
                x='total_tokens',
                y='duration_seconds',
                color='provider',
                size='cost_usd',
                hover_data=['template_type', 'experiment_name'],
                title='API Call Duration vs Token Count',
                labels={
                    'total_tokens': 'Total Tokens',
                    'duration_seconds': 'Duration (seconds)',
                    'cost_usd': 'Cost (USD)'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("🎯 Template Performance")
        
        if 'template_type' in df.columns and not df['template_type'].isna().all():
            template_stats = df.groupby('template_type').agg({
                'success': ['count', 'sum'],
                'duration_seconds': 'mean',
                'cost_usd': ['mean', 'sum'],
                'total_tokens': 'mean',
                'triples_count': 'mean'
            }).round(4)
            
            template_stats.columns = [
                'Total_Calls', 'Successful_Calls', 'Avg_Duration', 
                'Avg_Cost', 'Total_Cost', 'Avg_Tokens', 'Avg_Triples'
            ]
            template_stats['Success_Rate'] = (
                template_stats['Successful_Calls'] / template_stats['Total_Calls'] * 100
            ).round(2)
            
            st.subheader("Template Performance Summary")
            st.dataframe(template_stats, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Cost per template type
                fig = px.bar(
                    template_stats.reset_index(),
                    x='template_type',
                    y='Total_Cost',
                    title='Total Cost by Template Type',
                    labels={'Total_Cost': 'Total Cost (USD)', 'template_type': 'Template Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Average triples extracted
                fig = px.bar(
                    template_stats.reset_index(),
                    x='template_type',
                    y='Avg_Triples',
                    title='Average Triples Extracted by Template',
                    labels={'Avg_Triples': 'Average Triples', 'template_type': 'Template Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("⚖️ Provider Comparison")
        
        provider_stats = df.groupby('provider').agg({
            'success': ['count', 'sum'],
            'duration_seconds': 'mean',
            'cost_usd': ['mean', 'sum'],
            'total_tokens': ['mean', 'sum'],
            'triples_count': 'mean'
        }).round(4)
        
        provider_stats.columns = [
            'Total_Calls', 'Successful_Calls', 'Avg_Duration',
            'Avg_Cost_Per_Call', 'Total_Cost', 'Avg_Tokens', 'Total_Tokens', 'Avg_Triples'
        ]
        provider_stats['Success_Rate'] = (
            provider_stats['Successful_Calls'] / provider_stats['Total_Calls'] * 100
        ).round(2)
        
        st.subheader("Provider Performance Summary")
        st.dataframe(provider_stats, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Cost comparison
            fig = px.pie(
                provider_stats.reset_index(),
                values='Total_Cost',
                names='provider',
                title='Total Cost Distribution by Provider'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Performance comparison
            fig = go.Figure()
            
            providers = provider_stats.index
            fig.add_trace(go.Scatter(
                x=provider_stats['Avg_Cost_Per_Call'],
                y=provider_stats['Avg_Duration'],
                mode='markers+text',
                text=providers,
                textposition="top center",
                marker=dict(
                    size=provider_stats['Total_Calls'] / 2,
                    sizemode='diameter',
                    sizemin=4
                ),
                name='Providers'
            ))
            
            fig.update_layout(
                title='Provider Performance: Cost vs Speed',
                xaxis_title='Average Cost per Call (USD)',
                yaxis_title='Average Duration (seconds)'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("💰 Cost Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily cost trend
            daily_cost = df.groupby('date')['cost_usd'].sum().reset_index()
            daily_cost['date'] = pd.to_datetime(daily_cost['date'])
            
            fig = px.line(
                daily_cost,
                x='date',
                y='cost_usd',
                title='Daily Cost Trend',
                labels={'cost_usd': 'Cost (USD)', 'date': 'Date'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Cost distribution
            fig = px.box(
                df,
                y='cost_usd',
                x='provider',
                title='Cost Distribution by Provider',
                labels={'cost_usd': 'Cost per Call (USD)'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Cost efficiency analysis
        st.subheader("💡 Cost Efficiency Analysis")
        
        if 'triples_count' in df.columns:
            df['cost_per_triple'] = df['cost_usd'] / df['triples_count'].replace(0, np.nan)
            
            efficiency_stats = df.groupby(['provider', 'template_type']).agg({
                'cost_per_triple': 'mean',
                'cost_usd': 'mean',
                'triples_count': 'mean'
            }).round(6)
            
            st.dataframe(efficiency_stats, use_container_width=True)
    
    with tab5:
        st.header("🕒 Time Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Hourly activity
            hourly_activity = df.groupby('hour').size().reset_index(name='calls')
            
            fig = px.bar(
                hourly_activity,
                x='hour',
                y='calls',
                title='API Calls by Hour of Day',
                labels={'calls': 'Number of Calls', 'hour': 'Hour of Day'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Timeline of calls
            timeline = df.groupby(df['timestamp'].dt.floor('H')).size().reset_index(name='calls')
            
            fig = px.line(
                timeline,
                x='timestamp',
                y='calls',
                title='API Calls Timeline',
                labels={'calls': 'Calls per Hour', 'timestamp': 'Time'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Duration analysis
        if 'duration_seconds' in df.columns:
            st.subheader("⏱️ Duration Analysis")
            
            duration_by_template = df.groupby('template_type')['duration_seconds'].agg([
                'mean', 'median', 'std', 'min', 'max'
            ]).round(3)
            
            st.dataframe(duration_by_template, use_container_width=True)
    
    with tab6:
        st.header("🔍 Detailed Call Analysis")
        
        # Search and filter
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input("Search in prompts or responses:")
            
        with col2:
            show_errors_only = st.checkbox("Show failed calls only")
        
        # Filter data based on search
        filtered_df = df.copy()
        
        if search_term:
            mask = (
                filtered_df['system_prompt'].str.contains(search_term, case=False, na=False) |
                filtered_df['user_prompt'].str.contains(search_term, case=False, na=False) |
                filtered_df['raw_response'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        if show_errors_only:
            filtered_df = filtered_df[filtered_df['success'] == 0]
        
        # Display detailed table
        st.subheader(f"Call Details ({len(filtered_df)} records)")
        
        # Select columns to display
        display_columns = st.multiselect(
            "Select columns to display:",
            options=['timestamp', 'experiment_name', 'provider', 'model_name', 'template_type', 
                    'success', 'duration_seconds', 'total_tokens', 'cost_usd', 'triples_count', 'error_message'],
            default=['timestamp', 'experiment_name', 'provider', 'template_type', 'success', 'cost_usd']
        )
        
        if display_columns:
            st.dataframe(
                filtered_df[display_columns].sort_values('timestamp', ascending=False),
                use_container_width=True
            )
        
        # Individual call details
        if len(filtered_df) > 0:
            st.subheader("🔍 Individual Call Details")
            
            selected_call = st.selectbox(
                "Select a call to examine:",
                options=range(len(filtered_df)),
                format_func=lambda x: f"{filtered_df.iloc[x]['timestamp']} - {filtered_df.iloc[x]['template_type']} ({filtered_df.iloc[x]['provider']})"
            )
            
            if selected_call is not None:
                call_data = filtered_df.iloc[selected_call]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**System Prompt:**")
                    st.text_area("", value=call_data['system_prompt'] or "", height=200, key="system_prompt")
                    
                    st.write("**User Prompt:**")
                    st.text_area("", value=call_data['user_prompt'] or "", height=200, key="user_prompt")
                
                with col2:
                    st.write("**Response:**")
                    st.text_area("", value=call_data['raw_response'] or "", height=200, key="response")
                    
                    if call_data['triples_count'] > 0:
                        st.write("**Extracted Triples:**")
                        triples = call_data['parsed_triples_parsed']
                        if triples:
                            for i, triple in enumerate(triples):
                                if isinstance(triple, list) and len(triple) >= 3:
                                    st.write(f"{i+1}. [{triple[0]}] → {triple[1]} → [{triple[2]}]")
                    
                    if not call_data['success'] and call_data['error_message']:
                        st.error(f"Error: {call_data['error_message']}")

if __name__ == "__main__":
    main()