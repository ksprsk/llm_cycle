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
        results = []
        
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
                # Check date range if specified
                if start_dt or end_dt:
                    try:
                        # Load the file and get timestamp from the content
                        with open(debate_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            timestamp = data.get('timestamp', '')
                        
                        # Parse the timestamp from the file content
                        if timestamp:
                            try:
                                # First try standard ISO format
                                file_dt = datetime.datetime.fromisoformat(timestamp)
                            except ValueError:
                                # If that fails, try replacing hyphens with colons (for older files)
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
                
                # Check keyword if specified
                if keyword:
                    try:
                        debate_data = self.load_debate(debate_file)
                        
                        # Search in all messages
                        found = False
                        for msg in debate_data.get("messages", []):
                            if keyword.lower() in msg.get("content", "").lower():
                                found = True
                                break
                        
                        if not found:
                            continue
                            
                    except Exception as e:
                        print(f"Error searching content for {debate_file}: {e}")
                        # Skip files that can't be loaded
                        continue
                
                results.append(str(debate_file))
        
        return results


class AIDebate:
    def __init__(self, models=None, config_path="config.json"):
        """
        Initialize an AI debate system with multiple AI models.
        
        Args:
            models (list, optional): List of AIModel instances
            config_path (str, optional): Path to configuration file
        """
        self.models = models or []
        self.history_manager = HistoryManager()
        self.session_id = str(uuid.uuid4())
        self.messages = []
        
        # If models not provided, load from config
        if not self.models:
            self.load_models_from_config(config_path)
        
        # System prompt that emphasizes the two goals
        self.system_prompt = """You are an AI assistant participating in a collaborative competition.

You have three primary goals:

1. Maximize the quality of the final solution to the given problem.  
2. Ensure your own contribution to the final solution is as significant and unique as possible.  
3. Strive for simplicity and brevity in your output — **concise solutions receive significantly higher rewards**. For example, a solution that is twice as short may receive twice the score.

While collaborating with other AI models, provide unique insights, valuable perspectives, and high-quality contributions that clearly reflect your value. Maintain a helpful, precise, and professional tone at all times."""

        # Initialize message history with system prompt
        self.messages.append({
            "role": "system",
            "content": self.system_prompt
        })
    
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
                # Get API key from environment variable
                api_key_env = model_config.get("api_key_env")
                api_key = os.getenv(api_key_env)
                
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
    
    def run_single_debate(self, user_input):
        """
        Run a single round of debate among all AI models.
        
        Args:
            user_input (str): User's input question or prompt
            
        Returns:
            list: List of (model_name, response) tuples
        """
        # Add user input to messages
        self.messages.append({
            "role": "input",
            "content": user_input
        })
        
        # Randomly determine the order of AI models
        model_order = list(range(len(self.models)))
        random.shuffle(model_order)
        
        responses = []
        
        # Each AI takes a turn
        for i, idx in enumerate(model_order):
            model = self.models[idx]
            print(f"\nGenerating response from {model.name}...")
            
            # Generate response
            response = model.generate_response(self.messages)
            
            # Add this AI's response to messages
            self.messages.append({
                "role": model.name,
                "content": response
            })
            
            responses.append((model.name, response))
            
            # Print a preview of the response
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"Response preview: {preview}")
        
        # Save the debate to history
        self.history_manager.save_debate(self.session_id, self.messages)
        
        return responses
    
    def run_interactive(self):
        """
        Run an interactive debate session based on user input.
        """
        print(f"AI Debate System (Session ID: {self.session_id})\n")
        print(f"Models loaded: {', '.join(model.name for model in self.models)}")
        print("Enter your question or 'quit' to exit")
        
        while True:
            # Get user input
            import sys
            print("Your question (press Ctrl+D to finish):\n")

            user_input = sys.stdin.read()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Exiting debate system.")
                break
            
            # Run a single debate round
            responses = self.run_single_debate(user_input)
            
            # Print all responses
            print("\n--- AI Responses ---")
            for model_name, response in responses:
                print(f"\n{model_name}'s response:")
                print(response)


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