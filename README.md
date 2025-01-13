# MarketPlace Platform

This project is a web-based e-commerce platform developed using **Flask** and **SQLAlchemy**, with integrated **Google Generative AI (Gemini)** for advanced content generation, personalized product recommendations, and review moderation.

## 🚀 Key Features

### ✅ User Management
- User registration, login, and logout system with role-based access control (admin and standard user).
- Passwords are securely hashed using **Werkzeug** for enhanced security.

### ✅ Product Management
- **Admin Features:**
   - Add, edit, and delete products.
   - Automated product descriptions and category suggestions using **LLM** based on product name and optional keywords.

### ✅ Product Recommendations
- **Personalized Recommendations:**
   - Recommendations based on the user's browsing history and purchase history.
   - Hybrid scoring system (views, purchases, and interaction time) for relevance.
- **Content-Based Filtering:**
   - Product similarity scoring using LLM-generated vector representations.

### ✅ Product Reviews
- **Secure and Controlled Reviews:**
   - Only users who purchased a product can leave reviews.
   - Automatic review generation using **LLM** based on rating and provided keywords.
- **Content Filtering:**
   - Offensive content detection and blocking using LLM before review submission.

### ✅ Category Validation
- **Automated Category Suggestion:**
   - LLM automatically suggests the most relevant category based on the product name.

---

## 📦 Technologies Used

- **Python & Flask:** Backend web framework.
- **SQLAlchemy:** ORM for interacting with the database.
- **SQLite:** Lightweight database for storing products, users, and interactions.
- **Google Generative AI (Gemini):** LLM for dynamic content generation, recommendations, and moderation.
- **Bootstrap:** Frontend styling and responsiveness.
- **dotenv:** Environment variable management.

---

## 📖 Project Structure

```plaintext
.
├── app.py                 # Main Flask application file
├── models.py              # Database models and schema
├── templates/             # HTML templates for the web pages
├── static/                # CSS, JS, and images
├── database.db            # SQLite database
├── requirements.txt       # Required dependencies
└── README.md              # Project documentation
```

---

## 🛠️ Setup Instructions

Follow these steps to set up and run the project locally:

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```
2. **Install the required packages:**
   ```bash
   pip install flask sqlalchemy google-genai python-dotenv
   ```
   If the project fails to run due to missing dependencies, install all requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up the database:**
   The database (`database.db`) will be automatically created when the project runs for the first time.

4. **Run the application:**
   ```bash
   python app.py
   ```
5. **Access the web app:**
   Open a browser and go to `http://127.0.0.1:5000`.

---

## 🧠 How LLM is Integrated in the Project

### **Dynamic Content Generation**
- Automatic generation of high-quality product descriptions based on product names and optional keywords.
- Automatic category suggestions based on product titles using a language model prompt.

### **Personalized Recommendations**
- Recommendations based on user interaction history (views and purchases).
- Content-based filtering using vector-based similarity analysis between product descriptions.

### **Review Management & Content Filtering**
- Offensive review detection using an LLM-powered content filter.
- Automatic generation of reviews based on keywords and star ratings.

---

## ✅ Advantages of Using LLM in E-Commerce

- **Enhanced Automation:** Reduces the need for manual content creation for product descriptions and reviews.
- **Personalization:** Delivers personalized recommendations based on user behavior and interaction history.
- **Scalability:** Automated content generation enables faster product onboarding and listing.
- **Improved User Experience:** Users receive detailed descriptions, and the review process is moderated for quality and appropriateness.

---

## ⚠️ Potential Drawbacks

- **Accuracy Limitations:** LLMs can generate inaccurate content or descriptions that may not perfectly match the product.
- **Dependency on External APIs:** Reliance on **Google Generative AI (Gemini)** can lead to availability issues or quota limits (e.g., error 429 when quota is exhausted).
- **Cost:** API usage can become costly for large-scale e-commerce platforms.
- **Ethical Concerns:** Automated moderation can sometimes lead to false positives or content being unnecessarily blocked.

---

## 📈 Future Improvements

- **Enhanced Recommendations:** Implement hybrid collaborative filtering combined with LLM.
- **Multilingual Support:** Extend content generation to multiple languages.
- **Performance Optimization:** Improve database queries and cache results for faster recommendation retrieval.
- **LLM Fine-Tuning:** Use a domain-specific fine-tuned model for improved accuracy in e-commerce descriptions.

---




