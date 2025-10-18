from langgraph.graph import StateGraph, END
from .state import WorkflowState
from .nodes import (
    start_review_process,
    decide_next_step,
    escalate_to_senior,
    close_case_no_stenosis,
    send_satisfactory_email, # <-- Import the new node
    notify_and_schedule
)

# Create a new graph
workflow = StateGraph(WorkflowState)

# Define the nodes
workflow.add_node("start_review", start_review_process)
workflow.add_node("decide_next_step", decide_next_step)
workflow.add_node("escalate_to_senior", escalate_to_senior)
workflow.add_node("close_case_no_stenosis", close_case_no_stenosis)
workflow.add_node("send_satisfactory_email", send_satisfactory_email) # <-- Add the new node
workflow.add_node("notify_and_schedule", notify_and_schedule)

# Define the connections (edges) between nodes
workflow.set_entry_point("start_review")
workflow.add_edge("start_review", "decide_next_step")

# This edge handles the path for rejected cases
workflow.add_edge("close_case_no_stenosis", "send_satisfactory_email")

# Define the conditional logic for routing from the decision node
workflow.add_conditional_edges(
    "decide_next_step",
    lambda x: x["next_step"],
    {
        "escalate_to_senior": "escalate_to_senior",
        # Any rejection now goes to the 'close_case' node first
        "close_case_no_stenosis": "close_case_no_stenosis",
        "notify_and_schedule": "notify_and_schedule",
        "end": END
    }
)

# Add edges from the terminal nodes to the end
workflow.add_edge("escalate_to_senior", END)
workflow.add_edge("notify_and_schedule", END)
workflow.add_edge("send_satisfactory_email", END) # The new terminal node for satisfactory results


# Compile the graph into a runnable application
app = workflow.compile()

