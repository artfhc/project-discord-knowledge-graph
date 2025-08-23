#!/usr/bin/env python3
"""
Test script to verify database connection and data availability.
"""

import sqlite3
import sys
from pathlib import Path
from config import get_database_path

def test_database_connection():
    """Test connection to the LLM calls database."""
    
    print("🧪 Testing LLM Evaluation Dashboard Database Connection")
    print("=" * 60)
    
    # Get database path
    db_path = get_database_path()
    print(f"📁 Database path: {db_path}")
    
    # Check if file exists
    if not Path(db_path).exists():
        print("❌ Database file not found!")
        print(f"   Expected location: {Path(db_path).absolute()}")
        print("\n💡 To create data:")
        print("   1. Set ENABLE_LLM_RECORDING=true")
        print("   2. Run your extraction: python extractor_langgraph.py ...")
        print("   3. Check that bin/llm_evaluation/llm_calls.db is created")
        return False
    
    print("✅ Database file exists")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        print("✅ Database connection successful")
        
        # Check table structure
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📊 Tables found: {[table[0] for table in tables]}")
        
        if ('llm_calls',) not in tables:
            print("❌ llm_calls table not found!")
            conn.close()
            return False
        
        # Check data availability
        cursor = conn.execute("SELECT COUNT(*) FROM llm_calls;")
        total_calls = cursor.fetchone()[0]
        print(f"📈 Total LLM calls recorded: {total_calls}")
        
        if total_calls == 0:
            print("⚠️  No LLM calls found in database")
            print("   Run some extractions with ENABLE_LLM_RECORDING=true to generate data")
            conn.close()
            return False
        
        # Get some basic statistics
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                COUNT(DISTINCT provider) as providers,
                COUNT(DISTINCT template_type) as templates,
                COUNT(DISTINCT experiment_name) as experiments,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                SUM(cost_usd) as total_cost,
                SUM(total_tokens) as total_tokens
            FROM llm_calls
        """)
        
        stats = cursor.fetchone()
        
        print(f"\n📊 Database Statistics:")
        print(f"   • Total calls: {stats[0]:,}")
        print(f"   • Successful calls: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   • Unique providers: {stats[2]}")
        print(f"   • Template types: {stats[3]}")
        print(f"   • Experiments: {stats[4]}")
        print(f"   • Date range: {stats[5]} to {stats[6]}")
        print(f"   • Total cost: ${stats[7]:.4f}")
        print(f"   • Total tokens: {stats[8]:,}")
        
        # Check recent activity
        cursor = conn.execute("""
            SELECT COUNT(*) FROM llm_calls 
            WHERE datetime(timestamp) > datetime('now', '-24 hours')
        """)
        recent_calls = cursor.fetchone()[0]
        print(f"   • Recent calls (24h): {recent_calls:,}")
        
        # Sample some records
        cursor = conn.execute("""
            SELECT timestamp, provider, template_type, success, cost_usd 
            FROM llm_calls 
            ORDER BY timestamp DESC 
            LIMIT 3
        """)
        
        recent_records = cursor.fetchall()
        if recent_records:
            print(f"\n🔍 Recent Records (sample):")
            for record in recent_records:
                status = "✅" if record[3] else "❌"
                print(f"   {status} {record[0]} | {record[1]} | {record[2]} | ${record[4]:.4f}")
        
        conn.close()
        
        print(f"\n🎉 Database test completed successfully!")
        print(f"📊 Dashboard ready to launch!")
        print(f"\n🚀 To start the dashboard:")
        print(f"   cd {Path(__file__).parent}")
        print(f"   ./run_dashboard.sh")
        print(f"   # OR")
        print(f"   streamlit run llm_evaluation_app.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)