import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
import os



# Load environment variables from .env file
load_dotenv(find_dotenv())
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


# File path to store assistant and vector store IDs
ids_file_path = 'backend/ids.json'

def load_ids():
    """Load assistant and vector store IDs from a file."""
    try:
        with open(ids_file_path, 'r') as f:
            data = f.read()
            if data:
                return json.loads(data)
            else:
                return {"assistant_id": None, "vector_store_id": None}
    except FileNotFoundError:
        return {"assistant_id": None, "vector_store_id": None}
    except json.JSONDecodeError as e:
        
        return {"assistant_id": None, "vector_store_id": None},(f"Error decoding JSON from ids file: {e}")

def save_ids(assistant_id, vector_store_id):
    """Save assistant and vector store IDs to a file."""
    with open(ids_file_path, 'w') as f:
        json.dump({"assistant_id": assistant_id, "vector_store_id": vector_store_id}, f)

def create_new_assistant_and_vector_store():
    """Create a new assistant and vector store, and save their IDs."""
    assistant = client.beta.assistants.create(
        name='Hospital Receptionist Assistant',
        instructions=(
            'You are a hospital chatbot named Hospital Bot. Introduce yourself to users politely in the first message. '
            'Your task is to assist users with basic health and hospital information. If the response is not in the document, respond from your knowledge.'
        ),
        model='gpt-3.5-turbo',
        tools=[{"type": 'file_search'}]
    )
    assistant_id = assistant.id
    
    vector_store = client.beta.vector_stores.create()
    vector_store_id = vector_store.id

    file_path = ['files/Answers.pdf']
    file_stream = [open(path, 'rb') for path in file_path]
    client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id, files=file_stream
    )

    client.beta.assistants.update(
        assistant_id=assistant_id, 
        tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}}
    )

    save_ids(assistant_id, vector_store_id)
    return assistant_id, vector_store_id

def get_response(user_input,thread_id):
    """Get response from the assistant based on user input."""
    try:
        
        ids = load_ids()
        assistant_id = ids.get("assistant_id")
        vector_store_id = ids.get("vector_store_id")

        if not assistant_id or not vector_store_id:
            assistant_id, vector_store_id = create_new_assistant_and_vector_store()
        
        if not thread_id:
            thread = client.beta.threads.create()
               
            thread_id = thread.id
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role='user',
            content=user_input
        )
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id, assistant_id=assistant_id
        )

        messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))
        message_content = messages[0].content[0].text
        response = message_content['value']
    except Exception as e :
        if messages:
            response = messages[0].content[0].text.value
        else:
            return f"Error {e}"
    return response,thread_id  
     


