from app import app, db
from models import Product

products = [
    # Electrocasnice
    {"name": "Frigider Smart", "category": "Electrocasnice", "price": 3200, "description": "Frigider inteligent cu afișaj digital și control WiFi."},
    {"name": "Mașină de spălat Ultra", "category": "Electrocasnice", "price": 2800, "description": "Mașină de spălat cu funcție de uscare și control prin aplicație."},
    {"name": "Cuptor cu Microunde Deluxe", "category": "Electrocasnice", "price": 700, "description": "Cuptor cu microunde cu multiple funcții de gătit rapide."},

    # Electronice
    {"name": "Smartphone Galaxy S23", "category": "Electronice", "price": 4200, "description": "Telefon de ultimă generație cu cameră de 108MP și 5G."},
    {"name": "Laptop Ultra Pro", "category": "Electronice", "price": 6800, "description": "Laptop profesional pentru dezvoltatori și creatori de conținut."},
    {"name": "Căști Bluetooth ProSound", "category": "Electronice", "price": 500, "description": "Căști wireless cu anulare activă a zgomotului."},

    # Mobilă
    {"name": "Canapea Extensibilă Lux", "category": "Mobilă", "price": 3500, "description": "Canapea extensibilă pentru 3 persoane, cu design modern."},
    {"name": "Masa Dining Elegance", "category": "Mobilă", "price": 2100, "description": "Masă din lemn masiv, potrivită pentru 6 persoane."},
    {"name": "Dulap Spațios HomeStyle", "category": "Mobilă", "price": 2700, "description": "Dulap spațios cu uși glisante și oglindă."},

    # Cărți
    {"name": "Romanul Marele Gatsby", "category": "Cărți", "price": 50, "description": "Un roman clasic despre epoca jazzului și visul american."},
    {"name": "Codul lui Da Vinci", "category": "Cărți", "price": 70, "description": "Thriller plin de mister și descoperiri istorice."},
    {"name": "Povestiri Sci-Fi", "category": "Cărți", "price": 45, "description": "Colecție de povestiri științifico-fantastice despre viitor."},

    # Jucării
    {"name": "Set LEGO City", "category": "Jucării", "price": 300, "description": "Set creativ LEGO pentru copii peste 6 ani."},
    {"name": "Puzzle 1000 Piese", "category": "Jucării", "price": 150, "description": "Puzzle de 1000 piese cu tematică peisaj natural."},
    {"name": "Mașinuță Teleghidată Turbo", "category": "Jucării", "price": 200, "description": "Mașinuță controlată prin telecomandă, cu viteză mare."},

    # Cosmetice
    {"name": "Parfum Elegant Noir", "category": "Cosmetice", "price": 400, "description": "Parfum de lux cu arome de vanilie și lemn de santal."},
    {"name": "Crema Anti-Îmbătrânire", "category": "Cosmetice", "price": 150, "description": "Cremă pentru hidratarea profundă a pielii mature."},
    {"name": "Șampon Natural Bio", "category": "Cosmetice", "price": 80, "description": "Șampon fără parabeni, potrivit pentru toate tipurile de păr."}
]

with app.app_context():
    db.session.bulk_insert_mappings(Product, products)
    db.session.commit()
    print(f"{len(products)} produse au fost adăugate în baza de date!")
