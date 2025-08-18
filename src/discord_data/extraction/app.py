#!/usr/bin/env python3
"""
Discord Knowledge Graph - Extraction Evaluation App

Streamlit app for comparing LLM vs Rule-based extraction outputs.
Provides side-by-side comparison, metrics, and message-level analysis.
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import re

# Page config
st.set_page_config(
    page_title="KG Extraction Evaluator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    margin: 0.5rem 0;
}

.comparison-box {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    background: #f8f9fa;
}

.triple-box {
    border-left: 4px solid #007bff;
    padding: 0.5rem;
    margin: 0.25rem 0;
    background: white;
    border-radius: 4px;
}

.rule-based { border-left-color: #28a745; }
.llm-based { border-left-color: #6f42c1; }

.confidence-high { background: #d4edda; }
.confidence-medium { background: #fff3cd; }
.confidence-low { background: #f8d7da; }
</style>
""", unsafe_allow_html=True)

def load_data_from_files(rule_file, llm_file, messages_file):
    """Load data from user-uploaded files."""
    data = {}
    
    # Load rule-based data
    if rule_file is not None:
        try:
            content = rule_file.read().decode('utf-8')
            data['rule_based'] = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
            st.success(f"✅ Loaded {len(data['rule_based'])} rule-based triples")
        except Exception as e:
            st.error(f"❌ Error loading rule-based file: {e}")
            data['rule_based'] = []
    else:
        data['rule_based'] = []
    
    # Load LLM data
    if llm_file is not None:
        try:
            content = llm_file.read().decode('utf-8')
            data['llm_based'] = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
            st.success(f"✅ Loaded {len(data['llm_based'])} LLM-based triples")
        except Exception as e:
            st.error(f"❌ Error loading LLM file: {e}")
            data['llm_based'] = []
    else:
        data['llm_based'] = []
    
    # Load preprocessed messages data
    if messages_file is not None:
        try:
            content = messages_file.read().decode('utf-8')
            data['messages'] = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
            st.success(f"✅ Loaded {len(data['messages'])} preprocessed messages")
        except Exception as e:
            st.error(f"❌ Error loading preprocessed messages file: {e}")
            data['messages'] = []
    else:
        data['messages'] = []
    
    return data

def load_data_from_local_paths(rule_path, llm_path, messages_path):
    """Load data from local file paths."""
    data = {}
    
    # Load rule-based data
    if rule_path and Path(rule_path).exists():
        try:
            with open(rule_path, 'r') as f:
                data['rule_based'] = [json.loads(line) for line in f if line.strip()]
            st.success(f"✅ Loaded {len(data['rule_based'])} rule-based triples from {rule_path}")
        except Exception as e:
            st.error(f"❌ Error loading rule-based file: {e}")
            data['rule_based'] = []
    else:
        data['rule_based'] = []
    
    # Load LLM data
    if llm_path and Path(llm_path).exists():
        try:
            with open(llm_path, 'r') as f:
                data['llm_based'] = [json.loads(line) for line in f if line.strip()]
            st.success(f"✅ Loaded {len(data['llm_based'])} LLM-based triples from {llm_path}")
        except Exception as e:
            st.error(f"❌ Error loading LLM file: {e}")
            data['llm_based'] = []
    else:
        data['llm_based'] = []
    
    # Load preprocessed messages data
    if messages_path and Path(messages_path).exists():
        try:
            with open(messages_path, 'r') as f:
                data['messages'] = [json.loads(line) for line in f if line.strip()]
            st.success(f"✅ Loaded {len(data['messages'])} preprocessed messages from {messages_path}")
        except Exception as e:
            st.error(f"❌ Error loading preprocessed messages file: {e}")
            data['messages'] = []
    else:
        data['messages'] = []
    
    return data

def get_confidence_class(confidence):
    """Get CSS class based on confidence level."""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"

def get_confidence_color(confidence):
    """Get color for confidence visualization."""
    if confidence >= 0.8:
        return "#28a745"  # Green
    elif confidence >= 0.6:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red

def create_message_index(messages):
    """Create lookup index for messages by ID."""
    if not messages:
        return {}
    return {msg['message_id']: msg for msg in messages}

def create_triple_index(triples, method_name):
    """Create lookup index for triples by message ID."""
    index = defaultdict(list)
    for triple in triples:
        # Add method identifier
        triple['method'] = method_name
        index[triple['message_id']].append(triple)
    return index

def compare_triples_for_message(message_id, rule_triples, llm_triples):
    """Compare triples from both methods for a specific message."""
    comparison = {
        'message_id': message_id,
        'rule_based_count': len(rule_triples),
        'llm_based_count': len(llm_triples),
        'rule_based_triples': rule_triples,
        'llm_based_triples': llm_triples,
        'unique_predicates_rule': set(t['predicate'] for t in rule_triples),
        'unique_predicates_llm': set(t['predicate'] for t in llm_triples),
    }
    
    # Calculate overlap
    all_predicates_rule = [t['predicate'] for t in rule_triples]
    all_predicates_llm = [t['predicate'] for t in llm_triples]
    
    comparison['predicate_overlap'] = len(
        set(all_predicates_rule) & set(all_predicates_llm)
    )
    
    comparison['total_unique_predicates'] = len(
        set(all_predicates_rule) | set(all_predicates_llm)
    )
    
    return comparison

def show_file_import_interface():
    """Show file import interface for users to load their data."""
    
    st.header("📁 Import Data Files")
    st.markdown("Upload your extraction results and original messages to begin comparison.")
    
    # Create tabs for different import methods
    tab1, tab2 = st.tabs(["📤 File Upload", "📂 Local File Paths"])
    
    with tab1:
        st.subheader("Upload Files")
        st.markdown("Upload your JSONL files directly to the app:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Rule-based Results**")
            rule_file = st.file_uploader(
                "Choose rule-based extraction file",
                type=['jsonl', 'json'],
                help="JSONL file containing rule-based extraction triples",
                key="rule_upload"
            )
        
        with col2:
            st.markdown("**LLM Results** (Optional)")
            llm_file = st.file_uploader(
                "Choose LLM extraction file", 
                type=['jsonl', 'json'],
                help="JSONL file containing LLM-based extraction triples",
                key="llm_upload"
            )
        
        with col3:
            st.markdown("**Preprocessed Messages** (Optional)")
            messages_file = st.file_uploader(
                "Choose preprocessed messages file",
                type=['jsonl', 'json'], 
                help="JSONL file containing preprocessed Discord messages (output from step 2)",
                key="messages_upload"
            )
        
        if st.button("📊 Load Uploaded Files", type="primary"):
            if rule_file or llm_file:
                return load_data_from_files(rule_file, llm_file, messages_file)
            else:
                st.error("❌ Please upload at least one extraction file (rule-based or LLM)")
                return None
    
    with tab2:
        st.subheader("Local File Paths")
        st.markdown("Enter paths to local files on your system:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rule_path = st.text_input(
                "Rule-based Results Path",
                placeholder="e.g., /path/to/rule_based_results.jsonl",
                help="Path to rule-based extraction JSONL file"
            )
            
            llm_path = st.text_input(
                "LLM Results Path (Optional)",
                placeholder="e.g., /path/to/llm_results.jsonl", 
                help="Path to LLM-based extraction JSONL file"
            )
        
        with col2:
            messages_path = st.text_input(
                "Preprocessed Messages Path (Optional)",
                placeholder="e.g., /path/to/sample_results.jsonl",
                help="Path to preprocessed messages JSONL file (step 2 output)"
            )
            
            # Quick path suggestions
            st.markdown("**Common Paths:**")
            if st.button("📁 Use Current Directory"):
                st.code("""
Rule-based: ./extraction_rule_based_summary.jsonl
LLM: ./extraction_llm_summary.jsonl  
Preprocessed: ../preprocessing/sample_results.jsonl
                """)
        
        if st.button("📂 Load Local Files", type="primary"):
            if rule_path or llm_path:
                return load_data_from_local_paths(rule_path, llm_path, messages_path)
            else:
                st.error("❌ Please enter at least one file path")
                return None
    
    # Help sections
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📋 Expected File Format", expanded=False):
            st.markdown("**Extraction Files (JSONL format):**")
            st.code("""
{"subject": "user123", "predicate": "asks_about", "object": "DCA strategy", "message_id": "123", "segment_id": "seg1", "timestamp": "2022-09-14T13:32:23.005000+00:00", "confidence": 0.85}
{"subject": "expert456", "predicate": "recommends", "object": "wheel strategy", "message_id": "124", "segment_id": "seg1", "timestamp": "2022-09-14T13:35:23.005000+00:00", "confidence": 0.90}
            """)
            
            st.markdown("**Preprocessed Messages File (JSONL format):**")
            st.code("""
{"message_id": "123", "segment_id": "seg1", "author": "user123", "timestamp": "2022-09-14T13:32:23.005000+00:00", "type": "question", "clean_text": "What's the best DCA strategy?", "channel": "general", "confidence": 0.85}
{"message_id": "124", "segment_id": "seg1", "author": "expert456", "timestamp": "2022-09-14T13:35:23.005000+00:00", "type": "answer", "clean_text": "I recommend starting with the wheel strategy", "channel": "general", "confidence": 0.90}
            """)
    
    with col2:
        with st.expander("📁 Where to Find Files", expanded=False):
            st.markdown("**Rule-based Results:**")
            st.code("""
src/discord_kg/extraction/rule_based/step3_test_results.jsonl
src/discord_data/extraction/extraction_rule_based_summary.jsonl
            """)
            
            st.markdown("**LLM Results:**") 
            st.code("""
src/discord_data/extraction/extraction_llm_summary.jsonl
src/discord_kg/extraction/llm_powered/llm_output.jsonl
            """)
            
            st.markdown("**Preprocessed Messages (Step 2 Output):**")
            st.code("""
src/discord_kg/preprocessing/sample_results.jsonl
src/discord_data/preprocessing/sample_results.jsonl
            """)
            
            st.info("💡 Tip: Preprocessed messages come from Step 2 (classification), extraction files from Step 3")
    
    return None

def main():
    """Main Streamlit app."""
    
    st.title("🔍 Knowledge Graph Extraction Evaluator")
    st.markdown("Compare LLM vs Rule-based extraction outputs side-by-side")
    
    # Initialize session state
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.data = {}
    
    # Show import interface if no data loaded
    if not st.session_state.data_loaded:
        data = show_file_import_interface()
        
        if data is not None:
            st.session_state.data = data
            st.session_state.data_loaded = True
            st.rerun()
        else:
            st.info("👆 Please import your extraction data files to begin analysis")
            return
    
    # Use loaded data
    data = st.session_state.data
    
    # Check what data we have
    has_rule = 'rule_based' in data and data['rule_based']
    has_llm = 'llm_based' in data and data['llm_based'] 
    has_messages = 'messages' in data and data['messages']
    
    # Sidebar with data status and controls
    st.sidebar.header("📊 Data Status")
    st.sidebar.write(f"✅ Rule-based: {len(data.get('rule_based', []))} triples" if has_rule else "❌ Rule-based: Not loaded")
    st.sidebar.write(f"✅ LLM-based: {len(data.get('llm_based', []))} triples" if has_llm else "❌ LLM-based: Not loaded")
    st.sidebar.write(f"✅ Preprocessed messages: {len(data.get('messages', []))} messages" if has_messages else "❌ Preprocessed messages: Not loaded")
    
    # Data management controls
    st.sidebar.header("🔄 Data Management")
    
    if st.sidebar.button("📁 Load Different Files"):
        st.session_state.data_loaded = False
        st.session_state.data = {}
        st.rerun()
    
    if st.sidebar.button("🔄 Reload Current Data"):
        # Reset the data but keep the loaded flag
        st.session_state.data = {}
        st.session_state.data_loaded = False
        st.rerun()
    
    if not has_rule:
        st.warning("⚠️ Only found rule-based results. Generate LLM results to enable full comparison.")
        
    # Create indices
    message_index = create_message_index(data.get('messages', []))
    rule_index = create_triple_index(data.get('rule_based', []), 'rule_based')
    llm_index = create_triple_index(data.get('llm_based', []), 'llm_based') if has_llm else {}
    
    # Sidebar controls
    st.sidebar.header("🎛️ Controls")
    
    view_mode = st.sidebar.selectbox(
        "View Mode",
        ["📈 Overview", "🔍 Message Comparison", "📊 Analytics", "🎯 Quality Analysis"]
    )
    
    # Main content based on view mode
    if view_mode == "📈 Overview":
        show_overview(data, has_rule, has_llm)
        
    elif view_mode == "🔍 Message Comparison":
        show_message_comparison(data, message_index, rule_index, llm_index, has_llm)
        
    elif view_mode == "📊 Analytics":
        show_analytics(data, has_rule, has_llm)
        
    elif view_mode == "🎯 Quality Analysis":
        show_quality_analysis(data, message_index, rule_index, llm_index, has_llm)

def show_overview(data, has_rule, has_llm):
    """Show high-level overview and metrics."""
    
    st.header("📈 Extraction Overview")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        rule_count = len(data.get('rule_based', []))
        st.metric("Rule-based Triples", rule_count)
        
    with col2:
        llm_count = len(data.get('llm_based', []))
        st.metric("LLM-based Triples", llm_count)
        
    with col3:
        message_count = len(data.get('messages', []))
        st.metric("Original Messages", message_count)
        
    with col4:
        if has_rule and has_llm and message_count > 0:
            extraction_rate = ((rule_count + llm_count) / 2) / message_count * 100
            st.metric("Avg Extraction Rate", f"{extraction_rate:.1f}%")
        else:
            st.metric("Avg Extraction Rate", "N/A")
    
    # Method comparison chart
    if has_rule and has_llm:
        st.subheader("📊 Method Comparison")
        
        comparison_data = pd.DataFrame({
            'Method': ['Rule-based', 'LLM-based'],
            'Triple Count': [rule_count, llm_count],
            'Extraction Rate': [
                rule_count / message_count * 100 if message_count > 0 else 0,
                llm_count / message_count * 100 if message_count > 0 else 0
            ]
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                comparison_data, 
                x='Method', 
                y='Triple Count',
                title="Total Triples Extracted",
                color='Method',
                color_discrete_map={'Rule-based': '#28a745', 'LLM-based': '#6f42c1'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            fig = px.bar(
                comparison_data, 
                x='Method', 
                y='Extraction Rate',
                title="Extraction Rate (%)",
                color='Method',
                color_discrete_map={'Rule-based': '#28a745', 'LLM-based': '#6f42c1'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Predicate distribution
    if has_rule:
        st.subheader("🏷️ Predicate Distribution")
        
        rule_predicates = Counter(t['predicate'] for t in data['rule_based'])
        
        if has_llm:
            llm_predicates = Counter(t['predicate'] for t in data['llm_based'])
            
            # Combined predicate chart
            all_predicates = set(rule_predicates.keys()) | set(llm_predicates.keys())
            predicate_comparison = []
            
            for predicate in all_predicates:
                predicate_comparison.append({
                    'Predicate': predicate,
                    'Rule-based': rule_predicates.get(predicate, 0),
                    'LLM-based': llm_predicates.get(predicate, 0)
                })
            
            df_predicates = pd.DataFrame(predicate_comparison)
            
            fig = px.bar(
                df_predicates.melt(id_vars=['Predicate'], var_name='Method', value_name='Count'),
                x='Predicate',
                y='Count',
                color='Method',
                title="Predicate Usage by Method",
                barmode='group',
                color_discrete_map={'Rule-based': '#28a745', 'LLM-based': '#6f42c1'}
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Rule-based only
            pred_df = pd.DataFrame(list(rule_predicates.items()), columns=['Predicate', 'Count'])
            fig = px.bar(pred_df, x='Predicate', y='Count', title="Rule-based Predicate Distribution")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

def show_message_comparison(data, message_index, rule_index, llm_index, has_llm):
    """Show detailed message-level comparison."""
    
    st.header("🔍 Message-Level Comparison")
    
    # Get messages that have extractions
    messages_with_extractions = set(rule_index.keys())
    if has_llm:
        messages_with_extractions.update(llm_index.keys())
    
    if not messages_with_extractions:
        st.error("No messages with extractions found.")
        return
    
    # Message selector
    st.subheader("📝 Select Message")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        filter_type = st.selectbox(
            "Filter by",
            ["All Messages", "Has Rule-based Only", "Has LLM Only", "Has Both", "Message Type"]
        )
    
    with col2:
        if filter_type == "Message Type" and message_index:
            msg_types = set(msg['type'] for msg in message_index.values() if 'type' in msg)
            selected_type = st.selectbox("Message Type", list(msg_types))
        else:
            selected_type = None
    
    # Filter messages
    filtered_messages = []
    for msg_id in messages_with_extractions:
        has_rule = msg_id in rule_index
        has_llm_extract = msg_id in llm_index
        
        include = False
        if filter_type == "All Messages":
            include = True
        elif filter_type == "Has Rule-based Only":
            include = has_rule and not has_llm_extract
        elif filter_type == "Has LLM Only":
            include = not has_rule and has_llm_extract
        elif filter_type == "Has Both":
            include = has_rule and has_llm_extract
        elif filter_type == "Message Type" and selected_type:
            msg = message_index.get(msg_id)
            include = msg and msg.get('type') == selected_type
            
        if include:
            filtered_messages.append(msg_id)
    
    if not filtered_messages:
        st.warning(f"No messages found matching filter: {filter_type}")
        return
    
    # Message selector
    selected_message_id = st.selectbox(
        f"Select Message ({len(filtered_messages)} available)",
        filtered_messages,
        format_func=lambda x: f"{x[:8]}... - {message_index.get(x, {}).get('author', 'Unknown')}: {message_index.get(x, {}).get('clean_text', 'No text')[:50]}..."
    )
    
    if not selected_message_id:
        return
    
    # Show message details
    message = message_index.get(selected_message_id, {})
    rule_triples = rule_index.get(selected_message_id, [])
    llm_triples = llm_index.get(selected_message_id, [])
    
    st.subheader("💬 Preprocessed Message (Step 2 Output)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Author:** {message.get('author', 'Unknown')}")
        st.write(f"**Type:** {message.get('type', 'Unknown')}")
        st.write(f"**Channel:** {message.get('channel', 'Unknown')}")
    
    with col2:
        st.write(f"**Timestamp:** {message.get('timestamp', 'Unknown')}")
        st.write(f"**Segment ID:** {message.get('segment_id', 'Unknown')}")
        if message.get('mentions'):
            st.write(f"**Mentions:** {', '.join(message['mentions'])}")
    
    st.markdown(f"""
    <div class="comparison-box">
        <strong>Content:</strong><br>
        {message.get('clean_text', 'No content available')}
    </div>
    """, unsafe_allow_html=True)
    
    # Show extractions side by side
    st.subheader("🔄 Extraction Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 Rule-based Extraction")
        if rule_triples:
            for i, triple in enumerate(rule_triples):
                conf_class = get_confidence_class(triple['confidence'])
                st.markdown(f"""
                <div class="triple-box rule-based {conf_class}">
                    <strong>Subject:</strong> {triple['subject']}<br>
                    <strong>Predicate:</strong> {triple['predicate']}<br>
                    <strong>Object:</strong> {triple['object']}<br>
                    <strong>Confidence:</strong> {triple['confidence']:.2f}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No rule-based extractions for this message")
    
    with col2:
        st.markdown("### 🟣 LLM-based Extraction")
        if has_llm and llm_triples:
            for i, triple in enumerate(llm_triples):
                conf_class = get_confidence_class(triple['confidence'])
                st.markdown(f"""
                <div class="triple-box llm-based {conf_class}">
                    <strong>Subject:</strong> {triple['subject']}<br>
                    <strong>Predicate:</strong> {triple['predicate']}<br>
                    <strong>Object:</strong> {triple['object']}<br>
                    <strong>Confidence:</strong> {triple['confidence']:.2f}
                </div>
                """, unsafe_allow_html=True)
        elif not has_llm:
            st.info("LLM extractions not available")
        else:
            st.info("No LLM extractions for this message")
    
    # Comparison metrics
    if has_llm:
        st.subheader("📊 Comparison Metrics")
        
        comparison = compare_triples_for_message(selected_message_id, rule_triples, llm_triples)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Rule-based Triples", comparison['rule_based_count'])
        
        with col2:
            st.metric("LLM-based Triples", comparison['llm_based_count'])
        
        with col3:
            if comparison['total_unique_predicates'] > 0:
                overlap_pct = comparison['predicate_overlap'] / comparison['total_unique_predicates'] * 100
                st.metric("Predicate Overlap", f"{overlap_pct:.1f}%")
            else:
                st.metric("Predicate Overlap", "0%")

def show_analytics(data, has_rule, has_llm):
    """Show detailed analytics and insights."""
    
    st.header("📊 Detailed Analytics")
    
    if not has_rule:
        st.error("Rule-based data required for analytics")
        return
    
    # Confidence analysis
    st.subheader("🎯 Confidence Distribution")
    
    rule_confidences = [t['confidence'] for t in data['rule_based']]
    
    if has_llm:
        llm_confidences = [t['confidence'] for t in data['llm_based']]
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Rule-based Confidence', 'LLM-based Confidence'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        fig.add_trace(
            go.Histogram(x=rule_confidences, name="Rule-based", marker_color="#28a745", nbinsx=20),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Histogram(x=llm_confidences, name="LLM-based", marker_color="#6f42c1", nbinsx=20),
            row=1, col=2
        )
        
        fig.update_layout(title_text="Confidence Distribution Comparison", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Rule-based Statistics**")
            st.write(f"Mean: {np.mean(rule_confidences):.3f}")
            st.write(f"Median: {np.median(rule_confidences):.3f}")
            st.write(f"Std Dev: {np.std(rule_confidences):.3f}")
        
        with col2:
            st.markdown("**LLM-based Statistics**")
            st.write(f"Mean: {np.mean(llm_confidences):.3f}")
            st.write(f"Median: {np.median(llm_confidences):.3f}")
            st.write(f"Std Dev: {np.std(llm_confidences):.3f}")
    
    else:
        fig = px.histogram(x=rule_confidences, title="Rule-based Confidence Distribution", nbins=20)
        st.plotly_chart(fig, use_container_width=True)
    
    # Temporal analysis
    if 'messages' in data and data['messages']:
        st.subheader("⏰ Temporal Analysis")
        
        # Group extractions by time
        rule_by_time = defaultdict(int)
        for triple in data['rule_based']:
            try:
                dt = datetime.fromisoformat(triple['timestamp'].replace('Z', '+00:00'))
                date_key = dt.strftime('%Y-%m-%d')
                rule_by_time[date_key] += 1
            except:
                continue
        
        if rule_by_time:
            time_df = pd.DataFrame(list(rule_by_time.items()), columns=['Date', 'Extractions'])
            time_df['Date'] = pd.to_datetime(time_df['Date'])
            time_df = time_df.sort_values('Date')
            
            fig = px.line(time_df, x='Date', y='Extractions', title="Extractions Over Time")
            st.plotly_chart(fig, use_container_width=True)

def show_quality_analysis(data, message_index, rule_index, llm_index, has_llm):
    """Show quality analysis and potential issues."""
    
    st.header("🎯 Quality Analysis")
    
    if not has_llm:
        st.warning("LLM data required for comprehensive quality analysis")
        return
    
    # Quality metrics
    st.subheader("📈 Quality Metrics")
    
    # Calculate message-level comparisons
    comparisons = []
    all_message_ids = set(rule_index.keys()) | set(llm_index.keys())
    
    for msg_id in all_message_ids:
        rule_triples = rule_index.get(msg_id, [])
        llm_triples = llm_index.get(msg_id, [])
        comparison = compare_triples_for_message(msg_id, rule_triples, llm_triples)
        comparisons.append(comparison)
    
    # Aggregate metrics
    total_messages = len(comparisons)
    messages_with_both = sum(1 for c in comparisons if c['rule_based_count'] > 0 and c['llm_based_count'] > 0)
    messages_rule_only = sum(1 for c in comparisons if c['rule_based_count'] > 0 and c['llm_based_count'] == 0)
    messages_llm_only = sum(1 for c in comparisons if c['rule_based_count'] == 0 and c['llm_based_count'] > 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Messages", total_messages)
    
    with col2:
        st.metric("Both Methods", messages_with_both)
    
    with col3:
        st.metric("Rule-based Only", messages_rule_only)
    
    with col4:
        st.metric("LLM Only", messages_llm_only)
    
    # Agreement analysis
    st.subheader("🤝 Method Agreement")
    
    if messages_with_both > 0:
        overlaps = [c['predicate_overlap'] for c in comparisons if c['rule_based_count'] > 0 and c['llm_based_count'] > 0]
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0
        
        st.metric("Average Predicate Overlap", f"{avg_overlap:.1f}")
        
        # Overlap distribution
        fig = px.histogram(x=overlaps, title="Predicate Overlap Distribution", nbins=10)
        st.plotly_chart(fig, use_container_width=True)
    
    # Top disagreements
    st.subheader("⚠️ Top Disagreements")
    
    disagreements = []
    for comparison in comparisons:
        if comparison['rule_based_count'] > 0 and comparison['llm_based_count'] > 0:
            disagreement_score = abs(comparison['rule_based_count'] - comparison['llm_based_count'])
            if disagreement_score > 0:
                disagreements.append({
                    'message_id': comparison['message_id'],
                    'disagreement_score': disagreement_score,
                    'rule_count': comparison['rule_based_count'],
                    'llm_count': comparison['llm_based_count'],
                    'overlap': comparison['predicate_overlap']
                })
    
    if disagreements:
        disagreements.sort(key=lambda x: x['disagreement_score'], reverse=True)
        
        st.write("Messages with highest extraction count differences:")
        for i, d in enumerate(disagreements[:10]):
            msg = message_index.get(d['message_id'], {})
            with st.expander(f"#{i+1} - Message {d['message_id'][:8]}... (Diff: {d['disagreement_score']})"):
                st.write(f"**Content:** {msg.get('clean_text', 'No content')[:200]}...")
                st.write(f"**Rule-based triples:** {d['rule_count']}")
                st.write(f"**LLM triples:** {d['llm_count']}")
                st.write(f"**Overlap:** {d['overlap']}")

if __name__ == "__main__":
    # Import numpy for statistics (with fallback)
    try:
        import numpy as np
    except ImportError:
        # Fallback implementations
        def mean(data):
            return sum(data) / len(data) if data else 0
        def median(data):
            sorted_data = sorted(data)
            n = len(sorted_data)
            return sorted_data[n//2] if n % 2 == 1 else (sorted_data[n//2-1] + sorted_data[n//2]) / 2
        def std(data):
            if not data:
                return 0
            m = mean(data)
            return (sum((x - m) ** 2 for x in data) / len(data)) ** 0.5
        
        # Create a mock numpy module
        class MockNumpy:
            @staticmethod
            def mean(data):
                return mean(data)
            @staticmethod 
            def median(data):
                return median(data)
            @staticmethod
            def std(data):
                return std(data)
        
        np = MockNumpy()
    
    main()