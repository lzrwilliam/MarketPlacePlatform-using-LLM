from flask import Flask, render_template, request, redirect, url_for, jsonify, session,flash
from models import db, Product, UserInteraction, User, PurchaseHistory, Review
import os
import google.generativeai as genai
from flask_caching import Cache
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
from datetime import datetime, timezone
def generate_personalized_description(product_name, category, user_id, product_id):
    """Verifică dacă există o descriere salvată și o folosește. Dacă nu, generează și o salvează."""
    
    interaction = UserInteraction.query.filter_by(user_id=user_id, product_id=product_id).first()

    if interaction and interaction.personalized_description:
        last_updated_aware = interaction.last_updated.replace(tzinfo=timezone.utc) if interaction.last_updated else None
        if last_updated_aware and (datetime.now(timezone.utc) - last_updated_aware).days < 2:
            return interaction.personalized_description

    if not interaction:
        interaction = UserInteraction(user_id=user_id, product_id=product_id)
        db.session.add(interaction)
        db.session.commit()

    # Generăm o descriere nouă cu LLM
    interactions = UserInteraction.query.filter_by(user_id=user_id).all()
    purchased_products = PurchaseHistory.query.filter_by(user_id=user_id).all()

    viewed_categories = [db.session.get(Product, i.product_id).category for i in interactions if i.product_id]
    purchased_categories = [db.session.get(Product, i.product_id).category for i in purchased_products if i.product_id]

    try:
        chat_session = model.start_chat(history=[])
        prompt = (
            f"Generate a single, high-quality product description for '{product_name}' in '{category}'. "
            f"Highlight key benefits. "
            f"The user frequently views: {', '.join(viewed_categories)}. "
            f"The user has purchased from: {', '.join(purchased_categories)}. "
            f"The output must be in Romanian."
        )
        response = chat_session.send_message(prompt)
        final_description = response.text.strip()

        # Dacă răspunsul LLM este gol sau invalid, nu actualizăm baza de date
        if not final_description:
            return "Descriere indisponibilă."

        interaction.personalized_description = final_description
        interaction.last_updated = datetime.now(timezone.utc)
        db.session.commit()

        return final_description

    except Exception as e:
        print(f"Eroare la generarea descrierii: {str(e)}")
        return "Descriere indisponibilă."

def get_recommended_products(user_id):
    viewed = UserInteraction.query.filter_by(user_id=user_id).order_by(UserInteraction.id.desc()).limit(10).all()
    purchased = PurchaseHistory.query.filter_by(user_id=user_id).limit(5).all()

    if not viewed and not purchased:
        return Product.query.order_by(Product.purchases.desc(), Product.views.desc()).limit(5).all()
    
   
    viewed_categories = [db.session.get(Product, i.product_id).category for i in viewed]
    purchased_categories = [db.session.get(Product, i.product_id).category for i in purchased]

    all_categories = list(set(viewed_categories + purchased_categories))

    produse_recomandate = []
    for product in Product.query.filter(Product.category.in_(all_categories)).all():
        interactions = UserInteraction.query.filter_by(user_id=user_id, product_id=product.id).all()
        total_views = len(interactions)
        total_time_spent = sum(i.time_spent for i in interactions)

       
        score = (product.purchases * 0.4) + (total_views * 0.3) + (total_time_spent * 0.3)
        produse_recomandate.append((product, score))

    # sortare dupa scor
    produse_recomandate.sort(key=lambda x: x[1], reverse=True)
    produse_recomandate = [p[0] for p in produse_recomandate[:5]]

    #  daca nu avem suficient, completam cu produse populare
    if len(produse_recomandate) < 5:
        produse_populare = Product.query.order_by(Product.purchases.desc(), Product.views.desc()).limit(5).all()
        produse_recomandate.extend(produse_populare)
        produse_recomandate = list(set(produse_recomandate))  # Evita duplicarea produselor

    return produse_recomandate
    

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def get_content_based_recommendations(product):
    """Evită apelurile API inutile folosind caching și verificări suplimentare."""
    
    cache_key = f"recommendations_{product.id}"
    cached_recommendations = cache.get(cache_key)
    
    if cached_recommendations:
        print("✅ DEBUG: Folosim recomandările din cache")
        return cached_recommendations

    all_products = Product.query.filter(Product.id != product.id).all()
    
    # ⚠️ Evităm apelul LLM dacă descrierea produsului este goală
    if not product.description or product.description.strip() == "":
        return Product.query.filter(Product.category == product.category, Product.id != product.id).limit(5).all()
    
    try:
        chat_session = model.start_chat(history=[])
        prompt = (
            f"Generate a numeric vector representation for '{product.description}'. "
            f"Respond only with a list of numbers separated by commas."
        )
        response = chat_session.send_message(prompt)
        
        response_text = response.text.strip()
        if all(char.isdigit() or char in ",. " for char in response_text):
            current_vector = [float(x) for x in response_text.split(",")]
        else:
            raise ValueError("Invalid numeric vector format received.")

        similar_products = []
        for prod in all_products:
            prompt = (
                f"Generate a numeric vector representation for '{prod.description}'. "
                f"Respond only with a list of numbers separated by commas."
            )
            response = chat_session.send_message(prompt)
            response_text = response.text.strip()

            try:
                product_vector = [float(x) for x in response_text.split(",")]
                similarity_score = sum(a * b for a, b in zip(current_vector, product_vector))
                
                name_similarity = 1.0 if product.name.lower() in prod.name.lower() else 0.5
                
                final_score = (similarity_score * 0.7) + (name_similarity * 0.3)
                similar_products.append((prod, final_score))
            except ValueError:
                print(f"Error parsing vector for product: {prod.name}")
                continue  

        if similar_products:
            similar_products = sorted(similar_products, key=lambda x: x[1], reverse=True)[:5]
            recommended_products = [prod[0] for prod in similar_products]
            
            cache.set(cache_key, recommended_products, timeout=3600)
            return recommended_products

        return Product.query.filter(
            Product.category == product.category, Product.id != product.id
        ).limit(5).all()

    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return Product.query.filter(
            Product.category == product.category, Product.id != product.id
        ).limit(5).all()




def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Trebuie sa fii autentificat pentru a accesa aceasta pagina.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/popular_products")
@login_required
def popular_products():
    # Cele mai vizualizate produse global
    most_viewed = Product.query.order_by(Product.views.desc()).limit(5).all()
    
    # Cele mai achizitionate produse global
    most_purchased = Product.query.order_by(Product.purchases.desc()).limit(5).all()
    
    # Produse cu cele mai multe interactiuni (vizualizari + achizitii)
    most_interacted = (
        db.session.query(Product, db.func.sum(Product.views + Product.purchases).label("total_interactions"))
        .group_by(Product.id)
        .order_by(db.func.sum(Product.views + Product.purchases).desc())
        .limit(5)
        .all()
    )
    
    # Cele mai populare produse per categorie
    popular_per_category = {}
    for category in AVAILABLE_CATEGORIES:
        popular_per_category[category] = (
            Product.query.filter_by(category=category)
            .order_by(Product.purchases.desc(), Product.views.desc())
            .limit(5)
            .all()
        )
    
    return render_template(
        "popular_products.html",
        most_viewed=most_viewed,
        most_purchased=most_purchased,
        most_interacted=most_interacted,
        popular_per_category=popular_per_category
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
        prompt = (f"Suggest the most relevant product category for the product: '{name}'. Choose from these categories: {', '.join(AVAILABLE_CATEGORIES)}"
                f"The output must be in romanian.")
   
        response = chat_session.send_message(prompt)
        suggested_category = response.text.strip()
        return jsonify({"suggested_category": suggested_category})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/generate_description", methods=["POST"])
def generate_description():
    name = request.form.get('name')
    category = request.form.get('category')
    keywords = request.form.get('keywords')

    if not name or not category:
        return jsonify({"error": "Numele si categoria sunt necesare!"})

    try:
        chat_session = model.start_chat(history=[])
        prompt = (f"Generate a professional and creative product description for the product '{name}' in the '{category}' category. Highlight its unique features and benefits."
                 f"Be careful when generating the description, at cases such as name suggests a different category than the one provided. if so, please adjust the description accordingly, not to be an absurd one."
                 f"Use the keywords '{keywords}' to enhance the description."
                 f"Do not generate a too long description, keep it concise and informative, but not too short either.s"
                f"The output must be in romanian."
)
        response = chat_session.send_message(prompt)
        description = response.text.strip()
        return jsonify({"description": description})
        
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/add", methods=["GET", "POST"])
def add_product():
    if "role" not in session or session["role"] != "admin":
        flash("Doar administratorii pot adauga produse!")
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





@app.route("/view_product/<int:product_id>")
def view_product(product_id):
    product = db.session.get(Product, product_id)
    #Product.query.get_or_404(product_id)
    product.views += 1
    db.session.commit()
  

    start_time = datetime.now(timezone.utc)  
    session['start_time'] = start_time.timestamp()  
    
    has_purchased = PurchaseHistory.query.filter_by(user_id=session["user_id"], product_id=product_id).first() is not None

    already_reviewed = Review.query.filter_by(user_id=session["user_id"], product_id=product_id).first() is not None

    personalized_description = generate_personalized_description(product.name, product.category, session["user_id"], product_id)

    existing_interaction = UserInteraction.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
    if not existing_interaction:
        new_interaction = UserInteraction(user_id=session["user_id"], product_id=product_id)
        db.session.add(new_interaction)
        db.session.commit()

    similar_products = get_content_based_recommendations(product)
    
     # Verificăm dacă FAQ-urile sunt în cache
    faqs = cache.get(f"faqs_{product.id}")

    if not faqs:
        faqs = []
        try:
            chat_session = model.start_chat(history=[])
            prompt = (
                f"Generează între 3 și 5 întrebări frecvente pentru produsul '{product.name}' din categoria '{product.category}'. "
                f"Descrierea produsului este: '{product.description}'. "
                f"Întrebările ar trebui să fie despre utilizare, caracteristici și avantaje. "
                f"Formatul răspunsului trebuie să fie o listă JSON cu câmpurile 'question' și 'answer'. "
                f"Scrie în limba română."
            )
            response = chat_session.send_message(prompt)
            
            # Încercăm să convertim răspunsul în JSON
            try:
                faqs = json.loads(response.text.strip())
                if isinstance(faqs, list) and all(isinstance(faq, dict) and "question" in faq and "answer" in faq for faq in faqs):
                    cache.set(f"faqs_{product.id}", faqs, timeout=3600)
                else:
                    faqs = [{"question": "Nu există întrebări disponibile", "answer": "Nu am reușit să generăm întrebări."}]
            except json.JSONDecodeError:
                faqs = [{"question": "Nu există întrebări disponibile", "answer": "Nu am reușit să generăm întrebări."}]
        except Exception as e:
            print(f"Eroare la generarea FAQ: {str(e)}")
            faqs = [{"question": "Nu există întrebări disponibile", "answer": "Nu am reușit să generăm întrebări."}]

    return render_template("view_product.html", product=product, personalized_description=personalized_description, similar_products=similar_products, has_purchased=has_purchased, already_reviewed=already_reviewed, faqs=faqs)


@app.route("/purchase/<int:product_id>")
def purchase_product(product_id):
    product = db.session.get(Product, product_id)
    product.purchases += 1
    db.session.commit()

    new_purchase = PurchaseHistory(user_id=session["user_id"], product_id=product_id)
    db.session.add(new_purchase)
    db.session.commit()

    flash("Produs achiziționat!")
    return redirect(url_for("home"))



@app.route("/track_time/<int:product_id>", methods=["POST"])
def track_time(product_id):
    try:
        data = request.get_json() 
        time_spent = float(data.get('time_spent'))

     
        existing_interaction = UserInteraction.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
        if existing_interaction:
            existing_interaction.time_spent += time_spent  
        else:
            interaction = UserInteraction(user_id=session["user_id"], product_id=product_id, time_spent=time_spent)
            db.session.add(interaction)

        db.session.commit()
        return jsonify({"status": "success", "time_spent": time_spent})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/user_reports")
@login_required
def user_reports():
    if "role" not in session or session["role"] != "admin":
        flash("Doar administratorii pot accesa aceasta pagina!")
        return redirect(url_for("home"))
    
    users = User.query.all()
    user_reports = {}
    for user in users:
        interactions = UserInteraction.query.filter_by(user_id=user.id).all()
        purchased_products = PurchaseHistory.query.filter_by(user_id=user.id).all()
        
        user_reports[user.username] = {
            "interactions": interactions,
            "purchased_products": purchased_products
        }
    return render_template("user_reports.html", user_reports=user_reports)
    
@app.route('/add_review/<int:product_id>', methods=["POST"])
@login_required
def add_review(product_id):
    """Adaugă un review scris de utilizator sau generat de LLM"""
    rating = int(request.form.get('rating'))
    content = request.form.get('content')
    
    
    try:
        chat_session = model.start_chat(history=[])
        prompt = (f"Check if the following review is offensive or inappropriate in Romanian language:\n"
                  f"Review: {content}\n"
                  "Respond only with 'YES' if offensive or 'NO' if appropriate.")
        response = chat_session.send_message(prompt)
        if "YES" in response.text.upper():
            flash("Recenzia conține conținut ofensator și nu a fost acceptată!")
            return redirect(url_for('view_product', product_id=product_id))
    except Exception as e:
        flash("Eroare la verificarea conținutului!")
        print(str(e))
        return redirect(url_for('view_product', product_id=product_id))
    
    
    existing_review = Review.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
    
    if existing_review:
        flash("Ai deja un review pentru acest produs!")
        return redirect(url_for('view_product', product_id=product_id))
    
    new_review = Review(
        user_id=session["user_id"],
        product_id=product_id,
        rating=rating,
        content=content
    )
    db.session.add(new_review)
    db.session.commit()
    flash("Review adăugat cu succes!")
    return redirect(url_for('view_product', product_id=product_id))


@app.route('/generate_review/<int:product_id>', methods=["POST"])
@login_required
def generate_review(product_id):
    """Generează un review folosind LLM"""
    data = request.get_json()
    rating = data.get("rating")
    keywords = data.get("keywords", "").split(',')

    product = db.session.get(Product, product_id)
    try:
        chat_session = model.start_chat(history=[])
        prompt = (
            f"Generate a high-quality review for '{product.name}' with a rating of {rating} stars. "
            f"Include these aspects: {', '.join(keywords)}"
            f"The output must be in romanian."
        )
        response = chat_session.send_message(prompt)
        generated_review = response.text.strip()
        return jsonify({"generated_review": generated_review})
    except Exception as e:
        return jsonify({"error": str(e)})

from sqlalchemy import or_


@app.route("/search_products", methods=["POST"])
def search_products():
    query = request.form.get("query", "").strip()

    if not query:
        flash("Introduceți un termen de căutare!", "danger")
        return redirect(url_for("home"))

    try:
        # 🔍 1. Căutare directă în baza de date
        products = Product.query.filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.category.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        ).all()

        # daca gasim rezultate le afisam
        if products:
            return render_template("search_results.html", produse=products, query=query)

        # daca nu avem rezultate apelam llm pt sugestii
        all_products = Product.query.all()
        product_list = ", ".join([p.name for p in all_products])  # Listam toate produsele

        chat_session = model.start_chat(history=[])
        prompt = (
            f"Avem următoarele produse disponibile: {product_list}. "
            f"Utilizatorul caută: '{query}'. "
            f"Încearcă să identifici cele mai relevante produse din această listă care se potrivesc cererii utilizatorului, proceseaza bine ce a cerut utilizatorul. "
            f"Returnează doar numele produselor separate prin virgulă, fără alt text."
        )
        response = chat_session.send_message(prompt)

        # 🔍 Extragem lista de produse returnată de LLM
        suggested_products = response.text.strip().split(",") if response.text else []
        suggested_products = [p.strip() for p in suggested_products if p.strip()]

        # 🔍 Verificăm dacă produsele LLM există în baza de date
        if suggested_products:
            products = Product.query.filter(Product.name.in_(suggested_products)).all()

        
        return render_template("search_results.html", produse=products, query=query)

    except Exception as e:
        flash("Eroare la căutare!", "danger")
        print(f"Eroare căutare: {str(e)}")
        return redirect(url_for("home"))



if __name__ == "__main__":
    app.run(debug=True)
