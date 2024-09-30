from flask import Flask, render_template, request,redirect,jsonify,session
from flask_cors import CORS
from database import HospitalApp
from llm import get_response
from twilio.twiml.messaging_response import MessagingResponse
import datetime
import hmac
import hashlib
import requests
from dotenv import load_dotenv
import os

load_dotenv()
pp_merchant_id = os.getenv('PP_MERCHANT_ID')
pp_password = os.getenv('PP_PASSWORD')
integrity_salt = os.getenv("INTEGRITY_SALT")
server_link = os.getenv('SERVER_LINK')

#create a flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)
#use database functions
hospital_app = HospitalApp()
patient_data = {}
doctor_data = {'doctor_id': "", 'doctor_name': "", 'doctor_fee': "",'key':""}

h_notification = ""

# define route for whatsapp messages
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    #get whatsapp messages
    incoming_msg = request.values.get('Body', '').strip().lower()
    user_number = request.values.get('From')
    resp = MessagingResponse()

    #handle session
   
    if user_number not in session:
        session[user_number] = {'state':'start','thread_id':''}
        if not incoming_msg.startswith(("hello",'helo','hy','hi','appointment','shedule')):
            resp.message("Welcome! 👋 Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Talk With Hospital Chatbot")
        
    user_session = session[user_number]    
    
           

    # handle initial greeting and options
    if user_session['state'] == 'start':
        if incoming_msg.startswith(("hello",'helo','hy','hi','appointment','shedule')):
            resp.message("Welcome! 👋 Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Talk With Hospital Chatbot")
            # for some notification from hospital
            if h_notification:
                resp.message(h_notification)
            user_session['state'] = 'option_selection'
    elif incoming_msg == 'm':
        user_session['state'] = 'option_selection'        
        resp.message("Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Talk With Hospital Chatbot")
    # handle appointment request
    elif user_session['state'] == 'option_selection':
        if incoming_msg == '1':
            resp.message(f"👩‍⚕️ Choose your doctor, enter patient data, and proceed to pay the doctor's fee securely on the JazzCash website. 💳💰\n Link: [{server_link}]") 
            user_session['state'] = 'go_to_web'
        elif incoming_msg == '2':
            resp.message("🤖 Please ask your question.")
            user_session['state'] = 'conversation'
        else:
            resp.message("❎ Sorry! Invalid input. Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Talk With Hospital Chatbot.")    
    elif user_session['state'] == 'conversation':
        response, thread_id = get_response(incoming_msg,user_session['thread_id'])
        if user_session['thread_id'] == "":
            user_session['thread_id'] = thread_id

        resp.message(f"🤖: {response}")

    elif incoming_msg == "2":
        user_session['state'] = 'option_selection'
        resp.message('Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Talk With Hospital Chatbot."')

    else:
        resp.message("❎ Sorry! Invalid input. Please reply with an option number:\n👇\n\n1️⃣ Get Appointment\n2️⃣ Retrieve the current number of patients undergoing checkup.")
    
    session[user_number] = user_session
    return str(resp)
    
# route for get doctor list to select doctor
@app.route('/get_doctor_list',methods=['GET', 'POST'])
def get_doctor_list_route():
    # Call the function to fetch the list of doctors from the database
    doctors = hospital_app.get_doctor_list()
    # Return the list of doctors as JSON response
    return jsonify({'doctors': doctors})

# route for web form to select doctor
@app.route('/', methods=['GET', 'POST'])
@app.route('/select_doctor',methods=['GET', 'POST'])
def select_doctor():
    if request.method == 'POST':
        # fetch the doctor list using the defined function

        # retrieve selected doctor data from the form submission
        doctor_id = request.form['doctor_id']
        doctor_name = request.form['doctor_name']
        doctor_fee = request.form['doctor_fee']
        session['doctor_status'] = request.form['doctor_status']

        # store selected doctor data in the session
        session['selected_doctor'] = {
            'doctor_id': doctor_id,
            'doctor_name': doctor_name,
            'doctor_fee': doctor_fee
        }

        # redirect or return a response as needed
        return redirect(f"{server_link}/add_patient_data")
    doctors_response = requests.get(f"{server_link}/get_doctor_list")
    doctors = doctors_response.json()['doctors']
    return render_template('select.html',doctors = doctors)

# route for get patient data in a form
@app.route('/add_patient_data', methods=['GET', 'POST'])
def add_patient_data():
    if 'selected_doctor' not in session:
        return redirect(f"{server_link}/select_doctor")
    # doctor appointment control
    doctor_status = session['doctor_status']
    if doctor_status == 'stop':
        message = 'Appointments are stopped by the doctor.'
        return render_template('message.html', message=message)
    elif doctor_status == 'full':
        message = 'Appointment quota is full. Please try again later.'
        return render_template('message.html', message=message)
    elif doctor_status == 'start':
        if request.method == 'POST':
            
            # key to store every patient data separatly
            current_datetime = datetime.datetime.now()
            key = f"T{current_datetime.strftime('%Y%m%d%H%M%S')}"
            session['key'] = key
            # get data from web form
            patient_data = {
                'patient_name': request.form.get('patient_name'),
                'gender': request.form.get('gender'),
                'age': request.form.get('age'),
                'phone_number': request.form.get('phone_number'),
                'address': request.form.get('address'),
            }
            all_patient_data = session.get('all_patient_data',{})
            all_patient_data[key] = patient_data
            session['all_patient_data'] = all_patient_data
            return redirect(f"{server_link}/checkout")
        
        return render_template('form.html')

# route for checkout page before payment 
@app.route('/checkout',methods = ['GET', 'POST'])
def checkout():
    
    doctor_data = session['selected_doctor']
    doctor_name = doctor_data['doctor_name']
    doctor_fee = doctor_data['doctor_fee']

    pp_Amount = int(doctor_fee)
    # get the current date and time
    current_datetime = datetime.datetime.now()
    pp_TxnDateTime = current_datetime.strftime('%Y%m%d%H%M%S')
    
    # create expiy date and time by adding one hour to the current date and time
    expiry_datetime = current_datetime + datetime.timedelta(hours=1)
    pp_TxnExpiryDateTime = expiry_datetime.strftime('%Y%m%d%H%M%S')

    pp_TxnRefNo = session['key']
    
    post_data = {
        "pp_Version": "1.0",
        "pp_TxnType": "",
        "pp_Language": "EN",
        "pp_MerchantID":"MC87005",
        "pp_SubMerchantID": "",
        "pp_Password": "6894z12hx0",
        "pp_BankID": "TBANK",
        "pp_ProductID": "RETL",
        "pp_TxnRefNo": pp_TxnRefNo,
        "pp_Amount": pp_Amount,
        "pp_TxnCurrency": "PKR",
        "pp_TxnDateTime": pp_TxnDateTime,
        "pp_BillReference": "billRef",
        "pp_Description": "Description of transaction",
        "pp_TxnExpiryDateTime": pp_TxnExpiryDateTime,
        "pp_ReturnURL": f"{server_link}/success",
        "pp_SecureHash": "",
        "ppmpf_1": "1",
        "ppmpf_2": "2",
        "ppmpf_3": "3",
        "ppmpf_4": "4",
        "ppmpf_5": "5"
    }

    # calculate the secure hash
    sorted_string = '&'.join(f"{key}={value}" for key, value in sorted(post_data.items()) if value != "")
    pp_SecureHash = hmac.new(
    "zz512tst1y".encode(),
    sorted_string.encode(),
    hashlib.sha256
).hexdigest()
    session['pp_SecureHash'] = pp_SecureHash
    post_data['pp_SecureHash'] = pp_SecureHash
    return render_template('checkout.html', product_name=doctor_name, product_price=doctor_fee, post_data=post_data)


# route for for payment status recieve and do action
@app.route('/success', methods=['POST'])
def success(): 
    if 'pp_SecureHash' not in session:
        return redirect(f"{server_link}/select_doctor") 
    data = request.form
    payment_status = data.get('pp_ResponseCode')
    response_message = data.get('pp_ResponseMessage')
    transaction_id = data.get('pp_TxnRefNo')
    
    if payment_status == '199':
        # fetch patient data
        patient_dic = session.get('all_patient_data', {})
        patient_data = patient_dic.get(transaction_id, {})
        
        # add data to the database
        last_id = hospital_app.add_patient_data(
            patient_name=patient_data.get('patient_name'),
            gender=patient_data.get('gender'),
            age=patient_data.get('age'),
            phone_number=patient_data.get('phone_number'),
            address=patient_data.get('address'),
            table="Appointments"
        )
        
        message = f"Record inserted with Token No {last_id}. Thank you for providing your information."
        color = 'green' 
        
    else:
        message = "Payment failed. Appointment not scheduled."
        color = 'red'  
        
    return render_template('success.html', message=message, color=color, payment_failed=(payment_status != '199'))

@app.route('/ongoing_checkup',methods=["GET"])
def ongoing_checkup():
    id = request.args.get('id', default=1, type=int)
    try:
        data = hospital_app.patient_checkup(id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_table', methods=["GET"])
def get_appointment_data():
    try:
        # Fetch appointments from the database
        appointments = hospital_app.get_appointment_table('Appointments')
        
        return jsonify(appointments)
    except Exception as e:
        app.logger.error(f"Error fetching appointment data: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/checkup_complete',methods=['GET','POST'])
def checkup_complete():
    id = request.args.get('id',type=int)
    try:
        response,total_appointments = hospital_app.checkup_completed(id)
        return jsonify({'message' : response,'total_appointments':total_appointments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/total_appointments', methods=['GET'])
def total_appointments():
    try:
        total_appointments = hospital_app.get_total_appointments()
        return jsonify({'total_appointments': total_appointments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
      
@app.route('/login',methods=["POST"])
def login():
    data = request.json
    user_name = data.get('userName')
    password = data.get('password')
    doctor_password = hospital_app.login_data(user_name)
    if password == doctor_password:
        return "Login successful"
    else:
        return "Invalid id numbe  or password", 401


if __name__ == '__main__': 
    app.run(debug=True, port=8080)
    