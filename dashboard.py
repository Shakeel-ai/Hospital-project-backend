from flask import Flask, jsonify,request
import os
import sqlite3
from database import HospitalApp
from flask_cors import CORS

hospital_db = HospitalApp() 
app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = os.urandom(24)

@app.route('/ongoing_checkup',methods=["GET"])
def ongoing_checkup():
    id = request.args.get('id', default=1, type=int)
    try:
        data = hospital_db.patient_checkup(id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_table', methods=["GET"])
def get_appointment_data():
    try:
        # Fetch appointments from the database
        appointments = hospital_db.get_appointment_table('Appointments')
        
        # Return the data in JSON format
        return jsonify(appointments)
    except Exception as e:
        # Handle potential errors and return a JSON error message
        app.logger.error(f"Error fetching appointment data: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/checkup_complete',methods=['GET','POST'])
def checkup_complete():
    id = request.args.get('id',type=int)
    try:
        response,total_appointments = hospital_db.checkup_completed(id)
        return jsonify({'message' : response,'total_appointments':total_appointments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/total_appointments', methods=['GET'])
def total_appointments():
    try:
        total_appointments = hospital_db.get_total_appointments()
        return jsonify({'total_appointments': total_appointments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
      
@app.route('/login',methods=["POST"])
def login():
    data = request.json
    user_name = data.get('userName')
    password = data.get('password')
    doctor_password = hospital_db.login_data(user_name)
    if password == doctor_password:
        return "Login successful"
    else:
        return "Invalid id numbe  or password", 401
          

if __name__ == '__main__':
    # Run the Flask app in debug mode
    app.run(debug=True,port=8080)
