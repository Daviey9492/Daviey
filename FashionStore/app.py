from flask import Flask, render_template, session, redirect, url_for, request
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

DATABASE = 'database.db'

# Initialize DB
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    sold INTEGER DEFAULT 0,
                    revenue REAL DEFAULT 0
                )''')
    # Sales table
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    quantity INTEGER,
                    total_price REAL,
                    timestamp TEXT
                )''')
    # Insert initial products if table empty
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ("Red Dress", 3000, 10),
            ("Blue Shirt", 1500, 15),
            ("Black Shoes", 5000, 5)
        ]
        c.executemany("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", products)
    conn.commit()
    conn.close()

init_db()

# Home page
@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return render_template('index.html', products=products)

# Add to cart
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('index'))

# Clear cart
@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))

# View cart
@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    if 'cart' in session:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        for product_id, qty in session['cart'].items():
            c.execute("SELECT * FROM products WHERE id=?", (product_id,))
            product = c.fetchone()
            if product:
                subtotal = product[2] * qty
                total += subtotal
                cart_items.append({
                    'id': product[0],
                    'name': product[1],
                    'price': product[2],
                    'quantity': qty,
                    'subtotal': subtotal
                })
        conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

# Checkout page
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        phone = request.form['phone']
        # Simulate payment success
        if 'cart' in session:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            for product_id, qty in session['cart'].items():
                c.execute("SELECT stock, sold, revenue, price FROM products WHERE id=?", (product_id,))
                product = c.fetchone()
                if product:
                    stock, sold, revenue, price = product
                    sold += qty
                    revenue += price * qty
                    stock -= qty
                    c.execute("UPDATE products SET sold=?, stock=?, revenue=? WHERE id=?",
                              (sold, stock, revenue, product_id))
                    c.execute("INSERT INTO sales (product_id, quantity, total_price, timestamp) VALUES (?, ?, ?, ?)",
                              (product_id, qty, price*qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
        session.pop('cart', None)
        return render_template('success.html', phone=phone)
    return render_template('checkout.html')

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
