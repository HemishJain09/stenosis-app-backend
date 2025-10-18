# backend/visualize_graph.py

# This script imports your compiled graph and saves a visualization to a file.
from graph.workflow import app

# This will generate a PNG image file in your backend directory
app.get_graph().draw_png("workflow_graph.png")

print("✅ Successfully generated workflow_graph.png")