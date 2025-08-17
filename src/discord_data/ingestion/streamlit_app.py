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
def load_discord_data(uploaded_file):
    """Load and parse Discord export JSON data"""
    if uploaded_file is None:
        return None
    
    try:
        data = json.load(uploaded_file)
        return data
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
    # Clear cache if needed (can remove this line after first run)
    st.cache_data.clear()
    
    st.title("📊 Discord Embeds Analysis")
    st.markdown("Analysis of embed data from Discord export")
    
    # File upload section
    st.header("📁 Data Source")
    uploaded_file = st.file_uploader(
        "Upload Discord export JSON file",
        type=['json'],
        help="Upload a Discord export JSON file to analyze embed data"
    )
    
    # Load data
    with st.spinner("Loading Discord data..."):
        discord_data = load_discord_data(uploaded_file)
    
    if discord_data is None:
        if uploaded_file is None:
            st.info("👆 Please upload a Discord export JSON file to begin analysis")
        st.stop()
    
    # Extract embeds
    with st.spinner("Processing embeds..."):
        embeds_df = extract_embeds_data(discord_data)
    
    if embeds_df.empty:
        st.warning("No embed data found in the Discord export.")
        st.stop()
    
    # Sidebar filters and pagination
    st.sidebar.header("🔍 Filters")
    
    # Name filter (search in strategy titles)
    name_filter = st.sidebar.text_input(
        "🔍 Search Strategy Names",
        placeholder="Type to search strategy titles...",
        help="Filter strategies by name/title"
    )
    
    # Field Author filter (if it exists)
    if 'field_author' in embeds_df.columns:
        field_authors = embeds_df['field_author'].dropna().unique()
        if len(field_authors) > 0:
            # Add "All Authors" option at the beginning
            field_authors_options = ["All Authors"] + sorted(field_authors.tolist())
            selected_field_author = st.sidebar.selectbox(
                "Strategy Author",
                field_authors_options,
                index=0  # Default to "All Authors"
            )
            
            # Convert selection to list for filtering logic
            if selected_field_author == "All Authors":
                selected_field_authors = field_authors.tolist()
            else:
                selected_field_authors = [selected_field_author]
        else:
            selected_field_authors = []
    else:
        selected_field_authors = []
    
    st.sidebar.header("📄 Table Options")
    
    # Pagination options in sidebar
    show_urls = st.sidebar.checkbox("Show URLs", value=True)
    page_size = st.sidebar.selectbox("Rows per page", [10, 25, 50, 100], index=1)
    sort_by = st.sidebar.selectbox("Sort by", ['timestamp', 'author_name', 'total_reactions'], index=0)
    
    # Initialize page number if not exists
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1
    
    # Apply filters sequentially
    filtered_df = embeds_df.copy()
    
    # Apply name filter first
    if name_filter.strip():
        if 'embed_title' in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df['embed_title'].str.contains(name_filter, case=False, na=False)
            ]
    
    # Apply field_author filter
    if 'field_author' in filtered_df.columns and selected_field_authors:
        filtered_df = filtered_df[filtered_df['field_author'].isin(selected_field_authors)]
    
    # Date range filter (only if timestamps were successfully parsed)
    if 'timestamp' in filtered_df.columns and 'date' in filtered_df.columns and filtered_df['timestamp'].notna().any():
        try:
            min_date = filtered_df['timestamp'].min().date()
            max_date = filtered_df['timestamp'].max().date()
            
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df['date'] >= start_date) &
                    (filtered_df['date'] <= end_date)
                ]
        except Exception:
            # Keep current filtered_df if date filtering fails
            pass
    
    # Main content
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Embeds", len(filtered_df))
    with col2:
        if 'field_author' in filtered_df.columns:
            st.metric("Unique Strategy Authors", filtered_df['field_author'].nunique())
        else:
            st.metric("Unique Authors", filtered_df['author_name'].nunique())
    with col3:
        st.metric("Bot Messages", filtered_df['author_is_bot'].sum())
    with col4:
        st.metric("Total Reactions", filtered_df['total_reactions'].sum())
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Embed Table", "📈 Analytics", "🔗 Strategy Links", "⏰ Timeline"])
    
    with tab1:
        st.subheader("Embed Data Table")
        
        # Select columns to display
        display_columns = ['timestamp', 'embed_title']
        if show_urls:
            display_columns.append('embed_url')
        
        # Add field columns if they exist
        field_columns = [col for col in filtered_df.columns if col.startswith('field_')]
        if field_columns:
            display_columns.extend(field_columns)
        
        display_columns.extend(['total_reactions', 'reaction_count'])
        
        # Filter columns that exist in the dataframe
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        
        # Sort the dataframe
        if sort_by in filtered_df.columns:
            sorted_df = filtered_df.sort_values(sort_by, ascending=False)
        else:
            sorted_df = filtered_df
        
        # Pagination logic
        total_rows = len(sorted_df)
        total_pages = (total_rows + page_size - 1) // page_size  # Ceiling division
        
        # Add pagination navigation to sidebar if multiple pages
        if total_pages > 1:
            st.sidebar.header("📖 Navigation")
            
            # Page navigation buttons in sidebar
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("⬅️ First", key="first_btn"):
                    st.session_state.page_num = 1
                    st.rerun()
                if st.button("◀️ Prev", key="prev_btn"):
                    st.session_state.page_num = max(1, st.session_state.page_num - 1)
                    st.rerun()
            
            with col2:
                if st.button("▶️ Next", key="next_btn"):
                    st.session_state.page_num = min(total_pages, st.session_state.page_num + 1)
                    st.rerun()
                if st.button("➡️ Last", key="last_btn"):
                    st.session_state.page_num = total_pages
                    st.rerun()
            
            # Page number input in sidebar
            page_num = st.sidebar.number_input(
                f"Page (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.page_num,
                key="sidebar_page_input"
            )
            if page_num != st.session_state.page_num:
                st.session_state.page_num = page_num
                st.rerun()
            
            st.sidebar.caption(f"Total: {total_pages} pages")
            
            # Display current page info
            start_idx = (st.session_state.page_num - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            st.caption(f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}")
            
            # Get current page data
            current_page_df = sorted_df.iloc[start_idx:end_idx]
        else:
            # If only one page, show all data
            st.session_state.page_num = 1
            current_page_df = sorted_df
            st.caption(f"Showing all {total_rows} rows")
        
        # Prepare display dataframe with clickable links
        display_df = current_page_df[available_columns].copy()
        
        # Display the table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "embed_url": st.column_config.LinkColumn(
                    "Strategy Link",
                    help="Click to open strategy on Composer",
                    display_text="Open Strategy"
                ) if show_urls and 'embed_url' in display_df.columns else None,
                "embed_title": st.column_config.TextColumn("Title", width="large"),
                "field_author": st.column_config.TextColumn("Strategy Author", width="medium"),
                "timestamp": st.column_config.DatetimeColumn("Date", width="medium"),
                "total_reactions": st.column_config.NumberColumn("Reactions", width="small")
            }
        )
    
    with tab2:
        st.subheader("📈 Analytics Dashboard")
        
        if not filtered_df.empty:
            # Posts by strategy author
            if 'field_author' in filtered_df.columns:
                field_author_counts = filtered_df['field_author'].value_counts().head(10)
                fig1 = px.bar(
                    field_author_counts,
                    title="Top 10 Strategy Authors by Embed Count",
                    labels={'index': 'Strategy Author', 'value': 'Embed Count'}
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                # Fallback to regular author if field_author doesn't exist
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
            
            # Prepare strategy table with clickable links
            strategy_display_df = url_embeds.sort_values('timestamp', ascending=False).copy()
            
            # Select and rename columns for better display
            strategy_columns = ['embed_title', 'field_author', 'embed_url', 'timestamp', 'total_reactions']
            available_strategy_columns = [col for col in strategy_columns if col in strategy_display_df.columns]
            
            st.dataframe(
                strategy_display_df[available_strategy_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "embed_url": st.column_config.LinkColumn(
                        "Strategy Link",
                        help="Click to open strategy on Composer",
                        display_text="Open Strategy"
                    ),
                    "embed_title": st.column_config.TextColumn("Strategy Name", width="large"),
                    "field_author": st.column_config.TextColumn("Creator", width="medium"),
                    "timestamp": st.column_config.DatetimeColumn("Posted Date", width="medium"),
                    "total_reactions": st.column_config.NumberColumn("Reactions", width="small")
                }
            )
        else:
            st.info("No embeds with URLs found in the filtered data.")
    
    with tab4:
        st.subheader("⏰ Timeline Analysis")
        
        if 'hour' in filtered_df.columns:
            # Posts by hour
            hourly_counts = filtered_df['hour'].value_counts().sort_index()
            hourly_df = pd.DataFrame({
                'Hour': hourly_counts.index,
                'Number of Embeds': hourly_counts.values
            })
            fig5 = px.bar(
                hourly_df,
                x='Hour',
                y='Number of Embeds',
                title="Embed Posts by Hour of Day"
            )
            st.plotly_chart(fig5, use_container_width=True)
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_embeds = filtered_df.sort_values('timestamp', ascending=False).head(10)
        
        for _, embed in recent_embeds.iterrows():
            # Handle timestamp formatting safely
            try:
                timestamp_str = embed['timestamp'].strftime('%Y-%m-%d %H:%M') if pd.notna(embed['timestamp']) else "Unknown date"
            except:
                timestamp_str = str(embed['timestamp']) if pd.notna(embed['timestamp']) else "Unknown date"
            
            with st.expander(f"🕐 {timestamp_str} - {embed['embed_title'][:50]}..."):
                st.write(f"**Title:** {embed['embed_title']}")
                if 'field_author' in embed and pd.notna(embed['field_author']):
                    st.write(f"**Strategy Author:** {embed['field_author']}")
                if embed.get('embed_url'):
                    st.markdown(f"**URL:** [Open Strategy]({embed['embed_url']})")
                if embed.get('total_reactions', 0) > 0:
                    st.write(f"**Reactions:** {embed['total_reactions']}")
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Discord Data Analysis")

if __name__ == "__main__":
    main()