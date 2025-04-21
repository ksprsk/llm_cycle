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
        # Create the session directory
        session_dir = self.base_dir / session_id
        session_dir.mkdir(exist_ok=True, parents=True)
        
        # Create standard filename for the session
        filename = f"session_{session_id}.json"
        filepath = session_dir / filename
        
        # Get current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # If file exists, read it to preserve creation timestamp
        created_timestamp = timestamp
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    created_timestamp = existing_data.get("created_timestamp", timestamp)
            except:
                pass  # If reading fails, use current timestamp
        
        # Store data with timestamps
        data = {
            "session_id": session_id,
            "created_timestamp": created_timestamp,
            "last_updated": timestamp,
            "messages": messages
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def create_snapshot(self, session_id):
        """
        Create a timestamped snapshot of the current session.
        
        Args:
            session_id (str): Session ID to snapshot
            
        Returns:
            str or None: Path to snapshot file or None if session not found
        """
        session_dir = self.base_dir / session_id
        session_file = session_dir / f"session_{session_id}.json"
        
        if not session_file.exists():
            return None
            
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create timestamp filename for snapshot
            timestamp = datetime.datetime.now().isoformat().replace(':', '-')
            snapshot_file = session_dir / f"snapshot_{timestamp}.json"
            
            # Write the snapshot
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return str(snapshot_file)
        except Exception as e:
            print(f"Error creating snapshot: {e}")
            return None

    def load_debate(self, filepath):
        """
        Load a debate from a file.

        Args:
            filepath (str or Path): Path to the debate file

        Returns:
            dict: Debate data
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

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
        results = set()  # Use set to prevent duplicates

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

            # For each session, prioritize the main session file
            main_file = session_dir / f"session_{session_dir.name}.json"
            files_to_check = []
            
            if main_file.exists():
                files_to_check.append(main_file)
            else:
                # If no main file exists, check all JSON files
                files_to_check.extend(session_dir.glob("*.json"))
            
            for debate_file in files_to_check:
                str_path = str(debate_file)
                if str_path in results:
                    continue

                try:
                    with open(debate_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Check date range using last_updated field
                    timestamp = data.get('last_updated', data.get('timestamp', ''))
                    
                    if timestamp:
                        try:
                            file_dt = datetime.datetime.fromisoformat(timestamp)
                        except ValueError:
                            # Handle old format if needed
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
                        
                    # Keyword check
                    if keyword:
                        found = False
                        for msg in data.get("messages", []):
                            if keyword.lower() in msg.get("content", "").lower():
                                found = True
                                break
                        
                        if not found:
                            continue
                            
                    results.add(str_path)
                except Exception as e:
                    print(f"Error checking file {debate_file}: {e}")
                    
        return list(results)
    
    def list_all_debates(self, limit=50):
        """
        List all debate sessions (one per session).

        Args:
            limit (int, optional): Maximum number of sessions to return

        Returns:
            list: (filepath, session_id, created, updated, preview) tuples
        """
        all_debates = []
        
        # Iterate through all session directories
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            session_id = session_dir.name
            
            # First try to find the main session file
            main_file = session_dir / f"session_{session_id}.json"
            
            if main_file.exists():
                debate_file = main_file
            else:
                # Find most recent file if no main file
                files = list(session_dir.glob("*.json"))
                if not files:
                    continue
                debate_file = max(files, key=lambda f: f.stat().st_mtime)
            
            try:
                with open(debate_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Get timestamps
                updated = data.get('last_updated', data.get('timestamp', ''))
                created = data.get('created_timestamp', updated)
                
                # Get first user input as preview
                preview = "N/A"
                for msg in data.get("messages", []):
                    if msg.get("role") == "input":
                        preview = msg.get("content", "")[:100]
                        break
                
                # Parse timestamp for sorting
                try:
                    dt = datetime.datetime.fromisoformat(updated)
                except ValueError:
                    # Handle old format if needed
                    parts = updated.split('T')
                    if len(parts) == 2:
                        date_part = parts[0]
                        time_part = parts[1].replace('-', ':')
                        dt = datetime.datetime.fromisoformat(f"{date_part}T{time_part}")
                    else:
                        dt = datetime.datetime.min
                
                all_debates.append((str(debate_file), session_id, created, updated, preview, dt))
            except Exception as e:
                print(f"Error loading debate file {debate_file}: {e}")
        
        # Sort by timestamp (newest first)
        all_debates.sort(key=lambda x: x[5], reverse=True)
        
        # Return without datetime object
        return [(path, sid, created, updated, prev) for path, sid, created, updated, prev, _ in all_debates[:limit]]


    def delete_message(self, session_id, message_index):
        """
        Delete a specific message from the session file.

        Args:
            session_id (str): Session ID
            message_index (int): Index of message to delete

        Returns:
            bool: Success or failure
        """
        session_dir = self.base_dir / session_id
        session_file = session_dir / f"session_{session_id}.json"
        
        if not session_file.exists():
            # Try to find most recent file
            files = list(session_dir.glob("*.json"))
            if not files:
                return False
            session_file = max(files, key=lambda f: f.stat().st_mtime)
        
        try:
            # Load debate data
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check message index
            if message_index < 0 or message_index >= len(data.get("messages", [])):
                return False
            
            # Remove message
            data["messages"].pop(message_index)
            data["last_updated"] = datetime.datetime.now().isoformat()
            
            # Save updated file
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False

    def delete_debate_file(self, filepath):
        """
        Delete a specific debate file.

        Args:
            filepath (str): Path to file to delete

        Returns:
            bool: Success or failure
        """
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                path.unlink()
                
                # Remove directory if empty
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
    
    def run_single_debate(self, topic):
        """
        Run a single debate cycle with the given topic.
        This is a wrapper around run_debate_cycle for Streamlit app compatibility.
        
        Args:
            topic (str): The debate topic or question
            
        Returns:
            dict: Responses from each phase of the debate
        """
        return self.run_debate_cycle(topic)

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