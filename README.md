# Flask Product Recommendation and Review Platform

This is a web-based e-commerce platform built using Flask and SQLAlchemy, with integrated language model (LLM) capabilities for enhanced user experience, product recommendations, and automated content generation.

## Key Features

- **User Management:**
  - User registration, login, and logout system with role-based access control (admin and user).
- **Product Management:**
  - Admin can add, edit, and delete products.
  - Product descriptions and categories can be auto-generated using LLM based on product name and optional keywords.
- **Product Recommendations:**
  - Personalized recommendations based on user's interactions and purchase history.
  - Content-based filtering using LLM for suggesting similar products.
- **Product Reviews:**
  - Users can leave reviews only after purchasing a product.
  - Reviews can be automatically generated using LLM based on rating and keywords.
  - Offensive content filtering using LLM before submitting reviews.
- **Category Validation:**
  - Automatic category suggestion and validation using LLM based on product name.

## Technologies Used

- **Flask:** Web framework for Python.
- **SQLAlchemy:** ORM for database interactions.
- **SQLite:** Database for storing products, users, and interactions.
- **Google Generative AI (Gemini):** LLM for content generation, recommendations, and validation.
- **Bootstrap:** Frontend styling.

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd flask-llm-ecommerce
   ```
2. Install the required packages:
   ```bash
   pip install flask sqlalchemy google-genai
   ```
3. Set up the database:
   ```bash
   python -c "from app import db; db.create_all()"
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Access the app in your browser at `127.0.0.1:5000`.

## How It Works

1. **Admin Features:**
   - Add a new product with automatic category and description suggestions using LLM.
2. **User Interaction:**
   - Users can browse products and receive personalized recommendations.
   - Users can leave reviews with real-time content moderation using LLM.
3. **Product Recommendations:**
   - Content-based recommendations based on product descriptions and user interaction history.

## LLM Integration Use Cases

- **Dynamic Content Generation:** LLM generates product descriptions and categories automatically.
- **Personalization:** LLM recommends products based on user interaction.
- **Automated Moderation:** Offensive language detection for product reviews.

## Advantages of Using LLM in E-Commerce

- **Efficiency:** Automated content generation reduces manual workload.
- **Personalization:** Personalized recommendations increase user engagement and sales.
- **Moderation:** Automated content moderation ensures a safe and respectful platform.

## Potential Drawbacks

- **Accuracy:** LLM-generated content may sometimes lack context or accuracy.
- **Dependence on External APIs:** Relying on external LLM services can lead to availability issues.
- **Ethical Concerns:** Automated moderation can lead to false positives or censorship issues.

## Future Improvements

- Improve the recommendation algorithms with hybrid approaches (LLM + collaborative filtering).
- Implement multilingual support.
- Optimize the moderation filter for better accuracy.

## License
This project is licensed under the MIT License.

