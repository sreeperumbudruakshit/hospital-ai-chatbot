# 🏥 Hospital AI Chatbot
Live Demo:
https://hospital-ai-chatbot.onrender.com

An AI-powered hospital assistant that allows healthcare staff to interact with patient data using natural language queries. The system analyzes patient vitals, retrieves information from datasets, and generates visual insights.

## 🚀 Features

* Upload and analyze patient datasets
* Query patient vitals using natural language
* AI-powered responses using LLM integration
* Data visualization for vitals such as heart rate, oxygen level, and temperature
* Clean web interface built using Flask

## 🧠 Tech Stack

Backend:

* Python
* Flask
* Pandas
* HuggingFace API

Frontend:

* HTML
* CSS
* JavaScript

Libraries:

* Matplotlib
* python-dotenv
* NumPy

## 📂 Project Structure

```
hospital-chatbot-project
│
├── static
│   ├── script.js
│   └── style.css
│
├── templates
│   └── index.html
│
├── app.py
├── test_ai.py
├── .env
├── .gitignore
├── README.md

⚙️ Installation

Clone the repository

```
git clone https://github.com/yourusername/hospital-ai-chatbot.git
cd hospital-ai-chatbot
```

Create virtual environment

```
python -m venv venv
```

Activate virtual environment

Windows

```
venv\Scripts\activate
```

Mac/Linux

```
source venv/bin/activate
```

Install dependencies

```
pip install flask pandas matplotlib numpy python-dotenv huggingface_hub
```

🔑 Environment Variables

Create a `.env` file in the project root and add your API key.

```
HF_TOKEN=your_api_key_here
```

This key is used to access the HuggingFace inference API.

⚠️ Do NOT upload your `.env` file to GitHub.

▶️ Running the Application

Start the Flask server:

```
python app.py
```

Open your browser and go to:

```
http://127.0.0.1:5000
```

📊 Example Queries

* Show patients with high heart rate
* Visualize oxygen levels
* List patients with abnormal temperature
* Show respiratory rate distribution

## 📸 Screenshots

(Add screenshots of your chatbot interface here)

🎯 Future Improvements

* Real-time hospital monitoring dashboard
* Voice-based queries
* Advanced AI diagnosis suggestions
* Multi-user authentication

👨‍💻 Author

Akshit S

LinkedIn: (add your LinkedIn link)
GitHub: (add your GitHub link)

---
