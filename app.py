from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client['catalog_db']
products_collection = db['products']
admin_user = {'username': 'admin', 'password': 'admin123'}

# ------------------ Routes ------------------ #

@app.route('/')
def home():
    if 'admin' not in session:
        return redirect('/login')
    products = list(products_collection.find())
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == admin_user['username'] and password == admin_user['password']:
            session['admin'] = True
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if 'admin' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        file = request.files['image']
        filename = secure_filename(file.filename)
        image_id = str(uuid.uuid4()) + os.path.splitext(filename)[1]
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_id))

        # Only include non-empty attributes
        attributes = {}
        for key in request.form:
            if key.startswith('attr_'):
                attr_name = key.replace('attr_', '')
                value = request.form[key].strip()
                if value:  # Only add non-empty values
                    attributes[attr_name] = value

        product = {
            '_id': str(uuid.uuid4()),
            'name': request.form['name'],
            'price': request.form['price'],
            'description': request.form['description'],
            'type': request.form['type'],
            'image': image_id,
        }

        # Only add 'attributes' if there are any
        if attributes:
            product['attributes'] = attributes

        products_collection.insert_one(product)
        return redirect('/')
    
    return render_template('insert.html')

@app.route('/update/<product_id>', methods=['GET', 'POST'])
def update(product_id):
    if 'admin' not in session:
        return redirect('/login')

    product = products_collection.find_one({'_id': product_id})

    if not product:
        return "Product not found", 404

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        product_type = request.form['type']

        # Dynamic attributes (skip fixed fields)
        dynamic_attributes = {}
        for key in request.form:
            if key not in ['name', 'price', 'description', 'type']:
                dynamic_attributes[key] = request.form[key]

        updated_data = {
            'name': name,
            'price': price,
            'description': description,
            'type': product_type,
            'attributes': dynamic_attributes
        }

        # Handle image upload
        image = request.files['image']
        if image and image.filename != '':
            filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            updated_data['image'] = filename
        else:
            updated_data['image'] = product.get('image', '')

        products_collection.update_one({'_id': product_id}, {'$set': updated_data})
        return redirect('/')

    return render_template('update.html', product=product)



@app.route('/delete/<product_id>')
def delete(product_id):
    if 'admin' not in session:
        return redirect('/login')

    product = products_collection.find_one({'_id': product_id})

    if product:
        # Delete associated image if it exists
        image_filename = product.get('image')
        if image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

        products_collection.delete_one({'_id': product_id})
        return redirect('/')
    else:
        return "Product not found", 404


# ------------------ Run ------------------ #
if __name__ == '__main__':
    app.run(debug=True)
