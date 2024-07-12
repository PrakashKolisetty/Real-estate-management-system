# gemini_app.py

from dotenv import load_dotenv
load_dotenv()  # Load all the environment variables

import streamlit as st
import os
import google.generativeai as genai
import logging
import mysql.connector

# Configure Genai Key
genai.configure(api_key="AIzaSyB6xFbm8YjkSnlz763yUA-RWrc7OFh79Ro")

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="Prakash@1",
            database="project"
        )
        if connection.is_connected():
            logging.info("Connected to MySQL database")
            return connection
    except Exception as e:
        logging.error("Error connecting to MySQL database: %s", e)

# Function To Load Google Gemini Model and provide queries as response
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    return response.text

# Function To retrieve query from the database
def read_sql_query(sql):
    # Execute the SQL query
    connection = connect_to_database()
    if connection is None:
        st.write("No connection")
        return None

    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        connection.commit()
    except Exception as e:
        logging.error("Error executing SQL query: %s", e)
        rows = None
    finally:
        cursor.close()
        connection.close()

    return rows

# Define Your Prompt
prompt = [
    """
    You are an expert in real estate database queries!
The database contains tables like property, buyer, seller, agent, agent_prop, seller_prop, and record.

In the property table:
- property_id: integer (Primary Key)
- prop_type: varchar(50)
- prop_price: decimal(10,2)
- house_no: varchar(20)
- street: varchar(100)
- city: varchar(100)
- pincode: varchar(10)
- state_name: varchar(100)
- bhk: integer
- property_status: enum('Available','Not Available','Sold')

In the buyer table:
- buyer_id: integer (Primary Key)
- buyer_name: varchar(255)
- phone_no: varchar(20)

In the seller table:
- seller_id: integer (Primary Key)
- seller_name: varchar(255)
- phone_no: varchar(20)

In the agent table:
- agent_id: integer (Primary Key)
- agent_name: varchar(255)
- phone_no: varchar(20)

In the seller_prop table:
- seller_id: integer (Primary Key)
- prop_id: integer (Primary Key)

In the agent_prop table:
- agent_id: integer (Primary Key)
- prop_id: integer (Primary Key)

In the record table:
- agent_id: integer (Primary Key)
- prop_id: integer (Primary Key)

Ask me anything about properties, buyers, sellers, agents, or their relationships!
    """
]

# Streamlit App
st.set_page_config(page_title="Real Estate Database Query Assistant")
st.header("Real Estate Database Query Assistant")

question = st.text_input("Input: ", key="input")
submit = st.button("Ask the question")

# if submit is clicked
if submit:
    response = get_gemini_response(question, prompt)
    st.write(response)
    # Remove backticks and SQL code block markers from the query
    sql_query = response.replace("```sql", "").replace("```", "")
    response = read_sql_query(sql_query)
    if response:
        st.subheader("The Response is")
        for row in response:
            st.header(row)
    else:
        st.subheader("No data found matching the query.")
