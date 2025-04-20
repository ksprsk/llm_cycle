import streamlit as st
import os
import json
import datetime
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Import our existing classes (assuming they're in main.py)
from main import AIModel, HistoryManager, AIDebate

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="AI Debate System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if "debate" not in st.session_state:
    st.session_state.debate = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "debate_running" not in st.session_state:
    st.session_state.debate_running = False
if "config_path" not in st.session_state:
    st.session_state.config_path = "config.json"
if "history_manager" not in st.session_state:
    st.session_state.history_manager = HistoryManager()


def initialize_debate(config_path="config.json"):
    """Initialize a new debate instance"""
    debate = AIDebate(config_path=config_path)
    st.session_state.debate = debate
    st.session_state.messages = debate.messages.copy()
    st.session_state.current_session_id = debate.session_id
    st.session_state.debate_running = True
    return debate


def run_debate_round(user_input):
    """Run a single debate round and update UI"""
    if not st.session_state.debate:
        initialize_debate(st.session_state.config_path)
    
    # Add user input to messages for display
    st.session_state.messages.append({
        "role": "input",
        "content": user_input
    })
    
    # Run the debate round
    with st.spinner("AIs are thinking..."):
        responses = st.session_state.debate.run_single_debate(user_input)
    
    # Update our copy of messages
    st.session_state.messages = st.session_state.debate.messages.copy()


def load_debate_session(filepath):
    """Load an existing debate session"""
    try:
        # Load the debate data
        debate_data = st.session_state.history_manager.load_debate(filepath)
        
        # Create a new debate instance
        debate = initialize_debate(st.session_state.config_path)
        
        # Override the session ID and messages
        debate.session_id = debate_data.get("session_id", str(uuid.uuid4()))
        debate.messages = debate_data.get("messages", [])
        
        # Update session state
        st.session_state.current_session_id = debate.session_id
        st.session_state.messages = debate.messages.copy()
        
        st.success(f"Loaded debate session from {Path(filepath).name}")
        return True
    except Exception as e:
        st.error(f"Error loading debate: {str(e)}")
        return False


def search_debates():
    """Search for debates and display results"""
    keyword = st.sidebar.text_input("Search keyword")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From date", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("To date", datetime.date.today())
    
    if st.sidebar.button("Search"):
        results = st.session_state.history_manager.search_debates(
            keyword=keyword if keyword else None,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None
        )
        
        if results:
            st.sidebar.write(f"Found {len(results)} debates:")
            
            # Display results with load buttons
            for i, filepath in enumerate(results):
                debate_data = st.session_state.history_manager.load_debate(filepath)
                
                # Find first user input
                user_input = "N/A"
                timestamp = debate_data.get("timestamp", "Unknown")
                for msg in debate_data.get("messages", []):
                    if msg.get("role") == "input":
                        user_input = msg.get("content", "N/A")
                        break
                
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    st.write(f"**{timestamp}**  \n{user_input[:50]}...")
                with col2:
                    if st.button("Load", key=f"load_{i}"):
                        load_debate_session(filepath)
        else:
            st.sidebar.write("No debates found matching your criteria.")


def render_message(msg):
    """Render a message with appropriate styling"""
    role = msg.get("role")
    content = msg.get("content", "")
    
    if role == "system":
        # Don't display system messages
        return
    
    if role == "input":
        st.markdown("### 🧑 User")
        st.write(content)
    else:
        # AI model response
        st.markdown(f"### 🤖 {role}")
        st.write(content)
    
    # Add a separator
    st.markdown("---")


def main():
    # Title
    st.title("AI Debate System")
    
    # Sidebar
    st.sidebar.title("Controls")
    
    # Config selection
    config_files = list(Path(".").glob("*.json"))
    config_options = [f.name for f in config_files]
    if config_options:
        selected_config = st.sidebar.selectbox(
            "Select configuration file",
            config_options,
            index=config_options.index("config.json") if "config.json" in config_options else 0
        )
        st.session_state.config_path = selected_config
    
    # New debate button
    if st.sidebar.button("Start New Debate"):
        initialize_debate(st.session_state.config_path)
        st.rerun()
    
    # Search functionality
    st.sidebar.markdown("## Search Previous Debates")
    search_debates()
    
    # Main content area
    if st.session_state.debate_running:
        # Display current session ID
        st.caption(f"Session ID: {st.session_state.current_session_id}")
        
        # Display loaded models
        if st.session_state.debate:
            model_names = [model.name for model in st.session_state.debate.models]
            st.write(f"Loaded models: {', '.join(model_names)}")
        
        # Display messages
        for msg in st.session_state.messages:
            render_message(msg)
        
        # Input area
        user_input = st.text_area("Enter your question:", height=100)
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Submit"):
                if user_input:
                    run_debate_round(user_input)
                    st.rerun()
    else:
        # No active debate
        st.info("Start a new debate or load an existing one from the sidebar.")
        
        # Quick start option
        sample_questions = [
            "How can we solve climate change?",
            "What's the best way to learn a new language?",
            "Explain the concept of quantum computing.",
            "Design a smart city of the future."
        ]
        
        st.write("### Quick Start")
        st.write("Select a sample question to begin:")
        
        cols = st.columns(2)
        for i, question in enumerate(sample_questions):
            with cols[i % 2]:
                if st.button(question):
                    initialize_debate(st.session_state.config_path)
                    run_debate_round(question)
                    st.rerun()


if __name__ == "__main__":
    main()