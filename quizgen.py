import gradio as gr
import webbrowser
import os
import json
import shutil
from mistralai import Mistral

# Set up constants with relative paths for easier portability
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the script
SAVED_DIR = os.path.join(BASE_DIR, "Saved_Quizzes")  # Directory to save quizzes
QUIZ_FILE = os.path.join(BASE_DIR, "quiz.html")  # Temporary quiz file
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.text")  # Quiz prompt template file
TEMPLATE_FILE = os.path.join(BASE_DIR, "template.html")  # HTML template file
MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]  # Mistral API Key from environment
MODEL_NAME = "open-mistral-nemo"  # Mistral model name

# Global variables
difficulty = 0.1
title = ""

def transform_string(input_string):
    """
    Transforms the input string by removing "quiz" and replacing spaces with underscores.
    """
    transformed = input_string.replace("quiz", "").replace("Quiz", "").strip()
    return transformed.replace(" ", "_")

def generate_quiz_html(json_data):
    """
    Generates an HTML quiz file from a JSON object.

    Args:
        json_data (dict): The quiz data in JSON format.
    
    Returns:
        tuple: HTML content as a string and the quiz title.
    """
    quiz_title = json_data["quiz"].get("title", "NoName")
    questions_html = ""

    # Generate questions and answers dynamically
    for question in json_data["quiz"]["questions"]:
        question_block = f"""
        <div class="question" id="question-{question['id']}">
            <h2>{question['question']}</h2>
            <div class="answers">
"""
        for answer in question["answers"]:
            question_block += f"""
                <button 
                    data-question-id="{question['id']}" 
                    data-correct="{str(answer['isCorrect']).lower()}" 
                    onclick="checkAnswer(this, {str(answer['isCorrect']).lower()}, {question['id']})">
                    {answer['text']}
                </button>
"""
        question_block += """
            </div>
        </div>
"""
        questions_html += question_block

    # Load the template
    if not os.path.exists(TEMPLATE_FILE):
        raise FileNotFoundError(f"Template file '{TEMPLATE_FILE}' not found!")

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template = file.read()

    # Replace placeholders
    html_code = template.replace("{{title}}", quiz_title).replace("{{questions}}", questions_html)

    return html_code, quiz_title

def generate_quiz_prompt(input_content: str, difficulty: float) -> str:
    """
    Generates a quiz prompt by embedding input content into a template.

    Args:
        input_content (str): Content to base the quiz on.
        difficulty (float): Difficulty level for the quiz.

    Returns:
        str: The formatted quiz prompt.
    """
    try:
        with open(PROMPT_FILE, "r") as file:
            template = file.read()

        return template.replace("[Content]", input_content).replace("[difficulty]", str(difficulty))
    except Exception as e:
        raise ValueError(f"Error generating quiz prompt: {e}")

def get_json_data(input_text, difficulty):
    """
    Sends a prompt to the Mistral API and receives quiz JSON data.

    Args:
        input_text (str): The content for the quiz.
        difficulty (float): The difficulty level.

    Returns:
        dict: The quiz JSON data.
    """
    prompt = generate_quiz_prompt(input_text, difficulty)
    client = Mistral(api_key=MISTRAL_API_KEY)
    messages = [{"role": "user", "content": prompt}]

    chat_response = client.chat.complete(
        model=MODEL_NAME,
        messages=messages,
        response_format={"type": "json_object"}
    )

    return json.loads(chat_response.choices[0].message.content)

def get_html_response(input_text, difficulty_level):
    """
    Generates an HTML file for a quiz, opens it in the default browser, and prepares it for download.

    Args:
        input_text (str): The text to generate the quiz from.
        difficulty_level (float): The difficulty level for the quiz.

    Returns:
        str: A confirmation message about the quiz generation.
    """
    global title, difficulty
    difficulty = difficulty_level

    json_data = get_json_data(input_text, difficulty)
    html_content, quiz_title = generate_quiz_html(json_data)
    title = transform_string(quiz_title)

    # Write the HTML content to a temporary file
    with open(QUIZ_FILE, "w", encoding="utf-8") as file:
        file.write(html_content)

    # Open the quiz in the default browser
    webbrowser.open(f"file://{os.path.abspath(QUIZ_FILE)}")

    return f"A new quiz titled '{quiz_title}' with difficulty {difficulty} has been created."

def download_file():
    """
    Saves the generated quiz with a unique name based on title and difficulty.
    """
    global title
    new_name = f"{SAVED_DIR}/{title}_diff:{difficulty:.3f}.html"
    new_path = os.path.join(BASE_DIR, new_name)

    shutil.copy2(QUIZ_FILE, new_path)

def open_file(files):
    """
    Opens selected files in the default web browser.

    Args:
        files (list): List of file paths to open.
    """
    for file in files:
        webbrowser.open(f"file://{os.path.abspath(file)}")

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Quiz Generator")
    gr.Markdown("Insert your content, select a difficulty, and generate interactive quizzes!")

    with gr.Row():
        with gr.Column(scale=1):
            input_box = gr.Textbox(
                label="Enter Your Content",
                placeholder="Paste your content here...",
                lines=6
            )
            slider = gr.Slider(minimum=0.1, maximum=1, label="Difficulty")

        with gr.Column(scale=1):
            gen_button = gr.Button("Generate Quiz", variant="primary")
            chatbot_response = gr.Textbox(label="")
            save_button = gr.Button("Save Quiz")
            output_box = gr.FileExplorer(label="My Quizzes", root_dir=SAVED_DIR, ignore_glob=".DS_Store")
            open_button = gr.Button("Open Selected Quiz", variant="primary")

    # Action bindings
    gen_button.click(get_html_response, inputs=[input_box, slider], outputs=chatbot_response)
    save_button.click(fn=download_file).then(None, js="window.location.reload()")
    open_button.click(fn=open_file, inputs=output_box)

demo.launch()
