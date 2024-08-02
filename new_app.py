import streamlit as st
import pandas as pd
import requests
import json
from io import StringIO

# Set up the title and description
st.title("Query Generation Tool")
st.write("This application enables the mapping of source and target data systems and generates queries for comprehensive database testing.")

# Source System selection
st.sidebar.header("Source System")
source_system = st.sidebar.selectbox(
    "Select Source System", ["--Select--", "SQL Server", "Oracle", "RDBMS", "Flat Files"], index=0
)

# Target System selection
st.sidebar.header("Target System")
target_system = st.sidebar.selectbox(
    "Select Target System", ["--Select--", "SQL Server", "Oracle"], index=0
)

# Select Type of Validation
st.sidebar.header("Select Type of Validation")
validation_type = st.sidebar.selectbox(
    "Select Validation Type", ["--Select--", "Select", "Update", "Check for Duplicate", "Null Values", "Aggregate Function", "Record count", "Compare source and target records"]
)

# Adjust Temperature with tooltip
st.sidebar.header("Adjust Temperature")
temperature = st.sidebar.slider(
    "Temperature", min_value=0.0, max_value=2.0, value=1.0, step=0.1,
    help="Controls the randomness and creativity of the output.\nFor creative writing: Higher temperature and higher Top P might be suitable.\nFor factual writing: Lower temperature and lower Top P might be more appropriate."
)

# Adjust Top P with tooltip
st.sidebar.header("Adjust Top P")
top_p = st.sidebar.slider(
    "Top P", min_value=0.0, max_value=1.0, value=0.95, step=0.1,
    help="Controls the diversity of the output by focusing on the most probable words.\nHow it works:\nLower Top P (closer to 0): The model will only consider the most probable words, leading to less diverse and more predictable output.\nHigher Top P (closer to 1): The model will consider a wider range of words, leading to more diverse and potentially more creative output, but potentially less coherent."
)

# Function to display condition dropdown and textbox
def condition_input(section_name):
    st.header(f"{section_name} Table Details")
    table_input = st.text_area(f"Paste {section_name} Table Data Here (from Excel)", height=200)
    if table_input:
        table = pd.read_csv(StringIO(table_input), sep="\t")
        st.write(f"{section_name} Table:")
        st.dataframe(table)
    else:
        table = None

    condition = st.selectbox(f"{section_name} Condition", ["—Select—", "Order by", "Group by"])
    column_name = st.text_input(f"{section_name} Column Name", "")
    logic = st.text_area(f"{section_name} Logic", "")

    return table, condition, column_name, logic

# Source Table Details
source_table, source_condition, source_column, source_logic = condition_input("Source")

# Target Table Details (mandatory)
target_table, target_condition, target_column, target_logic = condition_input("Target")
if target_table is None:
    st.error("Target table details are mandatory.")

# Google Gemini API Key input
st.header("Enter Your Google Gemini API Key")
api_key = st.text_input("Your Google Gemini API Key", type="password")

# Function to verify the API key (dummy function, as the Google Gemini API doesn't provide a direct way to verify API keys)
def verify_api_key(api_key):
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents":[{"parts":[{"text":"Say hello"}]}]}
        )
        return response.status_code == 200
    except requests.RequestException as e:
        return False

# Verify API key button
if st.button("Verify API Key"):
    if verify_api_key(api_key):
        st.success("API key is valid.")
    else:
        st.error("API key is invalid. Please check and try again.")

# Function to generate the query using Google Gemini API
def generate_query(api_key, source_system, target_system, validation_type, source_table, target_table, source_condition, source_column, source_logic, target_condition, target_column, target_logic, temperature, top_p):
    prompt = f"""
    You are a database expert. Generate a database query according to selected Source System and target system technology and based on following details and :

    Source System: {source_system if source_system is not None else "Not provided"}
    Target System: {target_system}
    Validation Type: {validation_type}
    Source Table: {source_table if source_table is not None else "Not provided"}
    Target Table: {target_table}
    Source Condition: {source_condition if source_condition is not None else "Not provided"}
    Source Column: {source_column if source_column is not None else "Not provided"}
    Source Logic: {source_logic if source_logic is not None else "Not provided"}
    Target Condition: {target_condition if target_condition is not None else "Not provided"}
    Target Column: {target_column if target_column is not None else "Not provided"}
    Target Logic: {target_logic if target_logic is not None else "Not provided"}

    Generate an appropriate query:
    """
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "topP": top_p
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                ]
            }
        )
        response.raise_for_status()

        # Check response content type
        content_type = response.headers.get('Content-Type')
        if 'application/json' not in content_type:
            raise ValueError(f"Unexpected content type: {content_type}")

        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON response: {e}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return {"error": str(e)}

# Function to parse the response and extract SQL query, explanation, and notes
def parse_response(response):
    content = response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    sql_query = content.split('```sql')[1].split('```')[0].strip() if '```sql' in content else 'No SQL query generated.'
    explanation = content.split('**Explanation:**')[1].split('**Note:**')[0].strip() if '**Explanation:**' in content else ''
    note = content.split('**Note:**')[1].strip() if '**Note:**' in content else ''
    return sql_query, explanation, note

# Generate Query button functionality
if st.button("Generate Query"):
    if not api_key:
        st.error("Please add your Google Gemini API key.")
    elif target_table is None or target_table.empty:
        st.error("Please enter target table details.")
    else:
        # Verify the API key before generating the query
        if not verify_api_key(api_key):
            st.error("API key is invalid. Please check and try again.")
        else:
            # Generate the query using Google Gemini API
            response = generate_query(api_key, source_system, target_system, validation_type, source_table, target_table, source_condition, source_column, source_logic, target_condition, target_column, target_logic, temperature, top_p)
            sql_query, explanation, note = parse_response(response)

            st.header("Generated Query")
            st.text_area("Query", value=sql_query, height=200)

            if explanation:
                st.header("Explanation")
                st.write(explanation)

            if note:
                st.header("Note")
                st.write(note)
