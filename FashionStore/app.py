from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3, re

app = Flask(__name__)
app.secret_key = 'your_strong_and_unique_secret_key_12345'
DB = 'fashion_store.db'


# ---------- DATABASE ----------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db: db.close()


# ---------- CUSTOMER ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/product_details')
def product_details():
    """Show single product details."""
    pid = request.args.get('id')
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return render_template('product_details.html', product=None)

    db = get_db()
    item = db.execute('SELECT * FROM Inventory WHERE id = ?', (pid,)).fetchone()
    product = dict(item) if item else None
    if product:
        product['current_stock'] = int(product['qty_initial_bought']) - int(product['qty_sold'])

    msg = session.pop('status_message', None)
    return render_template('product_details.html', product=product, status_message=msg)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Add an item to the cart."""
    try:
        pid = int(request.form['item_id'])
        qty = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        session['status_message'] = "❌ Invalid item or quantity."
        return redirect(url_for('index'))

    if qty <= 0:
        session['status_message'] = "❌ Quantity must be at least 1."
        return redirect(url_for('product_details', id=pid))

    cart = session.get('cart', {})
    pid_str = str(pid)
    db = get_db()

    item = db.execute('SELECT item_name, qty_initial_bought, qty_sold FROM Inventory WHERE id = ?', (pid,)).fetchone()
    if not item:
        session['status_message'] = "❌ Product not found."
        return redirect(url_for('index'))

    stock = int(item['qty_initial_bought']) - int(item['qty_sold'])
    in_cart = cart.get(pid_str, 0)
    total = in_cart + qty

    if total > stock:
        left = max(0, stock - in_cart)
        session['status_message'] = f"⚠️ Only {left} units of {item['item_name']} left."
    else:
        cart[pid_str] = total
        session['status_message'] = f"✅ Added {qty} × {item['item_name']}!"
        session['cart'] = cart

    session.modified = True
    return redirect(url_for('product_details', id=pid))


@app.route('/cart')
def view_cart():
    """Show cart items with totals."""
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', cart_items=[], grand_total=0, total_cart_items=0)

    try:
        ids = [int(i) for i in cart.keys()]
    except ValueError:
        ids = []

    if not ids:
        return render_template('cart.html', cart_items=[], grand_total=0, total_cart_items=0)

    db = get_db()
    qmarks = ','.join(['?'] * len(ids))
    rows = db.execute(f'SELECT * FROM Inventory WHERE id IN ({qmarks})', ids).fetchall()

    items, total, count = [], 0.0, 0
    for r in rows:
        price = float(re.sub(r'[^\d.]', '', str(r['unit_price'])) or 0)
        qty = cart.get(str(r['id']), 0)
        subtotal = price * qty
        stock = int(r['qty_initial_bought']) - int(r['qty_sold'])
        total += subtotal
        count += qty
        items.append({
            'id': r['id'], 'item_name': r['item_name'], 'unit_price': price,
            'quantity': qty, 'total': subtotal, 'image': r['image'],
            'current_stock': stock
        })

    return render_template('cart.html', cart_items=items, grand_total=total, total_cart_items=count)


@app.route('/update_cart', methods=['POST'])
def update_cart():
    """Change or remove an item in the cart."""
    try:
        pid = int(request.form['item_id'])
        qty = int(request.form['quantity'])
    except (ValueError, TypeError):
        return redirect(url_for('view_cart'))

    cart = session.get('cart', {})
    key = str(pid)

    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Finalize purchase and update inventory."""
    if request.method == 'GET':
        return render_template('checkout.html', success=None)

    cart = session.pop('cart', {})
    if not cart:
        session['status_message'] = "❌ Your cart is empty."
        return redirect(url_for('index'))

    db = get_db()
    success = True
    try:
        for sid, qty in cart.items():
            pid = int(sid)
            item = db.execute('SELECT item_name, qty_initial_bought, qty_sold FROM Inventory WHERE id = ?', (pid,)).fetchone()
            if not item: success = False; break
            stock = int(item['qty_initial_bought']) - int(item['qty_sold'])
            if stock < qty:
                success = False
                session['status_message'] = f"❌ {item['item_name']} only has {stock} left."
                session['cart'] = cart; break
            db.execute('UPDATE Inventory SET qty_sold = qty_sold + ? WHERE id = ?', (qty, pid))
        if success:
            db.commit()
            session['status_message'] = "✅ Checkout successful!"
        else:
            db.rollback()
    except Exception as e:
        db.rollback()
        success = False
        session['status_message'] = "❌ Error during checkout."
        print("Checkout error:", e)

    return render_template('checkout.html', success=success)


# ---------- ADMIN ----------
@app.route('/admin/inventory')
def inventory_report():
    db = get_db()
    data = db.execute('SELECT * FROM Inventory ORDER BY id').fetchall()
    report = []
    for r in data:
        bought, sold = int(r['qty_initial_bought']), int(r['qty_sold'])
        price = float(r['unit_price'] or 0)
        stock = bought - sold
        revenue = sold * price
        report.append({
            'id': r['id'], 'item_name': r['item_name'],
            'qty_bought': bought, 'qty_sold': sold,
            'qty_stock': stock, 'revenue': revenue
        })
    return render_template('inventory_report.html', metrics=report)


@app.route('/admin/add_stock', methods=['GET', 'POST'])
def add_stock():
    db = get_db()
    msg = None
    if request.method == 'POST':
        try:
            pid = int(request.form['item_id'])
            qty = int(request.form['quantity'])
            if qty > 0:
                db.execute('UPDATE Inventory SET qty_initial_bought = qty_initial_bought + ? WHERE id = ?', (qty, pid))
                db.commit()
                msg = f"✅ Added {qty} units to item {pid}."
            else:
                msg = "❌ Enter a valid quantity."
        except Exception as e:
            msg = f"❌ Error: {e}"
        return redirect(url_for('add_stock', status_message=msg))

    items = db.execute('SELECT * FROM Inventory ORDER BY item_name').fetchall()
    msg = request.args.get('status_message')
    return render_template('add_stock.html', items=items, status_message=msg)


# ---------- MAIN ----------
if __name__ == '__main__':
    app.run(debug=True)
