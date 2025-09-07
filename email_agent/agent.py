from .system_prompt import SystemPrompts
from .util import refine_input_prompt
import ollama

class Agent:
    def __init__(self, model:str = "llama3.2:1b"):
        # Start a chat session with system prompt
        self.__model = model
        self.__history = [{"role": "system", "content": SystemPrompts.EMAIL_AGENT.value}]

    def generate_label(self, email_data, existing_labels):
        user_prompt = refine_input_prompt(email_data, existing_labels)
        self.__history.append({'role': 'user', 'content': user_prompt})

        response = ollama.chat(
            model=self.__model,
            messages=self.__history,
            options={
                "temperature": 0.3,
                "top_p": 0.95,
                "repeat_penalty": 1.1
            }
        )

        label = response['message']['content'].strip()
        # Add assistant reply to history (for continuity)
        self.__history.append({"role": "assistant", "content": label})
        return label