<img width="863" height="725" alt="image" src="https://github.com/user-attachments/assets/291241e2-4bc2-4c32-852e-bb7e55e9ecd0" /><br>

This is the rough workflow of my project

## 🚀 Getting Started

Follow the steps below to set up and run the project locally.

---

### 1️⃣ Clone the Repository

```bash
git clone <your-github-repo-url>
cd <repo-folder>
```

---

### 2️⃣ Install Core Dependencies

Make sure you are using **Python 3.9+**, then install the required libraries:

```bash
pip install langgraph langchain python-dotenv
```

---

### 3️⃣ Choose an LLM Provider

This project is **LLM-agnostic**. You can use either **open-source models** or **cloud-based models**.

---

#### 🔹 Option A: Hugging Face (Recommended – Free & Open Source)

If you prefer open-source models from Hugging Face:

```bash
pip install langchain_huggingface
```

Configure your Hugging Face token in a `.env` file:

```
HUGGINGFACEHUB_API_TOKEN=your_token_here
```

---

#### 🔹 Option B: Google Gemini

If you want to use Google Gemini:

```bash
pip install langchain_google_genai
```

Add your API key to `.env`:

```
GOOGLE_API_KEY=your_api_key_here
```

---

### 4️⃣ Run the Project

Once dependencies are installed and environment variables are set, you are ready to run the project.

---

### 5️⃣ Run with UI (Streamlit)

To launch the frontend interface:

```bash
streamlit run <frontend_ui_file.py>
```

Example:

```bash
streamlit run app.py
```

---

## ✅ Notes

* The backend logic is powered by **LangGraph** for structured AI workflows.
* The project supports **multiple LLM providers** without changing core logic.
* UI is built using **Streamlit** for quick interaction and demos.

---




