import streamlit as st
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Discord Embeds Analysis",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_discord_data():
    """Load and parse Discord export JSON data"""
    data_path = "data/discord_new-symphony-alert_data.json"
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Data file not found: {data_path}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON: {e}")
        return None

@st.cache_data
def extract_embeds_data(discord_data):
    """Extract embed data from Discord messages"""
    if not discord_data or 'messages' not in discord_data:
        return pd.DataFrame()
    
    embeds_list = []
    
    for message in discord_data['messages']:
        if message.get('embeds'):
            for embed in message['embeds']:
                embed_data = {
                    'message_id': message['id'],
                    'timestamp': message['timestamp'],
                    'author_name': message['author']['name'],
                    'author_is_bot': message['author']['isBot'],
                    'embed_title': embed.get('title', ''),
                    'embed_url': embed.get('url', ''),
                    'embed_description': embed.get('description', ''),
                    'embed_color': embed.get('color', ''),
                    'embed_timestamp': embed.get('timestamp', ''),
                    'reaction_count': len(message.get('reactions', [])),
                    'total_reactions': sum(r.get('count', 0) for r in message.get('reactions', []))
                }
                
                # Extract embed fields
                fields = embed.get('fields', [])
                for field in fields:
                    field_name = field.get('name', '').lower().replace(' ', '_')
                    embed_data[f'field_{field_name}'] = field.get('value', '')
                
                # Extract footer info
                footer = embed.get('footer', {})
                embed_data['footer_text'] = footer.get('text', '')
                
                embeds_list.append(embed_data)
    
    df = pd.DataFrame(embeds_list)
    
    # Convert timestamps
    if not df.empty and 'timestamp' in df.columns:
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            # Only process dates if conversion was successful
            if df['timestamp'].notna().any():
                df['date'] = df['timestamp'].dt.date
                df['hour'] = df['timestamp'].dt.hour
        except Exception as e:
            st.warning(f"Error parsing timestamps: {e}")
            # Keep timestamp as string if conversion fails
    
    return df

def main():
    st.title("📊 Discord Embeds Analysis")
    st.markdown("Analysis of embed data from Discord export")
    
    # Load data
    with st.spinner("Loading Discord data..."):
        discord_data = load_discord_data()
    
    if discord_data is None:
        st.stop()
    
    # Extract embeds
    with st.spinner("Processing embeds..."):
        embeds_df = extract_embeds_data(discord_data)
    
    if embeds_df.empty:
        st.warning("No embed data found in the Discord export.")
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Author filter
    authors = embeds_df['author_name'].unique()
    selected_authors = st.sidebar.multiselect(
        "Select Authors",
        authors,
        default=authors
    )
    
    # Date range filter (only if timestamps were successfully parsed)
    if 'timestamp' in embeds_df.columns and 'date' in embeds_df.columns and embeds_df['timestamp'].notna().any():
        try:
            min_date = embeds_df['timestamp'].min().date()
            max_date = embeds_df['timestamp'].max().date()
            
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = embeds_df[
                    (embeds_df['author_name'].isin(selected_authors)) &
                    (embeds_df['date'] >= start_date) &
                    (embeds_df['date'] <= end_date)
                ]
            else:
                filtered_df = embeds_df[embeds_df['author_name'].isin(selected_authors)]
        except Exception:
            # Fall back to author filter only if date filtering fails
            filtered_df = embeds_df[embeds_df['author_name'].isin(selected_authors)]
    else:
        filtered_df = embeds_df[embeds_df['author_name'].isin(selected_authors)]
    
    # Main content
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Embeds", len(filtered_df))
    with col2:
        st.metric("Unique Authors", filtered_df['author_name'].nunique())
    with col3:
        st.metric("Bot Messages", filtered_df['author_is_bot'].sum())
    with col4:
        st.metric("Total Reactions", filtered_df['total_reactions'].sum())
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Embed Table", "📈 Analytics", "🔗 Strategy Links", "⏰ Timeline"])
    
    with tab1:
        st.subheader("Embed Data Table")
        
        # Display options
        col1, col2 = st.columns(2)
        with col1:
            show_urls = st.checkbox("Show URLs", value=False)
        with col2:
            page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
        
        # Select columns to display
        display_columns = ['timestamp', 'author_name', 'embed_title', 'embed_description']
        if show_urls:
            display_columns.append('embed_url')
        
        # Add field columns if they exist
        field_columns = [col for col in filtered_df.columns if col.startswith('field_')]
        if field_columns:
            display_columns.extend(field_columns)
        
        display_columns.extend(['total_reactions', 'reaction_count'])
        
        # Filter columns that exist in the dataframe
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_columns].head(page_size),
            use_container_width=True,
            hide_index=True
        )
    
    with tab2:
        st.subheader("📈 Analytics Dashboard")
        
        if not filtered_df.empty:
            # Posts by author
            fig1 = px.bar(
                filtered_df['author_name'].value_counts().head(10),
                title="Top 10 Authors by Embed Count",
                labels={'index': 'Author', 'value': 'Embed Count'}
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Posts over time
            if 'date' in filtered_df.columns:
                daily_counts = filtered_df.groupby('date').size().reset_index(name='count')
                fig2 = px.line(
                    daily_counts,
                    x='date',
                    y='count',
                    title="Embeds Posted Over Time"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Reaction analysis
            if filtered_df['total_reactions'].sum() > 0:
                reaction_df = filtered_df[filtered_df['total_reactions'] > 0]
                fig3 = px.histogram(
                    reaction_df,
                    x='total_reactions',
                    title="Distribution of Reactions per Embed",
                    nbins=20
                )
                st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        st.subheader("🔗 Strategy Links Analysis")
        
        # Filter embeds with URLs
        url_embeds = filtered_df[filtered_df['embed_url'] != ''].copy()
        
        if not url_embeds.empty:
            st.metric("Embeds with URLs", len(url_embeds))
            
            # Extract domain information
            url_embeds['domain'] = url_embeds['embed_url'].apply(
                lambda x: x.split('/')[2] if x and len(x.split('/')) > 2 else 'Unknown'
            )
            
            # Domain distribution
            domain_counts = url_embeds['domain'].value_counts()
            fig4 = px.pie(
                values=domain_counts.values,
                names=domain_counts.index,
                title="Distribution of Link Domains"
            )
            st.plotly_chart(fig4, use_container_width=True)
            
            # Strategy details table
            strategy_columns = ['embed_title', 'embed_url', 'timestamp', 'total_reactions']
            if 'field_author' in url_embeds.columns:
                strategy_columns.append('field_author')
            
            available_strategy_columns = [col for col in strategy_columns if col in url_embeds.columns]
            
            st.subheader("Strategy Details")
            st.dataframe(
                url_embeds[available_strategy_columns].sort_values('timestamp', ascending=False),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No embeds with URLs found in the filtered data.")
    
    with tab4:
        st.subheader("⏰ Timeline Analysis")
        
        if 'hour' in filtered_df.columns:
            # Posts by hour
            hourly_counts = filtered_df['hour'].value_counts().sort_index()
            fig5 = px.bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                title="Embed Posts by Hour of Day",
                labels={'x': 'Hour', 'y': 'Number of Embeds'}
            )
            st.plotly_chart(fig5, use_container_width=True)
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_embeds = filtered_df.sort_values('timestamp', ascending=False).head(10)
        
        for _, embed in recent_embeds.iterrows():
            with st.expander(f"🕐 {embed['timestamp'].strftime('%Y-%m-%d %H:%M')} - {embed['embed_title'][:50]}..."):
                st.write(f"**Author:** {embed['author_name']}")
                st.write(f"**Title:** {embed['embed_title']}")
                st.write(f"**Description:** {embed['embed_description']}")
                if embed['embed_url']:
                    st.write(f"**URL:** {embed['embed_url']}")
                if embed['total_reactions'] > 0:
                    st.write(f"**Reactions:** {embed['total_reactions']}")
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Discord Data Analysis")

if __name__ == "__main__":
    main()