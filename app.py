from flask import Flask, render_template, request, redirect, url_for, jsonify, session,flash
from models import db, Product, UserInteraction, User, PurchaseHistory
import os
import google.generativeai as genai
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timezone, datetime, timedelta




client = genai.configure(api_key="AIzaSyAvJ_7_p9-VHaE86_k4T8OZYV8KXQNLHRg")
load_dotenv()

#AIzaSyAvJ_7_p9-VHaE86_k4T8OZYV8KXQNLHRg
app = Flask(__name__)
app.secret_key = 'supersecretkey'  
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# Creare baza de date
with app.app_context():
    db.create_all()


AVAILABLE_CATEGORIES = [
    "Electrocasnice", "Mobilă", "Electronice", "Îmbrăcăminte", "Cărți", "Jucării", "Cosmetice"
]

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 50,
    "max_output_tokens": 500,
    "response_mime_type": "text/plain"
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)


def generate_personalized_description(product_name, category, user_id):
    interactions = UserInteraction.query.filter_by(user_id=user_id).all()
    viewed_categories = [Product.query.get(i.product_id).category for i in interactions]

    try:
        chat_session = model.start_chat(history=[])
        prompt = f"Generate a personalized product description for '{product_name}' in the '{category}' category."

        if viewed_categories:
            prompt += f" The user has interacted with these categories before: {', '.join(viewed_categories)}."

        response = chat_session.send_message(prompt)
        return response.text.strip()
    except Exception as e:
        return "Descriere indisponibilă."

def get_recommended_products(user_id):
    viewed = UserInteraction.query.filter_by(user_id=user_id).order_by(UserInteraction.id.desc()).limit(10).all()
    purchased = PurchaseHistory.query.filter_by(user_id=user_id).limit(5).all()
    
    viewed_categories = [Product.query.get(i.product_id).category for i in viewed]
    purchased_categories = [Product.query.get(i.product_id).category for i in purchased]

    all_categories = list(set(viewed_categories + purchased_categories))

    produse_recomandate = (
        Product.query.filter(Product.category.in_(all_categories))
        .order_by(Product.views.desc(), Product.purchases.desc())
        .limit(5)
        .all()
    )
    return produse_recomandate

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Trebuie să fii autentificat pentru a accesa această pagină.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def home():
    produse = Product.query.all()
    produse_recomandate = get_recommended_products(session.get('user_id'))
    
    return render_template("index.html", 
                           produse=produse, 
                           produse_recomandate=produse_recomandate, 
                           user_role=session.get('role'))



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)
        if User.query.filter_by(username=username).first():
            flash("Acest utilizator există deja!")
            return redirect(url_for("register"))

        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Înregistrare reușită! Autentifică-te pentru a continua.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            flash("Autentificare reușită!")
            return redirect(url_for("home"))
        flash("Date de autentificare incorecte!")
    return render_template("login.html")

# ✅ Logout utilizator
@app.route("/logout")
def logout():
    session.clear()
    flash("Deconectare reușită!")
    return redirect(url_for("login"))

@app.route("/suggest_category", methods=["POST"])
def suggest_category():
    name = request.form.get('name')
    if not name:
        return jsonify({"error": "Numele produsului este necesar!"})

    try:
        chat_session = model.start_chat(history=[])
        prompt = f"Suggest the most relevant product category for the product: '{name}'. Choose from these categories: {', '.join(AVAILABLE_CATEGORIES)}"
        response = chat_session.send_message(prompt)
        suggested_category = response.text.strip()
        return jsonify({"suggested_category": suggested_category})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/add", methods=["GET", "POST"])
def add_product():
    if "role" not in session or session["role"] != "admin":
        flash("Doar administratorii pot adăuga produse!")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form['description']

        new_product = Product(name=name, category=category, price=price, description=description)
        db.session.add(new_product)
        db.session.commit()
        flash("Produs adăugat cu succes!")
        return redirect(url_for('home'))

    return render_template("add_product.html", categories=AVAILABLE_CATEGORIES)


@app.route("/generate_description", methods=["POST"])
def generate_description():
    name = request.form.get('name')
    category = request.form.get('category')

    if not name or not category:
        return jsonify({"error": "Numele și categoria sunt necesare!"})

    try:
        chat_session = model.start_chat(history=[])
        prompt = f"Generate a professional and creative product description for the product '{name}' in the '{category}' category. Highlight its unique features and benefits."

        response = chat_session.send_message(prompt)
        description = response.text.strip()
        return jsonify({"description": description})
        
    except Exception as e:
        return jsonify({"error": str(e)})



@app.route("/view_product/<int:product_id>")
def view_product(product_id):
    product = Product.query.get(product_id)
    product.views += 1
    db.session.commit()

    personalized_description = generate_personalized_description(product.name, product.category, session["user_id"])

    new_interaction = UserInteraction(user_id=session["user_id"], product_id=product_id)
    db.session.add(new_interaction)
    db.session.commit()
    
    return render_template("view_product.html", product=product, personalized_description=personalized_description)

@app.route("/purchase/<int:product_id>")
def purchase_product(product_id):
    product = Product.query.get(product_id)
    product.purchases += 1
    db.session.commit()

    new_purchase = PurchaseHistory(user_id=session["user_id"], product_id=product_id)
    db.session.add(new_purchase)
    db.session.commit()

    flash("Produs achiziționat!")
    return redirect(url_for("home"))

    
    
    
  

if __name__ == "__main__":
    app.run(debug=True)
