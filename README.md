# AI Debate System

This project implements a collaborative competition system between multiple AI models. Each AI model has dual goals:
1. Maximizing the quality of the final solution
2. Ensuring their own contribution is as significant as possible

## Features

- **Extensible Model Support**: Configure any number of AI models through config.json
- **History Management**: Save, load, and search debate sessions
- **Interactive Mode**: Engage in continuous conversations with multiple AI models
- **Command-line Interface**: Search past debates by keyword and date range

## Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/ai-debate-system.git
cd ai-debate-system
```

2. Install dependencies
```bash
pip install openai python-dotenv
```

3. Set up your API keys
   - Copy `.env.example` to `.env`
   - Add your API keys for each model used in config.json

4. Configure models in config.json
   - The default configuration includes OpenAI, Claude, and Gemini models
   - You can add or remove models as needed

## Usage

### Interactive Mode

Run the main script to start an interactive session:
```bash
python main.py
```

### Search Debate History

Search for past debates by keyword and/or date range:
```bash
python main.py --search --keyword "climate" --start-date "2025-04-01" --end-date "2025-04-21"
```

## Configuration

The `config.json` file defines the AI models to use:

```json
{
  "models": [
    {
      "name": "OpenAI",
      "model_name": "o4-mini",
      "api_key_env": "OPENAI_API_KEY",
      "base_url": null,
      "max_completion_tokens": 1000,
      "extra_body": {}
    },
    ...
  ]
}
```

Each model configuration includes:
- `name`: Display name for the model
- `model_name`: Technical model name used in API calls
- `api_key_env`: Environment variable name containing the API key
- `base_url`: API endpoint URL (null for default)
- `max_completion_tokens`: Maximum tokens in responses
- `extra_body`: Additional API parameters

## Project Structure

- `main.py` - Main script for the AI debate system
- `config.json` - Configuration file for AI models
- `.env` - Environment file for API keys (not included in repo)
- `debate_history/` - Directory storing past debate sessions