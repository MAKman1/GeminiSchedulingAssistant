# AI Agent Onboarding Protocol: Gemini Scheduling Assistant

**Objective:** To provide a comprehensive, machine-readable guide for AI agents tasked with maintaining and extending this codebase.

**Core Principle:** The reliability of this application is based on a structured, multi-step agentic workflow. Your primary directive is to understand and preserve this workflow. Deviations from this workflow are the most likely source of errors.

### **Core Application Context**

This application is a scheduling assistant that helps users find and book meeting times. It is designed to be used in a conversational manner, where the user interacts with the assistant through a chat interface. The assistant is powered by a Large Language Model (LLM) that is capable of understanding natural language and taking actions on behalf of the user.

The assistant is designed to be proactive and helpful. It should not simply respond to the user's requests, but should also anticipate their needs and provide them with relevant information. For example, if the user asks to find a meeting time, the assistant should not just provide a list of available slots, but should also consider the user's preferences and the availability of the other attendees.

### **Desired Workflow**

The following is a step-by-step description of the desired workflow for processing user requests:

1.  **Session Initiation & Main Agent Invocation**: A new input starts a session. The Flask backend invokes the Main Orchestrator Agent with the user's raw text.

2.  **Main Agent - Initial Analysis & Tool Selection**: The Main Agent analyzes the prompt. It understands the core intent (e.g., `find_availability`, `book_meeting`) and extracts initial entities (e.g., `duration`, `attendees`, `time_range`, `title`). It recognizes that it doesn't have the necessary calendar or preference data to find a slot, so it decides to use its specialized tool.

3.  **The "Data-Gatherer" Agent in Action (Tool Execution)**: The `get_comprehensive_attendee_data` function is triggered. This function contains the logic for the sub-agent.
    *   **Filter Internal Attendees**: It takes the list of attendees and filters it down to only include internal attendees.
    *   **Fetch NL Preferences**: It queries the database to get the `preference_text` for the internal attendees.
    *   **Fetch Calendar Data**: It makes the `freeBusy.query` call to the Google Calendar API for the internal attendees for the specified time range.
    *   **Consolidate into JSON**: It packages all the gathered information into a single, comprehensive JSON object and returns it to the Main Agent. This JSON is just raw data, not a solution.

4.  **Main Agent - The Synthesis & Reasoning Phase**: This is the most critical step. The Main Agent now has the original request and the detailed data dossier. It performs a "Chain of Thought" reasoning process by essentially creating a new, highly detailed prompt for itself.

5.  **Response Generation**: The LLM processes this complex prompt and concludes with a proposed meeting time. The Main Agent then uses this conclusion to generate a human-like response and proposes the time to the user.

6.  **User Confirmation & Booking**: The user can then confirm the proposed time. Once the user confirms, the Main Agent will call the `create_calendar_event` tool to book the meeting.

#### **1. System Architecture Overview**

*   **Primary Logic Hub:** `agents.py`. All reasoning, tool selection, and response generation originates here. You must always analyze this file first to understand the application's state.
*   **Tool Definitions:** `google_calendar.py` and `firestore_db.py`. These files contain the Python functions that are exposed to the LLM as tools.
*   **Web Interface:** The `templates` and `static` directories. You will modify these files to alter the user interface.
*   **API Endpoints:** `app.py`. This file contains the Flask routes that connect the frontend to the backend logic.

#### **2. The Multi-Step Agentic Workflow (Mandatory Knowledge)**

You must understand and adhere to this workflow. Do not attempt to simplify it into a single LLM call.

*   **Step 1: Intent Recognition (Initial Analysis)**
    *   **File:** `agents.py`
    *   **Function:** `run_orchestrator_agent`
    *   **Prompt:** `initial_analysis_prompt`
    *   **Process:** This is a classification task. The LLM is given the user's request and a list of attendees. It must classify the user's intent as either `find_availability` or `book_meeting`. The output is a JSON object that specifies the tool to be called.
    *   **Your Role:** If you need to modify the agent's ability to recognize new intents, you must update the `initial_analysis_prompt` to include the new intent and the corresponding tool.

*   **Step 2: Tool Execution**
    *   **File:** `agents.py`
    *   **Process:** The application logic parses the JSON from Step 1 and executes the specified tool.
    *   **Your Role:** If you add a new tool, you must add a new `elif` block to the `run_orchestrator_agent` function to handle the execution of that tool.

*   **Step 3: Synthesis & Reasoning**
    *   **File:** `agents.py`
    *   **Prompt:** `reasoning_prompt`
    *   **Process:** This step is only triggered after the `get_comprehensive_attendee_data` tool is called. The data from the tool is combined with the original request to form a new, detailed prompt. This prompt forces the LLM to reason through the data and generate a human-readable response.
    *   **Your Role:** If you need to change how the agent proposes times or handles conflicts, you must modify the `reasoning_prompt`.

#### **3. Common Errors and How to Avoid Them**

I have made several errors during the development of this application. You must learn from my mistakes to avoid repeating them.

*   **Error Type: `TypeError: ... got an unexpected keyword argument`**
    *   **Cause:** This error occurs when the arguments in the JSON object returned by the LLM do not match the arguments of the Python function being called.
    *   **Solution:** Ensure that the `args` in the JSON object are an exact match for the parameters of the tool function. For example, if the function is `def my_tool(arg1, arg2)`, the JSON must be `{"tool_name": "my_tool", "args": {"arg1": "value1", "arg2": "value2"}}`.

*   **Error Type: `400 INVALID_ARGUMENT: Regex parsing error`**
    *   **Cause:** This error is caused by a malformed prompt being sent to the LLM. It is almost always due to incorrectly embedding dynamic data into the prompt string.
    *   **Solution:** When embedding a Python object (like a list or dictionary) into a prompt, you **must** use `json.dumps()` to ensure it is correctly formatted as a string.

*   **Error Type: `AttributeError: 'NoneType' object has no attribute 'function_call'`**
    *   **Cause:** This error occurs when the LLM does not return a `function_call` object when one is expected.
    *   **Solution:** The `try...except` block in `run_orchestrator_agent` is designed to handle this. Do not remove it. If you are still encountering this error, it means the `initial_analysis_prompt` is not effective enough. You should improve the prompt to be more explicit about the expected JSON output.

*   **Error Type: Agent responds with raw JSON instead of calling a tool.**
    *   **Cause:** This happens when the `generate_content` function is not correctly configured to use tools.
    *   **Solution:** Ensure that the `tools` argument is passed inside the `config` object (`types.GenerateContentConfig`), and that the `response_mime_type` is set to `"application/json"`.

#### **4. Protocol for Modifying the Codebase**

1.  **Identify the Core Task:** Is the user asking to change the agent's behavior, the application's appearance, or the available tools?
2.  **Behavioral Changes:**
    *   Start by modifying the prompts in `agents.py`. This is the most effective way to change the agent's behavior.
    *   If the agent needs to perform a new action, add a new tool to `google_calendar.py` or `firestore_db.py`.
    *   Update the `initial_analysis_prompt` to recognize the intent for the new tool.
    *   Add a new `elif` block to `run_orchestrator_agent` to handle the new tool.
3.  **Appearance Changes:**
    *   Modify the HTML files in the `templates` directory.
    *   Modify the CSS files in the `static/css` directory.
    *   Modify the JavaScript files in the `static/js` directory.
4.  **Tool Changes:**
    *   When adding a new tool, ensure that the function signature is clear and the arguments are well-defined.
    *   Update the `initial_analysis_prompt` to include the new tool and the conditions for its use.

By following this protocol, you will be able to effectively and safely modify this codebase.
