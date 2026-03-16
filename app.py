from flask import Flask, request, jsonify, render_template
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os
import pandas as pd
import re
import matplotlib.pyplot as plt
import io
import base64

# Load environment variables
load_dotenv()
BOT_NAME = "MediAssist AI"

app = Flask(__name__)

dataset = None

# Initialize Hugging Face client
client = InferenceClient(
    api_key=os.getenv("HF_TOKEN")
)

# Conversation memory with system prompt
chat_history = [
    {
        "role": "system",
        "content": (
            "You are MediAssist AI, a hospital information assistant. "
            "You help explain medical terms, symptoms, and patient vitals in simple language. "
            "You do NOT diagnose diseases or replace doctors. "
            "If a question requires medical diagnosis, advise the user to consult a healthcare professional."
        )
    }
]


def analyze_vitals(patient_id=None):

    global dataset

    if dataset is None:
        return "No dataset uploaded."
    
    if patient_id:
        data = dataset[dataset["patient_id"].astype(str).str.lower() == patient_id.lower()]
    else:
        data = dataset

    results = []

    for index, row in data.iterrows():

        issues = []

        if row["heart_rate"] > 100:
            issues.append("High heart rate (Tachycardia)")
        elif row["heart_rate"] < 60:
            issues.append("Low heart rate (Bradycardia)")

        if row["oxygen"] < 95:
            issues.append("Low oxygen level")

        if row["temperature"] > 37.5:
            issues.append("Fever detected")

        if row["respiratory_rate"] > 20:
            issues.append("High respiratory rate")

        try:
            systolic, diastolic = map(int, str(row["blood_pressure"]).split("/"))

            if systolic >= 140 or diastolic >= 90:
                issues.append("High blood pressure (Hypertension)")
            elif systolic <= 90 or diastolic <= 60:
                issues.append("Low blood pressure (Hypotension)")

        except:
            issues.append("Invalid blood pressure format")

        issue_count = len(issues)

        if issue_count == 0:
            risk = "Normal"
        elif issue_count <= 2:
            risk = "Moderate Risk"
        else:
            risk = "High Risk"

        if issues:
            results.append(
                f"Patient {row['patient_id']} → Risk Level: {risk}. Issues: {', '.join(issues)}"
            )
        else:
            results.append(
                f"Patient {row['patient_id']} → Risk Level: Normal. No abnormal vitals detected."
            )

    return "\n".join(results)


# AI pandas query function
def ai_dataset_query(user_message):

    global dataset

    if dataset is None:
        return None

    columns = list(dataset.columns)

    prompt = f"""
                    You are a pandas assistant.

                    Dataset columns:
                    {columns}

                    Convert the user question into a pandas expression using dataframe name 'dataset'.

                    User question:
                    {user_message}

                    Return ONLY the pandas code.
                    """

    try:
        completion = client.chat.completions.create(
            model="NousResearch/Hermes-3-Llama-3.1-8B:featherless-ai",
            messages=[{"role": "user", "content": prompt}]
        )

        code = completion.choices[0].message.content.strip()

        result = eval(code, {"dataset": dataset})

        return str(result)

    except:
        return None
    
def dataset_query(user_message):

        global dataset

        if dataset is None:
            return None

        message = user_message.lower()

        columns = list(dataset.columns)

        # count columns
        if any(q in message for q in ["count columns", "how many columns", "number of columns","count column"]):
            return f"The dataset has {len(columns)} columns."

        # show columns
        if "column" in message:
            return f"Dataset columns: {columns}"
        
        selected_column = None
        for col in columns:
            if (
                col in message
                or col.replace("_"," ") in message
                or col.replace("_","") in message
                or col.replace("_"," ") + "s" in message
                or col.replace("_","") + "s" in message
                ):
                selected_column = col
                break


        #count dataset length
        if any(q in message for q in ["dataset size","size of the data set","size of data set","number of records", "how many records", "total records"]):
            return f"The dataset contains {len(dataset)} records."
        
        # fever above average
        if "fever above average" in message:
            avg_temp = dataset["temperature"].mean()
            filtered = dataset[dataset["temperature"] > avg_temp]
            patients = filtered["patient_id"].tolist()
            return f"Patients with temperature above average ({round(avg_temp,2)}): {patients}"
        
        # patients with fever
        if "fever" in message:

            fever_patients = dataset[dataset["temperature"] > 37.5]["patient_id"].tolist()

            if fever_patients:
                return f"Patients with fever: {fever_patients}"

            return "No patients with fever detected."

        if selected_column:

            # patients greater than average
            if "greater than average" in message or "above average" in message or "more than average" in message:
                avg_value = dataset[selected_column].mean()
                filtered = dataset[dataset[selected_column] > avg_value]
                if filtered.empty:
                    return f"No patients have {selected_column.replace('_',' ')} above the average."
                patients = filtered["patient_id"].tolist()
                return f"Patients with {selected_column.replace('_',' ')} above average ({round(avg_value,2)}):\n" + "\n".join(patients)

            # patients below average
            if "below average" in message or "less than average" in message:
                avg_value = dataset[selected_column].mean()
                filtered = dataset[dataset[selected_column] < avg_value]
                if filtered.empty:
                    return f"No patients have {selected_column.replace('_',' ')} below the average."
                patients = filtered["patient_id"].tolist()
                return f"Patients with {selected_column.replace('_',' ')} below average ({round(avg_value,2)}):\n" + "\n".join(patients)

            if "average" in message or "mean" in message:

                avg_value = dataset[selected_column].mean()
                idx = (dataset[selected_column] - avg_value).abs().idxmin()
                patient = dataset.loc[idx, "patient_id"]
                value = dataset.loc[idx, selected_column]
                return f"The average {selected_column.replace('_',' ')} is {round(avg_value,2)}. Patient {patient} is closest to the average with {value}."

            if "max" in message or "highest" in message or "maximum" in message:

                idx = dataset[selected_column].idxmax()
                patient = dataset.loc[idx, "patient_id"]
                value = dataset.loc[idx, selected_column]
                return f"Patient {patient} has the highest {selected_column.replace('_',' ')}: {value}"

            if "min" in message or "lowest" in message or "minimum" in message:

                idx = dataset[selected_column].idxmin()
                patient = dataset.loc[idx, "patient_id"]
                value = dataset.loc[idx, selected_column]

                return f"Patient {patient} has the lowest {selected_column.replace('_',' ')}: {value}"

            # patients with value above a number
            if "above" in message or "greater than" in message or "more than" in message:

                numbers = [int(n) for n in re.findall(r"\b\d+\b", message)]
                if numbers:
                    threshold = numbers[0]

                    filtered = dataset[dataset[selected_column] > threshold]

                    if filtered.empty:
                        return f"No patients have {selected_column.replace('_',' ')} above {threshold}"

                    patients = filtered["patient_id"].tolist()

                    return f"Patients with {selected_column.replace('_',' ')} above {threshold}:\n" + "\n".join(patients)
            # patients with value below a number
            if "below" in message or "less than" in message:

                numbers = [int(n) for n in re.findall(r"\b\d+\b", message)]
                if numbers:
                    threshold = numbers[0]

                    filtered = dataset[dataset[selected_column] < threshold]

                    if filtered.empty:
                        return f"No patients have {selected_column.replace('_',' ')} below {threshold}"

                    patients = filtered["patient_id"].tolist()

                    return f"Patients with {selected_column.replace('_',' ')} above {threshold}:\n" + "\n".join(patients)
            # patients with exact value
            if re.search(r"\d+", message):

                numbers = [int(n) for n in re.findall(r"\b\d+\b", message)]
                if numbers:
                    value = numbers[0]

                    filtered = dataset[dataset[selected_column] == value]

                    if filtered.empty:
                        return f"No patients have {selected_column.replace('_',' ')} equal to {value}"

                    patients = filtered["patient_id"].tolist()

                    return f"Patients with {selected_column.replace('_',' ')} equal to {value}:\n" + "\n".join(patients)     
                    

            patient_ids = dataset["patient_id"].astype(str).str.strip().str.lower().tolist()

            for patient in patient_ids:
                
                if re.search(rf"\b{patient}\b", message):
                    row = dataset[dataset["patient_id"].astype(str).str.strip().str.lower() == patient]
                    if not row.empty:
                        value = row.iloc[0][selected_column]
                        return f"{selected_column.replace('_',' ')} of {patient.upper()} is {value}"

            if re.search(r"\bp\d+\b", message):
                    return "Patient not found in the dataset."
           
        return None


def generate_plot(column):

    global dataset

    if dataset is None:
        return None

    plt.figure()

    dataset[column].plot(kind="bar")

    plt.title(column.replace("_"," ").title())
    plt.xlabel("Patients")
    plt.ylabel(column.replace("_"," ").title())

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)

    graph_url = base64.b64encode(img.getvalue()).decode()

    plt.close()

    return graph_url
#returns the patient name
def get_patient_name(patient_id):

    global dataset

    if dataset is None:
        return None

    row = dataset[
    dataset["patient_id"].astype(str).str.strip().str.lower() == patient_id.strip().lower()
]
    if not row.empty and "name" in dataset.columns:
        return row.iloc[0]["name"]

    return None

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():

    global chat_history
    global dataset

    data = request.json
    user_message = data["message"]
    msg = user_message.strip().lower()

    # greeting response
    if msg in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
        return jsonify({
        "reply": f"Hello! I am {BOT_NAME}, your hospital information assistant. How can I help you today?"
    })


    # chatbot name response
    if "your name" in msg or "who are you" in msg or "what is your name" in msg:
        return jsonify({"reply": f"My name is {BOT_NAME}. I am a hospital information assistant."})

    # detect if user typed something like p1, p2, p10 etc.
    match = re.fullmatch(r"p\d+", msg)

    if match:
        name = get_patient_name(msg)

        if name:
            return jsonify({"reply": name})
        else:
            return jsonify({"reply": "Patient not found"})

    if "analyze vitals" in user_message.lower():

        if dataset is None:
            return jsonify({"reply": "Please upload a dataset before analyzing vitals."})

        match = re.search(r"\bp\d+\b", user_message.lower())

        if match:
            patient_id = match.group()
            reply = analyze_vitals(patient_id)
        else:
            reply = analyze_vitals()

        return jsonify({"reply": reply})

    chat_history.append({
        "role": "user",
        "content": user_message
    })

    
    #plotting
    if dataset is not None and ("plot" in user_message.lower() or "graph" in user_message.lower()):

        columns = list(dataset.columns)

        for col in columns:

            msg = user_message.lower()

            if (
                col in msg
                or col.replace("_"," ") in msg
                or col.replace("_","") in msg
                or col.replace("_"," ") + "s" in msg
                or col.replace("_","") + "s" in msg
            ):

                img = generate_plot(col)

                if img:
                        return jsonify({"plot": img})

    dataset_keywords = [
    "patient", "patients", "dataset", "column",
    "average", "highest", "lowest",
    "heart", "oxygen", "temperature",
    "blood", "pressure", "respiratory",
    "records", "rows", "size", "count","heartrate","heart","rate"
    ]

    if dataset is not None and any(word in user_message.lower() for word in dataset_keywords):  
        result = dataset_query(user_message)
        if result is not None:
            return jsonify({"reply": result})


    # AI based dataset queries
    if dataset is not None and any(word in user_message.lower() for word in dataset_keywords):

        ai_result = ai_dataset_query(user_message)

        if ai_result:
            return jsonify({"reply": ai_result})


    try:
        completion = client.chat.completions.create(
            model="NousResearch/Hermes-3-Llama-3.1-8B:featherless-ai",
            messages=chat_history
        )

        reply = completion.choices[0].message.content

        chat_history.append({
            "role": "assistant",
            "content": reply
        })

    except Exception as e:
        print("ERROR:", e)
        reply = "Sorry, the AI service is not responding."

    return jsonify({"reply": reply})


@app.route("/upload", methods=["POST"])
def upload():

    global dataset
    file = request.files["file"]

    if not file:
        return jsonify({"message": "No file uploaded"})

    dataset = pd.read_csv(file)

    dataset.columns = dataset.columns.str.strip().str.lower().str.replace(" ", "_")

    print("DATASET COLUMNS:", dataset.columns)

    required_columns = [
        "patient_id",
        "name",
        "heart_rate",
        "oxygen",
        "temperature",
        "blood_pressure",
        "respiratory_rate"
    ]

    missing = [col for col in required_columns if col not in dataset.columns]

    if missing:
        return jsonify({"message": f"Dataset missing columns: {missing}"})

    return jsonify({"message": "Dataset uploaded successfully"})


if __name__ == "__main__":
    app.run(debug=True)