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
    """Generare descriere personalizata in functie de comportamentul utilizatorului"""
    interactions = UserInteraction.query.filter_by(user_id=user_id).all()
    purchased_products = PurchaseHistory.query.filter_by(user_id=user_id).all()
    
    viewed_categories = [Product.query.get(i.product_id).category for i in interactions]
    purchased_categories = [Product.query.get(i.product_id).category for i in purchased_products]

    try:
        chat_session = model.start_chat(history=[])
        prompt = (
            f"Generate a personalized product description for '{product_name}' in the '{category}' category."
            f" The user frequently views: {', '.join(viewed_categories)}."
            f" The user has purchased products from: {', '.join(purchased_categories)}."
        )
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
        .order_by((Product.purchases * 0.7) + (Product.views * 0.3))
        .limit(5)
        .all()
    )

    if len(produse_recomandate) < 5:
        produse_populare = Product.query.order_by(Product.purchases.desc(), Product.views.desc()).limit(5).all()
        produse_recomandate.extend(produse_populare)
        produse_recomandate = list(set(produse_recomandate))

    return produse_recomandate


def get_content_based_recommendations(product):
    all_products = Product.query.filter(Product.id != product.id).all()
    
    try:
        chat_session = model.start_chat(history=[])
        prompt = f"Convert the following product description into a numeric vector for similarity comparison: '{product.description}'"
        response = chat_session.send_message(prompt)
        
        try:
            current_vector = [float(x) for x in response.text.strip().split(",")]
        except ValueError:
            print("Invalid vector response, using name and category fallback:", response.text)
            # Dacă vectorul nu poate fi creat, fallback pe nume și categorie
            return Product.query.filter(
                Product.category == product.category, Product.id != product.id
            ).order_by(Product.views.desc()).limit(5).all()
        
        similar_products = []
        for prod in all_products:
            prompt = f"Convert the following product description into a vector representation: '{prod.description}'"
            response = chat_session.send_message(prompt)
            
            try:
                product_vector = [float(x) for x in response.text.strip().split(",")]
                similarity_score = sum(a * b for a, b in zip(current_vector, product_vector))
                
                # ✅ Calculăm și similaritatea pe baza numelui (similaritatea cosinus)
                name_similarity = 1.0 if product.name.lower() in prod.name.lower() else 0.5
                
                # ✅ Formula hibridă: 70% descriere, 30% nume similar
                final_score = (similarity_score * 0.7) + (name_similarity * 0.3)
                
                similar_products.append((prod, final_score))
            except ValueError:
                print(f"Eroare la conversia vectorului pentru produsul: {prod.name}")
                continue  

        # ✅ Sortare după scorul combinat
        if similar_products:
            similar_products = sorted(similar_products, key=lambda x: x[1], reverse=True)[:5]
            return [prod[0] for prod in similar_products]
        else:
            # Fallback: bazat doar pe categorie
            return Product.query.filter(
                Product.category == product.category, Product.id != product.id
            ).limit(5).all()
    
    except Exception as e:
        print(f"Eroare în generarea recomandărilor bazate pe conținut: {str(e)}")
        return Product.query.filter(
            Product.category == product.category, Product.id != product.id
        ).limit(5).all()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Trebuie să fii autentificat pentru a accesa această pagină.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/popular_products")
@login_required
def popular_products():
    # Cele mai vizualizate produse
    most_viewed = Product.query.order_by(Product.views.desc()).limit(5).all()
    
    # Cele mai achizitionate produse
    most_purchased = Product.query.order_by(Product.purchases.desc()).limit(5).all()
    
    # Produse cu cele mai multe interactiuni
    most_interacted = (
        db.session.query(Product, db.func.sum(Product.views + Product.purchases).label("total_interactions"))
        .order_by(db.func.sum(Product.views + Product.purchases).desc())
        .limit(5)
        .all()
    )
    
    return render_template(
        "popular_products.html",
        most_viewed=most_viewed,
        most_purchased=most_purchased,
        most_interacted=most_interacted
    )

@app.route("/")
@login_required
def home():
    produse = Product.query.all()
    produse_recomandate = get_recommended_products(session.get('user_id'))
    return render_template("index.html", produse=produse, produse_recomandate=produse_recomandate, user_role=session.get('role'))


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
    product = Product.query.get_or_404(product_id)
    product.views += 1
    db.session.commit()

    personalized_description = generate_personalized_description(product.name, product.category, session["user_id"])
    similar_products = get_content_based_recommendations(product)

    new_interaction = UserInteraction(user_id=session["user_id"], product_id=product_id)
    db.session.add(new_interaction)
    db.session.commit()

    return render_template("view_product.html", product=product, personalized_description=personalized_description, similar_products=similar_products)

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
