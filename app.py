# Railway redeploy test
# from flask import Flask, render_template, request, redirect, session, flash
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
import bcrypt
import os
import certifi
load_dotenv()

import os

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)  # ✅ THIS MUST BE FIRST

app.secret_key = os.getenv("SECRET_KEY")

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["ecommer"]

users = db.users
products = db.products
orders = db.orders
wishlist = db.wishlist
reviews = db.reviews



@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    all_products = list(
        products.find()
    )

    cart_count = len(
        session.get("cart", [])
    )

    return render_template(
        "home.html",
        user=session["user"],
        products=all_products,
        cart_count=cart_count
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing = users.find_one({"email": email})

        if existing:
            flash("Email already registered")
            return redirect("/register")

        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        users.insert_one({
            "name": name,
            "email": email,
            "password": hashed.decode("utf-8"),
            "role": "admin" if email == "admin@gmail.com" else "user"
        })

        flash("Registration Successful")
        return redirect("/login")

    return render_template("register.html")
 



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = users.find_one({"email": email})

     

        if not user:
            flash("User not found")
            return redirect("/login")

        stored_hash = user.get("password")

        if not stored_hash:
            flash("No password found in account")
            return redirect("/login")

        try:
            if bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8")
            ):

                session["user"] = user["name"]
                session["email"] = user["email"]
                session["role"] = user.get("role", "user")

                # ✅ ADMIN CHECK
                if session["role"] == "admin":
                    return redirect("/admin")

                return redirect("/")

        except:
            flash("Login error")
            return redirect("/login")

        flash("Invalid email or password")
        return redirect("/login")

    return render_template("login.html")



@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


@app.route("/product/<id>")
def product_detail(id):

    product = products.find_one(
        {"_id": ObjectId(id)}
    )

    return render_template(
        "product.html",
        product=product
    )

@app.route("/add_to_cart/<id>")
def add_to_cart(id):

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(id)

    session.modified = True

    return redirect("/cart")

@app.route("/cart")
def cart():

    cart_items = []

    if "cart" in session:

        for item_id in session["cart"]:

            product = products.find_one(
                {"_id": ObjectId(item_id)}
            )

            if product:
                cart_items.append(product)

    total = sum(
        item["price"]
        for item in cart_items
    )

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )

@app.route("/checkout")
def checkout():

    if "user" not in session:
        return redirect("/login")

    cart_items = []

    if "cart" in session:

        for item_id in session["cart"]:

            product = products.find_one(
                {"_id": ObjectId(item_id)}
            )

            if product:
                cart_items.append(product)

    total = sum(
        item["price"]
        for item in cart_items
    )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )

@app.route("/place_order", methods=["POST"])
def place_order():

    if "user" not in session:
        return redirect("/login")

    cart_items = []

    total = 0

    for item_id in session.get("cart", []):

        product = products.find_one(
            {"_id": ObjectId(item_id)}
        )

        if product:

            cart_items.append({
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"]
            })

            total += product["price"]

    order = {

        "customer_name": session["user"],
        "customer_email": session["email"],

        "items": cart_items,

        "total": total,

        "status": "Pending"
    }

    orders.insert_one(order)

    session["cart"] = []

    return redirect("/orders")

@app.route("/orders")
def orders_page():

    if "user" not in session:
        return redirect("/login")

    user_orders = list(
        orders.find(
            {
                "customer_email":
                session["email"]
            }
        )
    )

    return render_template(
        "orders.html",
        orders=user_orders
    )
@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return redirect("/admin/login")

    return redirect("/admin/products")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        admin = users.find_one({"email": email})

        if admin and admin.get("role") == "admin":

            session["user"] = admin["name"]
            session["email"] = admin["email"]
            session["role"] = "admin"

            return redirect("/admin/products")

        return redirect("/admin/login")

    return render_template("admin_login.html")




@app.route("/admin/products")
def admin_products():

    if session.get("role") != "admin":
        return redirect("/")

    all_products = list(
        products.find()
    )

    return render_template(
        "admin_products.html",
        products=all_products
    )

@app.route("/admin/add_product", methods=["GET", "POST"])
def add_product():

    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":

        name = request.form.get("name")
        price = request.form.get("price")
        image = request.form.get("image")
        description = request.form.get("description")

        if not name or not price:
            return "Missing fields"

        products.insert_one({
            "name": name,
            "price": int(price),
            "image": image,
            "description": description
        })

        return redirect("/admin/products")

    return render_template("add_product.html")

@app.route("/admin/delete_product/<id>")
def delete_product(id):

    if session.get("role") != "admin":
        return redirect("/")

    products.delete_one({
        "_id": ObjectId(id)
    })

    return redirect(
        "/admin/products"
    )

    users.update_one(
    {"email": "admin@gmail.com"},
    {"$set": {
        "name": "Admin",
        "email": "admin@gmail.com",
        "password": "admin123",
        "role": "admin"
    }},
    upsert=True
)

from bson import ObjectId

@app.route('/admin/edit_product/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):

    product = products.find_one(
        {"_id": ObjectId(product_id)}
    )

    if request.method == "POST":
        products.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "name": request.form["name"],
                    "price": int(request.form["price"]),
                    "image": request.form["image"],
                    "description": request.form["description"]
                }
            }
        )

        return redirect("/admin/products")

    return render_template(
        "edit_product.html",
        product=product
    )

@app.route("/admin/orders")
def admin_orders():

    if session.get("role") != "admin":
        return redirect("/")

    all_orders = list(
        orders.find()
    )

    return render_template(
        "admin_orders.html",
        orders=all_orders
    )

@app.route("/admin/users")
def admin_users():

    if session.get("role") != "admin":
        return redirect("/")

    all_users = list(
        users.find()
    )

    return render_template(
        "admin_users.html",
        users=all_users
    )

@app.route("/search")
def search():

    keyword = request.args.get("q", "")

    result = list(
        products.find({
            "name": {
                "$regex": keyword,
                "$options": "i"
            }
        })
    )

    return render_template(
        "search.html",
        products=result,
        keyword=keyword
    )

@app.route("/category/<category>")
def category(category):

    category_products = list(
        products.find({
            "category": category
        })
    )

    return render_template(
        "category.html",
        products=category_products,
        category=category
    )

@app.route("/wishlist/add/<id>")
def add_wishlist(id):

    if "email" not in session:
        return redirect("/login")

    wishlist.insert_one({
        "user": session["email"],
        "product_id": id
    })

    return redirect("/wishlist")

@app.route("/wishlist")
def view_wishlist():

    if "email" not in session:
        return redirect("/login")

    items = list(wishlist.find({"user": session["email"]}))

    product_list = []

    for item in items:
        product = products.find_one({"_id": ObjectId(item["product_id"])})
        if product:
            product_list.append(product)

    return render_template("wishlist.html", items=product_list)




@app.route(
"/review/<id>",
methods=["POST"]
)
def review(id):

    reviews.insert_one({

        "product_id": id,

        "user": session["email"],

        "rating":
        int(request.form["rating"]),

        "comment":
        request.form["comment"]

    })

    return redirect(
        f"/product/{id}"
    )

@app.route(
"/admin/update_order/<id>/<status>"
)
def update_order(id, status):

    orders.update_one(
        {
            "_id": ObjectId(id)
        },
        {
            "$set": {
                "status": status
            }
        }
    )

    return redirect(
        "/admin/orders"
    )

@app.route("/test")
def test():
    return "Flask is working!"


if __name__ == "__main__":
    app.run(debug=True)

@app.route("/make_admin")
def make_admin():

    users.update_one(
        {"email": "admin@gmail.com"},
        {"$set": {
            "name": "Admin",
            "email": "admin@gmail.com",
            "role": "admin"
        }},
        upsert=True
    )

    return "Admin created"


