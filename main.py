from openai import OpenAI
import random
import os
import json
import datetime
import uuid
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AIModel:
    def __init__(self, name, model_name, api_key, base_url=None, max_completion_tokens=1000, extra_body=None):
        """
        Initialize an AI model client.
        
        Args:
            name (str): Display name for the model
            model_name (str): Name of the model to use with the API
            api_key (str): API key for authentication
            base_url (str, optional): Base URL for the API
            max_completion_tokens (int, optional): Maximum tokens in completion
            extra_body (dict, optional): Additional parameters for the request
        """
        self.name = name
        self.model_name = model_name
        self.api_key = api_key
        self.max_completion_tokens = max_completion_tokens
        self.extra_body = extra_body or {}
        
        # Initialize the client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
    
    def generate_response(self, messages):
        """
        Generate a response based on the message history.
        
        Args:
            messages (list): List of message dictionaries with role and content
            
        Returns:
            str: Generated response from the AI model
        """
        # Transform messages for API compatibility
        api_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                # Keep system messages as is
                api_messages.append(msg)
            elif msg["role"] == self.name:
                # Messages from this model become assistant messages
                api_messages.append({
                    "role": "assistant",
                    "content": msg["content"]
                })
            else:
                # Messages from other sources (user or other models) become user messages
                # with the source prepended to the content
                source = msg["role"]
                content = msg["content"]
                
                # Only prepend source if it's not already there
                if not content.startswith(f"{source}:"):
                    content = f"{source}: {content}"
                
                api_messages.append({
                    "role": "user",
                    "content": content
                })
        
        # Create the completion request
        kwargs = {
            "model": self.model_name,
            "messages": api_messages,
            "max_completion_tokens": self.max_completion_tokens,
        }
        
        # Add any additional parameters if provided
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        
        try:
            # Generate completion
            completion = self.client.chat.completions.create(**kwargs)
            
            # Return the generated content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating response from {self.name}: {str(e)}")
            return f"[Error] Failed to generate response: {str(e)}"


class HistoryManager:
    def __init__(self, base_dir="debate_history"):
        """
        Initialize a manager for debate history.
        
        Args:
            base_dir (str): Base directory for storing debate history
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True, parents=True)
    
    def save_debate(self, session_id, messages):
        """
        Save a debate session to a file.
        
        Args:
            session_id (str): Unique identifier for the session
            messages (list): Full conversation messages
        
        Returns:
            str: Path to the saved file
        """
        # Generate proper ISO format timestamp
        timestamp_original = datetime.datetime.now().isoformat()
        
        # Create file-safe version for the filename
        timestamp_filename = timestamp_original.replace(':', '-')
        
        # Create the session directory
        session_dir = self.base_dir / session_id
        session_dir.mkdir(exist_ok=True, parents=True)
        
        # Set filename using the file-safe version
        filename = f"{timestamp_filename}.json"
        filepath = session_dir / filename
        
        # Store data with the original ISO format timestamp
        data = {
            "session_id": session_id,
            "timestamp": timestamp_original,  # Store original ISO format
            "messages": messages
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)

    def search_debates(self, keyword=None, start_date=None, end_date=None):
        """
        Search for debates by keyword and/or date range.

        Args:
            keyword (str, optional): Keyword to search for in user input
            start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
            end_date (str, optional): End date in ISO format (YYYY-MM-DD)

        Returns:
            list: List of filepaths to matching debate files
        """
        results = set()  # 중복 방지를 위해 set 사용

        # Convert date strings to datetime objects if provided
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.datetime.fromisoformat(end_date)
            # Set to end of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        # Iterate through all session directories
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Iterate through all debate files in the session
            for debate_file in session_dir.glob("*.json"):
                str_path = str(debate_file)
                
                # 이미 결과에 있으면 건너뛰기
                if str_path in results:
                    continue
                    
                # 날짜 범위 검사
                if start_dt or end_dt:
                    try:
                        with open(debate_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            timestamp = data.get('timestamp', '')

                        if timestamp:
                            try:
                                file_dt = datetime.datetime.fromisoformat(timestamp)
                            except ValueError:
                                parts = timestamp.split('T')
                                if len(parts) == 2:
                                    date_part = parts[0]
                                    time_part = parts[1].replace('-', ':')
                                    file_dt = datetime.datetime.fromisoformat(f"{date_part}T{time_part}")
                                else:
                                    raise ValueError(f"Cannot parse timestamp: {timestamp}")

                            if start_dt and file_dt < start_dt:
                                continue
                            if end_dt and file_dt > end_dt:
                                continue
                    except Exception as e:
                        print(f"Error parsing timestamp for {debate_file}: {e}")
                        continue

                # 키워드 검사
                if keyword:
                    try:
                        debate_data = self.load_debate(debate_file)
                        found = False
                        for msg in debate_data.get("messages", []):
                            if keyword.lower() in msg.get("content", "").lower():
                                found = True
                                break

                        if not found:
                            continue

                    except Exception as e:
                        print(f"Error searching content for {debate_file}: {e}")
                        continue

                results.add(str_path)

        return list(results)  # set을 list로 변환하여 반환
    
    def list_all_debates(self, limit=50):
        """
        List all debate sessions in chronological order (newest first).

        Args:
            limit (int, optional): 반환할 세션의 최대 개수

        Returns:
            list: (filepath, session_id, timestamp, preview) 튜플의 리스트
        """
        all_debates = []

        # 모든 세션 디렉토리 순회
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name

            # 세션 내 모든 대화 파일 순회
            for debate_file in session_dir.glob("*.json"):
                try:
                    # 파일 로드
                    with open(debate_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    timestamp = data.get('timestamp', '')
                    
                    # 첫 사용자 입력을 미리보기로 사용
                    preview = "N/A"
                    for msg in data.get("messages", []):
                        if msg.get("role") == "input":
                            preview = msg.get("content", "")[:100]
                            break
                    
                    # 정렬을 위해 타임스탬프 파싱
                    try:
                        dt = datetime.datetime.fromisoformat(timestamp)
                    except ValueError:
                        # 오래된 형식 처리
                        parts = timestamp.split('T')
                        if len(parts) == 2:
                            date_part = parts[0]
                            time_part = parts[1].replace('-', ':')
                            dt = datetime.datetime.fromisoformat(f"{date_part}T{time_part}")
                        else:
                            dt = datetime.datetime.min
                    
                    all_debates.append((str(debate_file), session_id, timestamp, preview, dt))
                except Exception as e:
                    print(f"Error loading debate file {debate_file}: {e}")
        
        # 타임스탬프로 정렬 (최신순)
        all_debates.sort(key=lambda x: x[4], reverse=True)
        
        # 정렬에 사용된 datetime 객체 없이 결과 반환
        return [(path, sid, ts, prev) for path, sid, ts, prev, _ in all_debates[:limit]]
    
    def delete_message(self, session_id, message_index):
        """
        Delete a specific message from the most recent debate file in a session.

        Args:
            session_id (str): 세션 ID
            message_index (int): 삭제할 메시지의 인덱스

        Returns:
            bool: 성공 시 True, 실패 시 False
        """
        session_dir = self.base_dir / session_id
        if not session_dir.exists() or not session_dir.is_dir():
            return False
        
        # 가장 최근 대화 파일 찾기
        debate_files = list(session_dir.glob("*.json"))
        if not debate_files:
            return False
        
        # 수정 시간순으로 정렬 (최신순)
        debate_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = debate_files[0]
        
        try:
            # 대화 로드
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 메시지 인덱스 유효성 확인
            if message_index < 0 or message_index >= len(data.get("messages", [])):
                return False
            
            # 메시지 제거
            data["messages"].pop(message_index)
            
            # 업데이트된 파일 저장
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False

    def delete_debate_file(self, filepath):
        """
        Delete a specific debate file.

        Args:
            filepath (str): 삭제할 대화 파일 경로

        Returns:
            bool: 성공 시 True, 실패 시 False
        """
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                path.unlink()
                
                # 디렉토리가 비어있으면 제거
                parent_dir = path.parent
                if not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    
                return True
            return False
        except Exception as e:
            print(f"Error deleting debate file: {e}")
            return False


class AIDebate:
    def __init__(self, models=None, config_path="config.json"):
        """
        Initialize an AI debate system with multiple AI models that follows a 
        structured three-phase approach.
        
        Args:
            models (list, optional): List of AIModel instances
            config_path (str, optional): Path to configuration file
        """
        self.models = models or []
        self.history_manager = HistoryManager()
        self.session_id = str(uuid.uuid4())
        self.messages = []
        self.current_phase = None
        
        # If models not provided, load from config
        if not self.models:
            self.load_models_from_config(config_path)
        
        # Base system prompt for all phases
        self.base_prompt = """You are an AI participating in a structured collaborative debate. 
Follow the instructions for your current phase carefully."""

        # Phase-specific prompts
        self.phase_prompts = {
            "propose": """
**Phase 1: Propose (제안)**
* Offer 1-2 core ideas related to the given topic
* Prioritize uniqueness – avoid repeating concepts already presented by others
* Be concise (1-3 sentences per idea)
* Label your response: `[제안]`

Focus on contributing original, valuable ideas while being brief and clear.""",

            "critique": """
**Phase 2: Critique & Refine (비판 및 개선)**
* Review proposals from OTHER participants only
* Identify at least one specific flaw OR suggest a concrete improvement for another's idea
* Be constructive and explain your reasoning briefly
* Label your response: `[피드백]` (On [Target Idea/Participant], Critique/Suggestion: ...)

Focus on strengthening others' ideas through constructive criticism.""",

            "synthesize": """
**Phase 3: Synthesize (종합)**
* Based on the discussion in Phases 1 & 2, construct one concise, improved solution
* Integrate the strongest points and refinements identified
* Acknowledge core contributions briefly if feasible
* Label your response: `[최종안]`

Focus on creating the most effective solution by combining the best elements from the previous phases."""
        }
        
        # Key rules to append to all phase prompts
        self.key_rules = """
**Key Rules:**
* Uniqueness: Strive for distinct contributions in each phase
* Interaction: Phase 2 must engage with others' ideas
* Brevity: Concise responses are highly valued - solutions that are twice as short may receive twice the score

Maintain a helpful, precise, and professional tone at all times."""
    
    def load_models_from_config(self, config_path):
        """
        Load AI models from configuration file.
        
        Args:
            config_path (str): Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for model_config in config.get("models", []):
                # Get API key directly from config
                api_key = model_config.get("api_key")
                
                if not api_key:
                    print(f"Warning: API key not found for {model_config.get('name')}. Skipping model.")
                    continue
                
                # Create model instance
                model = AIModel(
                    name=model_config.get("name", "Unknown"),
                    model_name=model_config.get("model_name"),
                    api_key=api_key,
                    base_url=model_config.get("base_url"),
                    max_completion_tokens=model_config.get("max_completion_tokens", 1000),
                    extra_body=model_config.get("extra_body", {})
                )
                
                self.models.append(model)
            
            print(f"Loaded {len(self.models)} models from config.")
        except Exception as e:
            print(f"Error loading models from config: {str(e)}")
    
    def get_system_prompt(self, phase):
        """
        Generate the appropriate system prompt for the current phase.
        
        Args:
            phase (str): Current debate phase ('propose', 'critique', or 'synthesize')
            
        Returns:
            str: Complete system prompt for the specified phase
        """
        prompt = f"{self.base_prompt}\n\n{self.phase_prompts.get(phase, '')}\n{self.key_rules}"
        return prompt
    
    def run_phase(self, phase, topic=None, previous_messages=None):
        """
        Run a single phase of the debate with all AI models.
        
        Args:
            phase (str): Current debate phase ('propose', 'critique', or 'synthesize')
            topic (str, optional): The debate topic (used for propose phase)
            previous_messages (list, optional): Messages from previous phases
            
        Returns:
            list: List of (model_name, response) tuples for this phase
        """
        self.current_phase = phase
        phase_messages = previous_messages.copy() if previous_messages else []
        
        # Add phase system prompt
        system_prompt = self.get_system_prompt(phase)
        
        # Create phase messages with system prompt
        if phase_messages:
            # Find and replace any existing system messages
            system_replaced = False
            for i, msg in enumerate(phase_messages):
                if msg["role"] == "system":
                    phase_messages[i] = {"role": "system", "content": system_prompt}
                    system_replaced = True
                    break
                    
            if not system_replaced:
                phase_messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            # Initialize with system prompt
            phase_messages = [{"role": "system", "content": system_prompt}]
        
        # For propose phase, add the topic as user input
        if phase == "propose" and topic and not any(msg["role"] == "input" for msg in phase_messages):
            phase_messages.append({
                "role": "input",
                "content": topic
            })
        
        # Add phase indicator message
        phase_messages.append({
            "role": "system",
            "content": f"Current phase: {phase.upper()}. Follow the guidelines for this phase only."
        })
        
        # Randomly determine the order of AI models for this phase
        model_order = list(range(len(self.models)))
        random.shuffle(model_order)
        
        responses = []
        
        # Each AI takes a turn in this phase
        for i, idx in enumerate(model_order):
            model = self.models[idx]
            print(f"\nGenerating {phase.upper()} response from {model.name}...")
            
            # Generate response
            response = model.generate_response(phase_messages)
            
            # Format response with phase label if not already included
            if phase == "propose" and "[제안]" not in response:
                response = f"[제안]\n{response}"
            elif phase == "critique" and "[피드백]" not in response:
                response = f"[피드백]\n{response}"
            elif phase == "synthesize" and "[최종안]" not in response:
                response = f"[최종안]\n{response}"
            
            # Add model's response to messages
            model_response = {
                "role": model.name,
                "content": response,
                "phase": phase
            }
            
            phase_messages.append(model_response)
            self.messages.append(model_response)
            
            responses.append((model.name, response))
            
            # Print a preview of the response
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"{phase.upper()} response preview: {preview}")
        
        return responses, phase_messages
    
    def run_debate_cycle(self, topic):
        """
        Run a complete debate cycle with all three phases.
        
        Args:
            topic (str): The debate topic or question
            
        Returns:
            dict: Responses from each phase of the debate
        """
        print(f"\n=== Starting New Debate Cycle on: {topic} ===\n")
        
        # Initialize cycle results
        cycle_results = {
            "propose": [],
            "critique": [],
            "synthesize": []
        }
        
        # Reset messages for new cycle
        self.messages = []
        
        # Store cumulative messages from all phases
        cumulative_messages = []
        
        # Add user input to messages
        self.messages.append({
            "role": "input",
            "content": topic
        })
        
        # Phase 1: Propose
        print("\n=== PHASE 1: PROPOSE (제안) ===")
        propose_results, propose_messages = self.run_phase("propose", topic)
        cycle_results["propose"] = propose_results
        cumulative_messages = propose_messages
        
        # Phase 2: Critique & Refine
        print("\n=== PHASE 2: CRITIQUE & REFINE (비판 및 개선) ===")
        critique_results, critique_messages = self.run_phase("critique", previous_messages=cumulative_messages)
        cycle_results["critique"] = critique_results
        cumulative_messages = critique_messages
        
        # Phase 3: Synthesize
        print("\n=== PHASE 3: SYNTHESIZE (종합) ===")
        synthesize_results, synthesize_messages = self.run_phase("synthesize", previous_messages=cumulative_messages)
        cycle_results["synthesize"] = synthesize_results
        
        # Save the complete debate cycle to history
        self.history_manager.save_debate(self.session_id, self.messages)
        
        return cycle_results
    
    def run_interactive(self):
        """
        Run an interactive debate session with complete cycles based on user input.
        """
        print(f"AI Debate System (Session ID: {self.session_id})\n")
        print(f"Models loaded: {', '.join(model.name for model in self.models)}")
        print("The debate will follow three phases: Propose → Critique & Refine → Synthesize")
        print("Enter your question/topic or 'quit' to exit")
        
        while True:
            # Get user input
            import sys
            print("\nYour debate topic (press Ctrl+D to finish):\n")

            user_input = sys.stdin.read().strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Exiting debate system.")
                break
            
            # Run a complete debate cycle
            cycle_results = self.run_debate_cycle(user_input)
            
            # Print summary of cycle results
            print("\n=== DEBATE CYCLE SUMMARY ===")
            
            for phase in ["propose", "critique", "synthesize"]:
                print(f"\n--- {phase.upper()} PHASE RESPONSES ---")
                for model_name, response in cycle_results[phase]:
                    print(f"\n{model_name}'s response:")
                    print(response)
                    print("-" * 40)
            
            print("\nDebate cycle complete. Enter a new topic or 'quit' to exit.")

def main():
    parser = argparse.ArgumentParser(description='AI Debate System')
    parser.add_argument('--config', type=str, default='config.json', help='Path to configuration file')
    parser.add_argument('--search', action='store_true', help='Search debate history')
    parser.add_argument('--keyword', type=str, help='Keyword to search for')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    if args.search:
        history_manager = HistoryManager()
        results = history_manager.search_debates(
            keyword=args.keyword,
            start_date=args.start_date,
            end_date=args.end_date
        )
        print(f"Found {len(results)} debate(s):")
        for i, filepath in enumerate(results, 1):
            debate = history_manager.load_debate(filepath)
            # Find first user input
            user_input = "N/A"
            for msg in debate.get("messages", []):
                if msg.get("role") == "input":
                    user_input = msg.get("content", "N/A")
                    break
            print(f"{i}. {debate['timestamp']} - {user_input[:50]}...")
        
        if results:
            while True:
                choice = input("\nEnter number to view debate (or 'q' to quit): ")
                if choice.lower() == 'q':
                    break
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        debate = history_manager.load_debate(results[idx])
                        for msg in debate.get("messages", []):
                            role = msg.get("role")
                            content = msg.get("content", "")
                            
                            if role == "system":
                                continue  # Skip system messages
                            elif role == "input":
                                print(f"\nUser: {content}\n")
                            else:
                                print(f"{role}:\n{content}\n")
                    else:
                        print("Invalid number.")
                except ValueError:
                    print("Please enter a valid number.")
    else:
        # Run the debate system
        debate = AIDebate(config_path=args.config)
        debate.run_interactive()


if __name__ == "__main__":
    main()