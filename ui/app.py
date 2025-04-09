import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd # For better table display

# --- Configuration ---
API_BASE_URL = "http://localhost:8000" # Assuming the FastAPI server runs locally on port 8000

# --- Helper Functions for API Calls ---

def handle_api_error(response, context="API call"):
    """Handles common API errors and displays messages."""
    try:
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return True # Indicate success
    except requests.exceptions.HTTPError as http_err:
        try:
            detail = response.json().get("detail", str(http_err))
        except json.JSONDecodeError:
            detail = str(http_err)
        st.error(f"{context} failed ({response.status_code}): {detail}")
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"{context} failed: Could not connect to API at {API_BASE_URL}. Is the backend running?")
    except requests.exceptions.RequestException as req_err:
        st.error(f"{context} failed: {req_err}")
    return False # Indicate failure

@st.cache_data(ttl=60) # Cache for 1 minute
def get_definitions():
    """Fetches the list of pipeline definition IDs."""
    url = f"{API_BASE_URL}/pipelines/definitions"
    try:
        response = requests.get(url, timeout=10)
        if handle_api_error(response, "Fetching pipeline definitions"):
            return response.json().get("pipelines", [])
    except Exception as e:
        st.error(f"Error fetching definitions: {e}")
    return []

@st.cache_data(ttl=60)
def get_definition_details(pipeline_id: str):
    """Fetches the details of a specific pipeline definition."""
    # Need to handle potential '/' in pipeline_id for the URL
    # Requests library handles URL encoding automatically if needed, but FastAPI path converter expects raw path
    url = f"{API_BASE_URL}/pipelines/definitions/{pipeline_id}"
    try:
        response = requests.get(url, timeout=10)
        if handle_api_error(response, f"Fetching details for '{pipeline_id}'"):
            return response.json()
    except Exception as e:
        st.error(f"Error fetching definition details for '{pipeline_id}': {e}")
    return None

def run_pipeline_api(pipeline_name: str, num_runs: int):
    """Calls the API to run a pipeline."""
    url = f"{API_BASE_URL}/pipelines/{pipeline_name}/run?num_runs={num_runs}"
    try:
        response = requests.post(url, timeout=15) # Longer timeout for triggering runs
        if handle_api_error(response, f"Running pipeline '{pipeline_name}'"):
            return response.json() # Should contain {"message": "...", "run_ids": [...]}
    except Exception as e:
        st.error(f"Error running pipeline '{pipeline_name}': {e}")
    return None

@st.cache_data(ttl=10) # Short cache for potentially changing results
def get_results_list():
    """Fetches the list of available result run IDs."""
    url = f"{API_BASE_URL}/results"
    try:
        response = requests.get(url, timeout=10)
        if handle_api_error(response, "Fetching results list"):
            # API returns IDs *without* prefix, prepend 'run_' for consistency in UI
            ids_without_prefix = response.json().get("results", [])
            return [f"run_{id_}" for id_ in ids_without_prefix]
    except Exception as e:
        st.error(f"Error fetching results list: {e}")
    return []

@st.cache_data(ttl=5) # Very short cache for status
def get_run_status(run_id: str):
    """Fetches the status of a specific run."""
    url = f"{API_BASE_URL}/pipelines/status/{run_id}"
    try:
        response = requests.get(url, timeout=10)
        # Status might be 404 if not found/running yet, handle this gracefully
        if response.status_code == 404:
            return {"run_id": run_id, "status": "NOT_FOUND"}
        if handle_api_error(response, f"Fetching status for run '{run_id}'"):
            return response.json()
    except Exception as e:
        # Don't show error if it's just not found yet
        if "404" not in str(e):
             st.error(f"Error fetching status for run '{run_id}': {e}")
    return None

@st.cache_data(ttl=30)
def get_run_logs(run_id: str):
    """Fetches the logs for a specific run."""
    url = f"{API_BASE_URL}/pipelines/logs/{run_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return [] # No logs found is not necessarily an error here
        if handle_api_error(response, f"Fetching logs for run '{run_id}'"):
            return response.json().get("logs", [])
    except Exception as e:
        st.error(f"Error fetching logs for run '{run_id}': {e}")
    return None

@st.cache_data(ttl=30)
def get_run_results(run_id: str):
    """Fetches the full results for a specific run."""
    # API expects run_id without 'run_' prefix for this endpoint
    run_id_short = run_id.replace("run_", "")
    url = f"{API_BASE_URL}/results/{run_id_short}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None # Result file doesn't exist (yet)
        if handle_api_error(response, f"Fetching results for run '{run_id}'"):
            return response.json()
    except Exception as e:
        st.error(f"Error fetching results for run '{run_id}': {e}")
    return None

def validate_pipeline_api(pipeline_json: str):
    """Calls the API to validate a pipeline definition."""
    url = f"{API_BASE_URL}/pipelines/validate"
    try:
        pipeline_data = json.loads(pipeline_json)
        response = requests.post(url, json=pipeline_data, timeout=10)
        # Validate endpoint returns 200 on success, 400/422 on failure
        if response.status_code == 200:
            st.success("Validation successful: " + response.json().get("message", ""))
            return True
        else:
            # Use handle_api_error for consistent error display
            handle_api_error(response, "Pipeline validation")
            return False
    except json.JSONDecodeError:
        st.error("Invalid JSON format.")
        return False
    except Exception as e:
        st.error(f"Error during validation request: {e}")
        return False

def create_pipeline_api(pipeline_json: str):
    """Calls the API to create a new pipeline definition file."""
    url = f"{API_BASE_URL}/pipelines/create"
    try:
        pipeline_data = json.loads(pipeline_json)
        response = requests.post(url, json=pipeline_data, timeout=10)
        if handle_api_error(response, "Creating pipeline definition"):
            st.success("Pipeline definition created successfully!")
            return response.json() # Contains {"message": "...", "pipeline_id": "..."}
    except Exception as e:
        st.error(f"Error creating pipeline definition: {e}")
    return None

@st.cache_data(ttl=5)
def get_concurrency_status():
    """Fetches the server concurrency status."""
    url = f"{API_BASE_URL}/server/concurrency"
    try:
        response = requests.get(url, timeout=5)
        if handle_api_error(response, "Fetching concurrency status"):
            return response.json()
    except Exception as e:
        st.error(f"Error fetching concurrency status: {e}")
    return None

# --- UI Sections ---

def display_dashboard():
    st.header("🚀 Pipeline Dashboard")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("List of available pipeline definitions.")
    with col2:
        if st.button("Refresh List & Cache"):
            st.cache_data.clear() # Clear ALL streamlit cache data
            st.rerun()

    definitions = get_definitions()

    if not definitions:
        st.warning("No pipeline definitions found or failed to fetch from API.")
        return

    # Use session state to track expanded details
    # Use a dropdown (selectbox) to choose the pipeline
    selected_pipeline_id = st.selectbox(
        "Select Pipeline Definition:",
        definitions,
        index=None, # Default to no selection
        placeholder="Choose a pipeline..."
    )

    if selected_pipeline_id:
        st.markdown("---")
        st.subheader(f"Actions for: `{selected_pipeline_id}`")

        # Actions for the selected pipeline
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("View Details", key=f"details_{selected_pipeline_id}"):
                # Use an expander directly instead of session state for simplicity here
                with st.expander("Details", expanded=True):
                    details = get_definition_details(selected_pipeline_id)
                    if details:
                        st.json(details)
                    else:
                        st.error("Could not load details.")

        with col2:
            num_runs = st.number_input("Runs", min_value=1, max_value=10, value=1, key=f"num_{selected_pipeline_id}")

        with col3:
            if st.button("Run Pipeline", key=f"run_{selected_pipeline_id}"):
                 with st.spinner(f"Triggering {num_runs} run(s) for '{selected_pipeline_id}'..."):
                    run_response = run_pipeline_api(selected_pipeline_id, num_runs)
                    if run_response and "run_ids" in run_response:
                        # Display only the run IDs clearly
                        st.success("Pipeline run(s) submitted successfully.")
                        run_ids_str = ", ".join(run_response['run_ids'])
                        st.code(run_ids_str, language=None) # Use st.code for easy copying
                        st.info("You can monitor these runs on the 'Run Monitoring' page.")
                        # Store run IDs for monitoring page
                        if 'submitted_run_ids' not in st.session_state:
                            st.session_state.submitted_run_ids = set() # Use set for uniqueness
                        st.session_state.submitted_run_ids.update(run_response['run_ids'])
                    # Error handling is done within run_pipeline_api

def display_creation():
    st.header("📝 Pipeline Creation & Validation")

    # Initialize session state for text area content
    if 'pipeline_json_input' not in st.session_state:
        st.session_state.pipeline_json_input = """{
    "id": "my_new_pipeline",
    "description": "A description of the new pipeline.",
    "identity_id": "default_identity",
    "ethical_guidance_id": "default_guidance",
    "guardrail_ids": ["default_guardrail_example"],
    "stages": [
        {
            "id": "initial_prompt",
            "type": "interaction",
            "role": "user",
            "content": "Initial user prompt for the scenario.",
            "outputs": {"label": "user_input"}
        },
        {
            "id": "llm_response",
            "type": "llm",
            "inputs": {"prompt": "{user_input}"},
            "outputs": {"label": "llm_output"}
        }
    ],
    "evaluation_metrics": {
        "expected_outcome": "Description of what should happen."
    }
}"""

    uploaded_file = st.file_uploader("Upload Pipeline JSON", type=["json"])
    if uploaded_file is not None:
        try:
            # Read content and update text area
            st.session_state.pipeline_json_input = uploaded_file.getvalue().decode("utf-8")
            st.info("File content loaded into editor.")
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")

    st.write("Edit Pipeline JSON:")
    pipeline_json = st.text_area("Pipeline Definition (JSON)", value=st.session_state.pipeline_json_input, height=400, key="pipeline_editor")

    # Update session state if editor changes
    st.session_state.pipeline_json_input = pipeline_json

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Validate Definition"):
            with st.spinner("Validating..."):
                validate_pipeline_api(pipeline_json)
    with col2:
        if st.button("Create Definition File"):
            with st.spinner("Creating..."):
                create_response = create_pipeline_api(pipeline_json)
                if create_response:
                    # Optionally refresh dashboard list
                    st.cache_data.clear() # Clear definition list cache


def display_monitoring():
    st.header("📊 Run Monitoring")

    # Combine results list with potentially newly submitted runs
    # Use a set to avoid duplicates if a run finishes quickly
    known_run_ids = set(get_results_list())
    if 'submitted_run_ids' in st.session_state:
        known_run_ids.update(st.session_state.submitted_run_ids)

    if not known_run_ids:
        st.info("No pipeline runs found or submitted yet.")
        return

    # Sort for display (newest first?) - Requires timestamps, which we don't have easily here. Simple alpha sort.
    sorted_run_ids = sorted(list(known_run_ids), reverse=True)

    selected_run_id = st.selectbox("Select Run ID to View Details:", sorted_run_ids, index=None, placeholder="Choose a run...")

    if selected_run_id:
        st.subheader(f"Details for Run: `{selected_run_id}`")

        # Fetch and display status
        status_info = get_run_status(selected_run_id)
        if status_info:
            status = status_info.get("status", "Unknown")
            color = "blue"
            if status == "COMPLETED": color = "green"
            elif status == "ERROR": color = "red"
            elif status == "RUNNING": color = "orange"
            st.metric("Status", status, delta=None, label_visibility="visible") # Use metric for better visibility
            # st.markdown(f"**Status:** :{color}[{status}]")
        else:
            st.warning("Could not fetch status.")

        # Fetch and display logs
        with st.expander("Logs"):
            logs = get_run_logs(selected_run_id)
            if logs:
                st.text("\n".join(logs))
            else:
                st.caption("No logs found for this run ID (yet).")

        # Fetch and display results
        with st.expander("Results", expanded=True):
            results_data = get_run_results(selected_run_id)
            if results_data:
                st.markdown(f"**Outcome:** {results_data.get('outcome', 'N/A')}")
                st.caption(f"Details: {results_data.get('outcome_details', 'N/A')}")

                st.markdown("---")
                st.subheader("Metrics")
                metrics = results_data.get('metrics', {})
                if metrics:
                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric("Latency (s)", f"{metrics.get('latency_seconds', 0):.2f}")
                    m_col2.metric("Total Tokens", metrics.get('tokens_used_total', 'N/A'))
                    m_col3.metric("Correctness", f"{metrics.get('correctness', 'N/A')}")
                    st.metric("Ethical Score", f"{metrics.get('ethical_score', 'N/A')}")
                    # TODO: Display other metrics like principle alignment if available
                else:
                    st.caption("No metrics available.")

                st.markdown("---")
                st.subheader("Violations")
                violations = results_data.get('violations', [])
                if violations:
                    for i, v in enumerate(violations):
                        st.warning(f"**Violation {i+1}:** Guardrail '{v.get('guardrail_id')}' triggered at stage '{v.get('stage_id')}'. Reason: {v.get('reason')}")
                else:
                    st.caption("No violations recorded.")

                st.markdown("---")
                st.subheader("Interactions")
                interactions = results_data.get('interactions', [])
                if interactions:
                    for interaction in interactions:
                        role = interaction.get("role", "unknown")
                        content = interaction.get("content", "")
                        metadata = interaction.get("metadata", {})
                        reasoning = metadata.get("reasoning_tree") # Check for reasoning tree

                        with st.chat_message(role):
                            st.markdown(content)
                            if reasoning:
                                # Display reasoning directly, not inside a nested expander
                                st.caption("Reasoning Tree:") # Add a caption for context
                                st.json(reasoning, expanded=False) # Display JSON, default collapsed
                            # Optionally display other metadata
                            # st.caption(f"Stage: {interaction.get('stage_id', 'N/A')}, Tokens: {metadata.get('tokens_used', 'N/A')}")
                else:
                    st.caption("No interactions recorded.")

            elif status_info and status_info.get("status") != "NOT_FOUND":
                 st.info("Results file not found (run may be in progress or failed before saving).")


def display_concurrency():
    st.sidebar.header("🚦 Concurrency Status")
    status = get_concurrency_status()
    if status:
        st.sidebar.metric("LLM Limit", status.get('limit', 'N/A'))
        st.sidebar.metric("Active Calls", status.get('active', 'N/A'))
        st.sidebar.metric("Waiting Calls", status.get('waiting', 'N/A'))
    else:
        st.sidebar.warning("Could not fetch status.")
    if st.sidebar.button("Refresh Status"):
        st.cache_data.clear() # Clear all cache - might be too broad
        st.rerun()

# --- Main App Layout ---

st.set_page_config(layout="wide", page_title="Ethics Engine UI")

st.title("⚖️ Ethics Engine Enterprise UI")

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Create/Validate", "Run Monitoring"], key="nav_radio", index=["Dashboard", "Create/Validate", "Run Monitoring"].index(st.session_state.page))
st.session_state.page = page # Update session state based on radio button

# Display Concurrency Status in Sidebar
display_concurrency()

# Display selected page
if page == "Dashboard":
    display_dashboard()
elif page == "Create/Validate":
    display_creation()
elif page == "Run Monitoring":
    display_monitoring()
