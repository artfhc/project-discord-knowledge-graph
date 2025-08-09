"""Streamlit frontend for visualization and exploration"""

import streamlit as st
import pandas as pd

def main():
    """Main Streamlit application"""
    st.title("Discord Knowledge Graph Explorer")
    
    st.sidebar.header("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Overview", "Graph Query", "Statistics"])
    
    if page == "Overview":
        show_overview()
    elif page == "Graph Query":
        show_graph_query()
    elif page == "Statistics":
        show_statistics()

def show_overview():
    """Overview page"""
    st.header("System Overview")
    
    # TODO: Show system status, recent activity
    st.info("Pipeline status and recent activity will be shown here")

def show_graph_query():
    """Graph query interface"""
    st.header("Query Knowledge Graph")
    
    # TODO: Cypher query interface
    query = st.text_area("Enter Cypher query:")
    
    if st.button("Execute Query"):
        # TODO: Execute query and display results
        st.info("Query results will be shown here")

def show_statistics():
    """Statistics dashboard"""
    st.header("Pipeline Statistics")
    
    # TODO: Show processing stats, node counts, etc.
    st.info("Processing statistics will be shown here")

if __name__ == "__main__":
    main()