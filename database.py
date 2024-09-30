# import required libraries
import os
import datetime
import pytz
import sqlite3
import pandas as pd
datetim = datetime.datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')


# create a class
class HospitalApp:
  def __init__(self) -> None:
    self.conn = sqlite3.connect("hospital.db")
    self.cursor = self.conn.cursor()
    
    self.sqlite_datetime = datetime.datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')

  # create new table function  
  def create_patients_table(self):
    try:
      conn = sqlite3.connect("hospital.db")
      cursor = conn.cursor()
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS Doctors (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Doctor_Name VARCHAR(50) NOT NULL,         
            Specialties VARCHAR(100) NOT NULL,
            Fees INTEGER  NOT NULL,
            Password VARCHAR(12) NOT NULL,
            Phone_Number VARCHAR(20)  
            )           
          """)
      conn.commit()
      
    except sqlite3.Error as error:
      return f"Error creating table: {error}"

  # To book patients appoinments
  def add_patient_data(self,patient_name, gender, age, phone_number, address,table):
      try:
        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(Id) FROM {table}")
        last_row = cursor.fetchone()[0]
        
          
        
        cursor.execute(f"""
          INSERT INTO {table} (
          Patient_Name,Gender,Age,Phone_Number,Address,Date,Time)
          VALUES (?,?,?,?,?,?,?)
          """, (patient_name,gender,age,phone_number,address,datetime.datetime.now().strftime('%d-%m-%Y'),datetime.datetime.now().strftime('%I:%M:%S %p')))
        conn.commit() 
        last_id = cursor.lastrowid
        
        return last_id
      except sqlite3.Error as e:
        return str(f"Error: {e}") 
      
    

  # To see patient appoinments one by one
  def patient_checkup(self,Id=1):
    try:
      conn = sqlite3.connect("hospital.db")
      cursor = conn.cursor()
      cursor.execute(f"SELECT * FROM Appointments WHERE Id ={Id}")
      data = cursor.fetchone()
      if data:
        return dict(zip([column[0] for column in cursor.description], data))
      else:
        return "No Appointment Found on Provided ID"
    except sqlite3.Error as e:
      return f"Error: {e}"
    
  # To mark patient as checkup completed
  def checkup_completed(self,Id):
    try:
      conn = sqlite3.connect('hospital.db')
      cursor = conn.cursor()
      cursor.execute(f"SELECT * FROM Appointments WHERE Id ={Id}")
      data = cursor.fetchone()
      if data:
        cursor.execute(f"""
                INSERT INTO Patient_record (
                TokenNumber,Patient_Name,Gender,Age,Phone_Number,Address,Date,Time)
                VALUES (?,?,?,?,?,?,?,?)
                """, data)
        cursor.execute(f"DELETE FROM Appointments where Id = {Id}")
        cursor.execute("SELECT COUNT(*) FROM Appointments")
        row = cursor.fetchone()
        total_rows = row[0] if row else 0
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Appointments';")
        conn.commit()
        conn.close()
        return "Record moved successfuly",total_rows
      else:
        f"No appointment found with Id {Id}", 0
    except sqlite3.Error as e:
      return(f"Error: {e}"),0  

  def get_total_appointments(self):
    conn = sqlite3.connect('hospital.db')  
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Appointments")
    row = cursor.fetchone()
    total_rows = row[0] if row else 0
    return total_rows

  # patients can check their appointment status
  def check_appointment_status(self,Id):
    return f"✅ The current number of patient undergoing checkup is : *{Id}*\n\n Reply with *M* for main menu"

  # To add column in ex. table
  def add_column(self):
    try:
      self.cursor.execute("""
        ALTER TABLE Patient_record
        ADD COLUMN DateTime DATETIME;
      """)
      self.conn.commit()
      
    except sqlite3.Error as e:
      return f"Error : {e}" 


  #delete any table through name
  def delete_table(self,table_name):
    try:
        self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.commit()
    except sqlite3.Error as e:
        return f"Error : {e}"

# create a function to download tables
  def download_table(self,table_name):
    try:
      query = (f"SELECT * FROM {table_name} ")
      df = pd.read_sql_query(query,self.conn)
      df.to_csv(f"{table_name}.csv",index=False)
      with open(f"{table_name}.csv","rb") as file:
        file_content = file.read()
      #st.download_button(label="Download Excel File",data=file_content,file_name=f"{table_name}.csv")
      if os.path.exists(f"{table_name}.csv"):
        os.remove(f"{table_name}.csv")
    except sqlite3.Error as e:
      return f"Error : {e}"

  # To close database connection    
  def close_connections(self):
    self.conn.close()

  # To get patient id of appointments
  def get_appointments_id(self):
    try:
      self.cursor.execute("SELECT Id FROM Appointments")
      patient_ids = [row[0] for row in self.cursor.fetchall()] 
      total_patient = len(patient_ids)
      return patient_ids, total_patient
    except sqlite3.Error as e:
      return f"Error : {e}"

  # check patient record table length
  def check_length(self):
    self.cursor.execute("SELECT MAX(Id) FROM Patient_record") 
    max_id = self.cursor.fetchone()[0]  
    if max_id is not None and max_id > 100:
      return True
    else:
      return False

  # Delete Patient record if limit exceeded
  def delete_patient_record(self):
    try:
      self.cursor.execute("DELETE FROM Patient_record")  
      self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='Patient_record';")
      self.conn.commit()      
    except sqlite3.Error as e:
      return f"Error : {e}" 
  
  #get doctor list
  def get_doctor_list(self):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM DOCTORS')
    doctors = cursor.fetchall()
    doctor_list = [{"id": doctor[0], "name": doctor[1], "specialties": doctor[2],'fee':doctor[3],'doctor_status':doctor[6]} for doctor in doctors]
    conn.close()  
    return doctor_list
  
  def get_doctor_fees(self,id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM Doctors WHERE Id = {id}')
    doctor_data = cursor.fetchone()
    doctor_name = doctor_data[1]
    specialty = doctor_data[2]
    fee = doctor_data[3]
    return doctor_name, specialty,fee
  
  def login_data(self,doctor_name):
    try:
      conn = sqlite3.connect('hospital.db')
      cursor = conn.cursor()
      cursor.execute(f"SELECT * FROM Doctors WHERE Id ={doctor_name}")
      row = cursor.fetchone()
      password = row[4]
      conn.close()
      return password
    except:
        return "Invalid username"




  def get_appointment_table(self,table_name):
    try:
        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        appointments = [dict(zip(column_names, row)) for row in rows]
    except sqlite3.Error as e:
        return (f"Database error: {e}")
    except Exception as e:
        return  (f"Error: {e}")
    finally:
        if conn:
            conn.close()
    return appointments

    

#if __name__ == "__main__":
  #app = HospitalApp()
  #app.create_patients_table()
  #app.add_column()
  #if st.button('Check password'):
  #  data = app.login_data("Imran")
  #  st.write(data)
  #if st.button('Get Table'):
  #  res = app.get_appointment_table('Appointments')
  #  st.write(res)
  #limit = st.number_input("Enter Patient Appointment Limit",min_value=0,max_value=10000,step=1)
  #app.add_patient_data(limit)
  #Id = st.number_input("Enter Id",step=1)
  #if Id:
  #  data = app.patient_checkup(Id=Id)
  #  if data:
  #    if st.button("Completed"):
  #      app.checkup_completed(Id=Id)
  #if st.button("Check Appointments"):
  #  patient_id, total_patiens = app.get_appointments_id()  
  #  st.write(f"Total Patients are : {total_patiens}")
  #  if patient_id:
  #    st.write(patient_id)
  #delete_table = app.check_length()
  #if delete_table == True:
  #  st.warning("The Patient_record table has exceeded the limit. Click the buttons below to download data and then delete it.")

  #  if st.button("Download"):
  #    app.download_table(table_name="Patient_record")
  #  if st.button("Delete"):
  #    app.delete_patient_record()    
  #with st.sidebar: 
  #  table_name = st.radio("Select Table",("Appointments","Patient_record"))
  #  if st.button("Get Record"):
  #    app.download_table(table_name)
  #  if st.button("Check_status"):
  #    app.check_appointment_status(Id) 
  #app.close_connections()    
        
