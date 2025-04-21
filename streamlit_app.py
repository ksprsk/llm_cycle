import streamlit as st
import os
import json
import datetime
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Import our existing classes
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
if "load_filepath" not in st.session_state:
    st.session_state.load_filepath = None


# Helper function to load JSON file
def load_json_file(filepath):
    """
    Load and parse a JSON file.
    
    Args:
        filepath (str): Path to the JSON file
        
    Returns:
        dict: Parsed JSON data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def set_load_filepath(filepath):
    """Set the filepath to load in session state"""
    st.session_state.load_filepath = filepath


def load_debate_session(filepath=None):
    """Load an existing debate session"""
    # Use filepath from arguments or from session state
    filepath = filepath or st.session_state.load_filepath
    
    if not filepath:
        st.error("No filepath specified for loading")
        return False
    
    try:
        # Load the debate data using our helper function
        debate_data = load_json_file(filepath)
        
        # Create a new debate instance
        debate = initialize_debate(st.session_state.config_path)
        
        # Override the session ID and messages
        debate.session_id = debate_data.get("session_id", str(uuid.uuid4()))
        debate.messages = debate_data.get("messages", [])
        
        # Update session state
        st.session_state.current_session_id = debate.session_id
        st.session_state.messages = debate.messages.copy()
        st.session_state.debate_running = True
        st.session_state.load_filepath = None  # Clear after successful load
        
        return True
    except Exception as e:
        st.error(f"Error loading debate: {str(e)}")
        st.session_state.load_filepath = None  # Clear on error
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
                try:
                    # Load debate data directly using our helper function
                    debate_data = load_json_file(filepath)
                    
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
                        if st.button("Load", key=f"load_{i}", on_click=set_load_filepath, args=(filepath,)):
                            pass  # The on_click callback handles setting the filepath
                except Exception as e:
                    st.sidebar.write(f"Error loading file {filepath}: {str(e)}")
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

    # Check if we need to load a debate from a previous click
    if st.session_state.load_filepath:
        success = load_debate_session()
        if success:
            st.success(f"Loaded debate session!")
            st.rerun()

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

    # 대화 기록 관리
    st.sidebar.markdown("## Debate History")
    
    # 기록 접근 방식을 위한 탭 생성
    tab1, tab2 = st.sidebar.tabs(["Recent Debates", "Search"])
    
    with tab1:
        # 시간순 대화 목록 표시
        if "recent_debates" not in st.session_state:
            st.session_state.recent_debates = st.session_state.history_manager.list_all_debates(limit=10)
        
        if st.button("Refresh List", key="refresh_recent"):
            st.session_state.recent_debates = st.session_state.history_manager.list_all_debates(limit=10)
            st.rerun()
        
        for i, (filepath, session_id, timestamp, preview) in enumerate(st.session_state.recent_debates):
            with st.expander(f"{timestamp} - {preview[:30]}..."):
                st.write(f"Session ID: {session_id}")
                st.write(f"Preview: {preview}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Load", key=f"load_recent_{i}", on_click=set_load_filepath, args=(filepath,)):
                        pass
                with col2:
                    if st.button("Delete", key=f"delete_recent_{i}"):
                        if st.session_state.history_manager.delete_debate_file(filepath):
                            st.success("Debate deleted")
                            st.session_state.recent_debates = st.session_state.history_manager.list_all_debates(limit=10)
                            st.rerun()
                        else:
                            st.error("Failed to delete debate")
    
    with tab2:
        # 검색 기능
        search_debates()

    # 메인 컨텐츠 영역
    if st.session_state.debate_running:
        # 현재 세션 ID 표시
        st.caption(f"Session ID: {st.session_state.current_session_id}")

        # 로드된 모델 표시
        if st.session_state.debate:
            model_names = [model.name for model in st.session_state.debate.models]
            st.write(f"Loaded models: {', '.join(model_names)}")

        # 삭제 버튼과 함께 메시지 표시
        for i, msg in enumerate(st.session_state.messages):
            with st.container():
                col1, col2 = st.columns([10, 1])
                
                with col1:
                    render_message(msg)
                
                with col2:
                    # 시스템 메시지가 아닌 경우에만 삭제 버튼 표시
                    if msg.get("role") != "system":
                        if st.button("🗑️", key=f"delete_msg_{i}"):
                            # 메시지 삭제
                            if st.session_state.history_manager.delete_message(
                                st.session_state.current_session_id, i
                            ):
                                # 현재 표시에서 제거
                                st.session_state.messages.pop(i)
                                # debate 객체도 업데이트
                                if st.session_state.debate:
                                    st.session_state.debate.messages = st.session_state.messages.copy()
                                st.success("Message deleted")
                                st.rerun()
                            else:
                                st.error("Failed to delete message")

        # 입력 영역
        user_input = st.text_area("Enter your question:", height=100)
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Submit"):
                if user_input:
                    run_debate_round(user_input)
                    st.rerun()
    else:
        # 활성화된 대화가 없는 경우
        st.info("Start a new debate or load an existing one from the sidebar.")

        # 빠른 시작 옵션
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