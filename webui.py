import gradio as gr
from backend_manager import load_model, get_predictions
import sys

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        
    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def isatty(self):
        return False    

sys.stdout = Logger("output.log")

# Create a Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Audio Spectrogram Transformer")

    with gr.Row():
        label_csv = gr.Textbox(label="Label CSV Path", placeholder="Path to the label CSV file")
        checkpoint_path = gr.Textbox(label="Checkpoint Path", placeholder="Path to the checkpoint file")
        audio_sample = gr.Textbox(label="Audio Sample Path", placeholder="Path to the audio sample file")

    with gr.Row():
        load_model_button = gr.Button("Load Model")
        predict_button = gr.Button("Get Predictions")

    model_state = gr.State()
    prediction_output = gr.Textbox(label="Prediction Output", placeholder="Prediction output will appear here")

    def model_loader(checkpoint_path):
        model = load_model(checkpoint_path)
        
    # Load the model when the "Load Model" button is clicked
    load_model_button.click(
        fn=load_model,
        inputs=[checkpoint_path],
        outputs=[model_state],
        show_progress=True,
    )

    # Get predictions when the "Get Predictions" button is clicked
    predict_button.click(
        fn=get_predictions,
        inputs=[model_state, label_csv, audio_sample],
        outputs=[prediction_output],
        show_progress=True,
    )
    def read_logs():
        sys.stdout.flush()
        with open("output.log", "r") as f:
            return f.read()
    
    logs = gr.Textbox(label="Python Logs")
    demo.load(read_logs, None, logs, every=5)
# Launch the Gradio interface
demo.launch(server_name="0.0.0.0", server_port=7860, share=False)