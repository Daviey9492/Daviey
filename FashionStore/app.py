from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3, re

# --- Configuration ---
app = Flask(__name__)
app.secret_key = 'your_strong_and_unique_secret_key_12345'
DB = 'fashion_store.db'
SHIPPING_FEE_PER_ITEM = 129.00 # Set the required shipping fee per item


# ---------- DATABASE CONNECTION ----------
def get_db():
    """Connects to the specific database."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db: db.close()


# ---------- CUSTOMER ROUTES ----------
@app.route('/')
def index():
    """Renders the main index page."""
    return render_template('index.html')


@app.route('/product_details')
def product_details():
    """Show single product details."""
    pid = request.args.get('id')
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        # Redirect if ID is invalid
        flash("Invalid product request.", 'error')
        return redirect(url_for('index'))

    db = get_db()
    item = db.execute('SELECT * FROM Inventory WHERE id = ?', (pid,)).fetchone()
    product = dict(item) if item else None
    
    if product:
        # Calculate current stock for display
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
        session['status_message'] = f"⚠️ Only {left} units of {item['item_name']} left. Could not add {qty}."
    else:
        cart[pid_str] = total
        session['status_message'] = f"✅ Added {qty} × {item['item_name']}!"
        session['cart'] = cart

    session.modified = True
    return redirect(url_for('product_details', id=pid))


@app.route('/cart')
def view_cart():
    """
    Show cart items and calculate totals including per-item shipping cost.
    This function now handles all final financial calculations.
    """
    cart = session.get('cart', {})
    
    # Initialize variables for an empty cart case
    if not cart:
        return render_template('cart.html', cart_items=[], subtotal=0, item_count=0, 
                               shipping_fee=SHIPPING_FEE_PER_ITEM, total_shipping_cost=0, grand_total=0)

    try:
        ids = [int(i) for i in cart.keys()]
    except ValueError:
        ids = []

    if not ids:
        return render_template('cart.html', cart_items=[], subtotal=0, item_count=0, 
                               shipping_fee=SHIPPING_FEE_PER_ITEM, total_shipping_cost=0, grand_total=0)

    db = get_db()
    qmarks = ','.join(['?'] * len(ids))
    rows = db.execute(f'SELECT * FROM Inventory WHERE id IN ({qmarks})', ids).fetchall()

    items, subtotal, total_item_count = [], 0.0, 0
    for r in rows:
        # Use regex to safely extract the price and convert to float
        price_str = str(r['unit_price'])
        price = float(re.sub(r'[^\d.]', '', price_str) or 0)
        
        qty = cart.get(str(r['id']), 0)
        item_total = price * qty
        
        subtotal += item_total
        total_item_count += qty # Sum of all quantities
        
        stock = int(r['qty_initial_bought']) - int(r['qty_sold'])
        
        items.append({
            'id': r['id'], 'item_name': r['item_name'], 'unit_price': price,
            'quantity': qty, 'total': item_total, 'image': r['image'],
            'current_stock': stock
        })

    # --- FIX: Calculate Shipping and Grand Total ---
    total_shipping_cost = total_item_count * SHIPPING_FEE_PER_ITEM
    grand_total = subtotal + total_shipping_cost

    return render_template('cart.html', 
                           cart_items=items, 
                           subtotal=subtotal, 
                           item_count=total_item_count,
                           shipping_fee=SHIPPING_FEE_PER_ITEM,
                           total_shipping_cost=total_shipping_cost,
                           grand_total=grand_total)


@app.route('/update_cart', methods=['POST'])
def update_cart():
    """
    Change or remove an item in the cart using the manual quantity input.
    Handles both quantity change (Edit button) and removal (Remove button, sends qty=0).
    """
    try:
        pid = int(request.form['item_id'])
        # The 'quantity' value from the input field is the desired new quantity
        qty = int(request.form['quantity']) 
    except (ValueError, TypeError):
        session['status_message'] = "❌ Invalid item or quantity submitted."
        return redirect(url_for('view_cart'))

    cart = session.get('cart', {})
    key = str(pid)

    if qty <= 0:
        # Remove item if quantity is 0 or less
        cart.pop(key, None)
        session['status_message'] = "✅ Item removed from cart."
    else:
        db = get_db()
        item = db.execute('SELECT item_name, qty_initial_bought, qty_sold FROM Inventory WHERE id = ?', (pid,)).fetchone()
        
        if item:
            stock = int(item['qty_initial_bought']) - int(item['qty_sold'])
            if qty > stock:
                # Stock constraint check
                session['status_message'] = f"⚠️ Failed to update: Only {stock} units of {item['item_name']} in stock."
                return redirect(url_for('view_cart'))
            
            # If valid, update cart quantity
            cart[key] = qty
            session['status_message'] = f"✅ Quantity updated to {qty} for {item['item_name']}."
        else:
            session['status_message'] = "❌ Product not found."
            
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
                session['status_message'] = f"❌ {item['item_name']} only has {stock} left. Cannot checkout."
                session['cart'] = cart; break # Restore cart and break
            db.execute('UPDATE Inventory SET qty_sold = qty_sold + ? WHERE id = ?', (qty, pid))
        if success:
            db.commit()
            session['status_message'] = "✅ Checkout successful! Inventory updated."
        else:
            db.rollback()
    except Exception as e:
        db.rollback()
        success = False
        session['status_message'] = "❌ Error during checkout. Please try again."
        print("Checkout error:", e)

    return render_template('checkout.html', success=success)


# ---------- ADMIN ROUTES ----------
@app.route('/admin/inventory')
def inventory_report():
    """Generates the inventory report for the admin."""
    db = get_db()
    data = db.execute('SELECT * FROM Inventory ORDER BY id').fetchall()
    report = []
    for r in data:
        bought, sold = int(r['qty_initial_bought']), int(r['qty_sold'])
        # Ensure price conversion is safe
        price_str = str(r['unit_price'])
        price = float(re.sub(r'[^\d.]', '', price_str) or 0)
        
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
    """Handles the form to add stock to existing inventory items."""
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
                msg = "❌ Enter a valid quantity (must be positive)."
        except Exception as e:
            msg = f"❌ Error: {e}"
        # Use Flask's built-in flash messaging for status updates
        flash(msg, 'info')
        return redirect(url_for('add_stock'))

    items = db.execute('SELECT * FROM Inventory ORDER BY item_name').fetchall()
    return render_template('add_stock.html', items=items)


# ---------- MAIN ENTRY POINT ----------
if __name__ == '__main__':
    app.run(debug=True)
