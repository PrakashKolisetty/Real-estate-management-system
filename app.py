import pymongo
from flask import Flask, render_template, request, redirect, url_for, session,jsonify
from pymongo import MongoClient
import mysql.connector
import random
import logging
import subprocess
from dotenv import load_dotenv
load_dotenv()  # Load all the environment variables
import google.generativeai as genai

genai.configure(api_key="AIzaSyB6xFbm8YjkSnlz763yUA-RWrc7OFh79Ro")

app = Flask(__name__)
app.secret_key = "my_secret_key_1234567890"

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["feedbacks"]
collection = db["buyer_feedbacks"]


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


def generate_user_id():
    return random.randint(10000, 99999)


def register_user(name, password, phone, role):
    connection = connect_to_database()
    cursor = connection.cursor()

    user_id = generate_user_id()

    try:
        if role == "seller":
            cursor.execute("INSERT INTO seller (seller_id, seller_name, phone_no) VALUES (%s, %s, %s)", (user_id, name, phone))
        elif role == "buyer":
            cursor.execute("INSERT INTO buyer (buyer_id, buyer_name, phone_no) VALUES (%s, %s, %s)", (user_id, name, phone))
        elif role == "agent":
            cursor.execute("INSERT INTO agent (agent_id, agent_name, phone_no) VALUES (%s, %s, %s)", (user_id, name, phone))

        cursor.execute("INSERT INTO passwords (user_id, password,role) VALUES (%s, %s,%s)", (user_id, password,role))
        connection.commit()
        cursor.close()
        connection.close()
        return user_id
    except Exception as e:
        logging.error("Error registering user: %s", e)
        return None

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']
        role = request.form['role']

        if password != confirm_password:
            return render_template('registration.html', error_message="Passwords do not match")

        user_id = register_user(name, password, phone, role)

        if user_id:
            return render_template('registration_success.html', user_id=user_id)
        else:
            return render_template('registration.html', error_message="Error registering user")

    return render_template('registration.html', error_message=None)


def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    return response.text

# Function To retrieve query from the database
def read_sql_query(sql):
    # Execute the SQL query
    connection = connect_to_database()
    if connection is None:
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
-record_id: integer (Primary key) 
-buyer_id: integer
-seller_id: integer 
-property_id: integer 
-agent_id: integer 
-sale_type: varchar(50) 
-date: date 
-amount: decimal(10,2)

Ask me anything about properties, buyers, sellers, agents, or their relationships!
    """
]

# Route for the query input page
@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        question = request.form.get('question')
        response = get_gemini_response(question, prompt)
        print("Generated SQL query: %s", response)
        # Remove backticks and SQL code block markers from the query
        sql_query = response.replace("```sql", "").replace("```", "")
        result = read_sql_query(sql_query)
        return jsonify({'question': question, 'response': result})
    return render_template('query.html')
# @app.route('/query')
# def query():
#     # Run the Streamlit app
#     subprocess.Popen(['streamlit', 'run', 'gemini_app.py'])
#     # Redirect to the Streamlit page
#     return redirect(url_for('login'))

@app.route('/logout', methods=['POST'])
def logout():

    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        user_id = request.form['user_id']
        password = request.form['password']


        if user_id == '1234' and password == 'Prakash@1':
            return redirect(url_for('admin_page'))


        connection = connect_to_database()
        if connection is None:
            return render_template('login.html', error_message="Failed to connect to database. Please try again later.")
        cursor = connection.cursor()


        query = "SELECT role FROM passwords WHERE user_id = %s AND password = %s"
        cursor.execute(query, (user_id, password))
        user_role = cursor.fetchone()

        if user_role:
            role = user_role[0]

            cursor.close()
            connection.close()


            session['user_id'] = user_id

            # Redirect to corresponding page based on the role
            if role == "seller":
                return redirect(url_for('property_registration'))
            elif role == "buyer":
                return redirect(url_for('buyer_page'))
            elif role == "agent":
                return redirect(url_for('agent_page'))
        else:
            # Close database connection
            cursor.close()
            connection.close()

            # If credentials don't match, render login page again with error message
            return render_template('login.html', error_message="Invalid user_id or password")

    return render_template('login.html', error_message=None)


@app.route('/agent_page')
def agent_page():
    user_id = session.get('user_id')
    agent_properties = fetch_agent_properties(user_id)  # Assuming you have the current agent's ID
    sellers = fetch_all_sellers()  # Function to fetch all sellers
    return render_template('agent_page.html', agent_properties=agent_properties, sellers=sellers)


# Function to fetch property details assigned to the current agent
# Function to fetch property details assigned to the current agent along with seller information
def fetch_agent_properties(agent_id):
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT property.*, seller.seller_name
        FROM property
        INNER JOIN seller_prop ON property.property_id = seller_prop.prop_id
        INNER JOIN seller ON seller_prop.seller_id = seller.seller_id
        INNER JOIN agent_prop ON property.property_id = agent_prop.prop_id
        WHERE agent_prop.agent_id = %s
    """, (agent_id,))
    agent_properties = cursor.fetchall()

    cursor.close()
    connection.close()
    return agent_properties


# Function to fetch all sellers
def fetch_all_sellers():
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM seller")
    sellers = cursor.fetchall()

    cursor.close()
    connection.close()
    return sellers


from flask import render_template

@app.route('/sell_property', methods=['POST'])
def sell_property():
    if request.method == 'POST':
        property_id = request.form['property_id']
        buyer_id = request.form['buyer_id']
        sale_type = request.form['sale_type']
        date = request.form['date']
        amount = request.form['amount']
        agent_id = session.get('user_id')  # Assuming you have the agent's ID in session
        seller_id = get_seller_id(property_id)  # Function to get seller_id from property_id

        # Update tables and set property status to 'Sold'
        record_id = update_tables(buyer_id, seller_id, property_id, agent_id, sale_type, date, amount)

        if record_id:
            # Property sold successfully, set sold_successfully to True
            return render_template('agent_page.html', sold_successfully=True, agent_properties=fetch_agent_properties(agent_id))
        else:
            # Error occurred while updating tables
            return render_template('agent_page.html', error_message="Error occurred while selling property", agent_properties=fetch_agent_properties(agent_id))

    # Handle invalid request method
    return 'Invalid request'






def get_seller_id(property_id):
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT seller_id FROM seller_prop WHERE prop_id = %s", (property_id,))
        result = cursor.fetchone()
        if result:
            seller_id = result[0]
        else:
            seller_id = None
    except Exception as e:
        logging.error("Error fetching seller ID: %s", e)
        seller_id = None
    finally:
        cursor.close()
        connection.close()

    return seller_id


def generate_record_id(connection):
    cursor = connection.cursor()
    while True:
        record_id = random.randint(10000, 99999)  # Generate a random 5-digit number
        cursor.execute("SELECT * FROM record WHERE record_id = %s", (record_id,))
        if not cursor.fetchone():  # If record ID doesn't exist in the database, break the loop
            break
    cursor.close()
    return record_id

import logging

def update_tables(buyer_id, seller_id, property_id, agent_id, sale_type, date, amount):
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor()

    try:
        record_id = generate_record_id(connection)

        cursor.execute("UPDATE property SET property_status = 'Sold' WHERE property_id = %s", (property_id,))
        # Insert into record table
        cursor.execute("INSERT INTO record (record_id, buyer_id, seller_id, property_id, agent_id, sale_type, date, amount) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (record_id, buyer_id, seller_id, property_id, agent_id, sale_type, date, amount))

        connection.commit()
        logging.info("Database updated successfully")
    except Exception as e:
        logging.error("Error updating record table: %s", e)
        return None
    finally:
        cursor.close()
        connection.close()

    return record_id


# Admin page
@app.route('/admin_page')
def admin_page():
    properties = fetch_all_properties()
    agents = fetch_all_agents()
    records = fetch_all_records()  # New function to fetch records
    return render_template('admin_page.html', properties=properties, agents=agents, records=records)  # Passing records to the template

# Function to fetch all records
# Function to fetch all records
def fetch_all_records():
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            record.*, 
            agent.agent_name AS agent_name, 
            seller.seller_name AS seller_name,
            buyer.buyer_name AS buyer_name
        FROM 
            record
        LEFT JOIN 
            agent ON record.agent_id = agent.agent_id
        LEFT JOIN 
            seller ON record.seller_id = seller.seller_id
        LEFT JOIN
            buyer ON record.buyer_id = buyer.buyer_id
    """)
    records = cursor.fetchall()
    cursor.close()
    connection.close()
    return records

# Function to fetch all properties
def fetch_all_properties():
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
    property.*, 
    agent.agent_id AS assigned_agent_id, 
    agent.agent_name AS assigned_agent_name
FROM 
    property
LEFT JOIN 
    agent_prop ON property.property_id = agent_prop.prop_id
LEFT JOIN 
    agent ON agent_prop.agent_id = agent.agent_id

    """)
    properties = cursor.fetchall()
    cursor.close()
    connection.close()
    return properties

# Function to fetch all agents
def fetch_all_agents():
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM agent")
    agents = cursor.fetchall()

    cursor.close()
    connection.close()
    return agents


@app.route('/assign_agent', methods=['POST'])
def assign_agent():
    if request.method == 'POST':
        agent_id = request.form['agent_id']
        property_id = request.form['property_id']

        connection = connect_to_database()
        if connection is not None:
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO agent_prop (agent_id, prop_id) VALUES (%s, %s)", (agent_id, property_id))
                connection.commit()
                cursor.close()
                connection.close()
                # Redirect to the admin page after successfully assigning an agent
                return redirect(url_for('admin_page'))
            except Exception as e:
                logging.error("Error assigning agent to property: %s", e)
                return "Error assigning agent to property"
        else:
            return "Failed to connect to the database"

    return "Invalid request"



def fetch_available_properties():
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT seller.seller_name, agent.agent_name AS assigned_agent_name, agent.phone_no, property.* 
        FROM property 
        INNER JOIN seller_prop ON property.property_id = seller_prop.prop_id 
        INNER JOIN seller ON seller_prop.seller_id = seller.seller_id 
        LEFT JOIN agent_prop ON property.property_id = agent_prop.prop_id 
        LEFT JOIN agent ON agent_prop.agent_id = agent.agent_id
    """)
    properties = cursor.fetchall()
    cursor.close()
    connection.close()
    return properties


# Buyer page
@app.route('/buyer_page')
def buyer_page():
    properties = fetch_available_properties()
    return render_template('buyer_page.html', properties=properties)


@app.route('/add_feedback', methods=['POST'])
def add_feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        user_id = session.get('user_id')
        property_id = request.form['property_id']  # Retrieve property_id from the form

        # Store feedback in MongoDB
        if user_id:
            feedback_data = {'user_id': user_id, 'property_id': property_id, 'feedback': feedback}  # Include property_id in feedback data
            collection.insert_one(feedback_data)
            return redirect(url_for('buyer_page'))

    return 'Invalid request'


# Show feedbacks route
@app.route('/show_feedbacks', methods=['GET'])
def show_feedbacks():
    property_id = request.args.get('property_id')
    if property_id:
        # Retrieve feedbacks for the given property ID
        feedbacks = list(collection.find({'property_id': property_id}))
        return render_template('feedbacks.html', feedbacks=feedbacks)
    else:
        return 'Property ID is missing in the request parameters', 400


# Home page
@app.route('/home')
def home():
    return render_template('home.html')

def generate_property_id(connection):
    cursor = connection.cursor()
    while True:
        property_id = random.randint(100000, 999999)  # Generate a random 6-digit number
        cursor.execute("SELECT * FROM property WHERE property_id = %s", (property_id,))
        if not cursor.fetchone():  # If property ID doesn't exist in the database, break the loop
            break
    cursor.close()
    return property_id

# Page for property registration for seller
def fetch_past_properties(user_id):
    connection = connect_to_database()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM seller_prop WHERE seller_id = %s", (user_id,))
    seller_properties = cursor.fetchall()
    past_properties = []

    for seller_property in seller_properties:
        property_id = seller_property['prop_id']
        cursor.execute("SELECT * FROM property WHERE property_id = %s", (property_id,))
        property_details = cursor.fetchone()
        past_properties.append(property_details)

    cursor.close()
    connection.close()
    return past_properties



# Property registration page for seller
@app.route('/property_registration', methods=['GET', 'POST'])
def property_registration():
    if request.method == 'POST':
        # Fetch form data
        prop_type = request.form['prop_type']
        prop_price = request.form['prop_price']
        house_no = request.form['house_no']
        street = request.form['street']
        city = request.form['city']
        pincode = request.form['pincode']
        state_name = request.form['state_name']
        bhk = request.form['bhk']
        property_status = request.form['property_status']

        # Fetch user ID from session (assuming user is already logged in)
        user_id = session.get('user_id')
        print(user_id)

        # Connect to database
        connection = connect_to_database()

        # Generate a unique random property ID
        property_id = generate_property_id(connection)

        # Insert data into property table
        cursor = connection.cursor()
        query = "INSERT INTO property (property_id, prop_type, prop_price, house_no, street, city, pincode, state_name, bhk, property_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (property_id, prop_type, prop_price, house_no, street, city, pincode, state_name, bhk, property_status)
        cursor.execute(query, values)

        # Update seller_prop table
        cursor.execute("INSERT INTO seller_prop (seller_id, prop_id) VALUES (%s, %s)", (user_id, property_id))

        connection.commit()

        # Close database connection
        cursor.close()
        connection.close()

        # Fetch user's past properties
        past_properties = fetch_past_properties(user_id)

        return render_template('property_registration.html', success_message="Property registered successfully!",
                               past_properties=past_properties)

    # Fetch user's past properties
    user_id = session.get('user_id')
    past_properties = fetch_past_properties(user_id)

    return render_template('property_registration.html', past_properties=past_properties)


if __name__ == '__main__':
    # Attempt to connect to the database
    connection = connect_to_database()
    if connection:
        logging.info("Connected to MySQL database")
        connection.close()
    else:
        logging.error("Failed to connect to MySQL database")

    # Run the Flask application
    app.run(debug=True)