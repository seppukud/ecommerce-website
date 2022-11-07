from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from azuredb import sql_connection
import random
import base64
import string
import redis
import json
import os
#from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage

from azure.storage.queue import QueueService, QueueMessageFormat

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

app = Flask(__name__)
app.secret_key = randomString()
AZURE_CDN_ENDPOINT = 'https://ecommercecdnendpoint.azureedge.net/'
STORAGE_ACCOUNT_NAME = "cdnstorageaccount2"

#STORAGE_ACCESS_KEY = os.environ['STORAGE_ACCESS_KEY']
STORAGE_ACCESS_KEY ='NBZVbMUi6oQmNvuk6xQz7kFUNOq4DUYqCLIKZM6AWnvAmO35boWEVQQfr76RZqIeHh3iLJbNVizW+ASthLJugA=='

BLOB_ACCOUNT_CONTAINER_URL = 'https://cdnstorageaccount2.blob.core.windows.net/ecomblobcontainer/'

#REDIS_ACCESS_KEY = os.environ['REDIS_ACCESS_KEY']
REDIS_ACCESS_KEY = 'sFyETkfNxa6rdrrvDXIheZanx8BWvQMw7AzCaO7xbHQ='

REDIS_HOSTNAME  = "ecommercecache.redis.cache.windows.net"
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = BLOB_ACCOUNT_CONTAINER_URL
app.static_url_path = AZURE_CDN_ENDPOINT

redis_client = redis.StrictRedis(host=REDIS_HOSTNAME, port=6380,
                                 password=REDIS_ACCESS_KEY, ssl=True)

def getLoginDetails():
    conn_obj = sql_connection()
    with conn_obj.conn as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute(f"SELECT userId, firstName FROM users WHERE CONVERT(VARCHAR, email) = '{session['email']}' ")
            userId, firstName = cur.fetchone()
            cur.execute(f"SELECT count(productId) FROM kart WHERE userId = '{userId}' ")
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    conn_obj = sql_connection()
    homepage_from_redis = redis_client.get("homepage")
    if homepage_from_redis:
        print("hitting cache to retrieve homepage")
        return homepage_from_redis.decode("utf-8")
    with conn_obj.conn as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        itemData = cur.fetchall()
        cur.execute('SELECT categoryId, name FROM categories')
        categoryData = cur.fetchall()
    itemData = parse(itemData)
    rendered_output = render_template('home.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)
    redis_client.set("homepage", rendered_output)
    return rendered_output

@app.route("/add")
def admin():
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute("SELECT categoryId, name FROM categories")
        categories = cur.fetchall()
    conn.close()
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        with sql_connection().conn as conn:
            try:
                cur = conn.cursor()
                cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (?, ?, ?, ?, ?, ?)''', (name, price, description, imagename, stock, categoryId))
                conn.commit()
                msg="added successfully"
            except:
                msg="error occured"
                conn.rollback()
        conn.close()
        print(msg)
        return redirect(url_for('root'))

@app.route("/remove")
def remove():
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        data = cur.fetchall()
    conn.close()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with sql_connection().conn as conn:
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE productID = ?', (productId, ))
            conn.commit()
            msg = "Deleted successsfully"
        except:
            conn.rollback()
            msg = "Error occured"
    conn.close()
    print(msg)
    return redirect(url_for('root'))

@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with sql_connection().conn as conn:
            cur = conn.cursor()
            cur.execute("SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = ?", (categoryId, ))
            data = cur.fetchall()
        conn.close()
        categoryName = data[0][4]
        data = parse(data)
        return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = ?", (session['email'], ))
        profileData = cur.fetchone()
    conn.close()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        with sql_connection().conn as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId, password FROM users WHERE CONVERT(VARCHAR, email) = ?", (session['email'], ))
            userId, password = cur.fetchone()
            if (password == oldPassword):
                try:
                    cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                    conn.commit()
                    msg="Changed successfully"
                except:
                    conn.rollback()
                    msg = "Failed"
                return render_template("changePassword.html", msg=msg)
            else:
                msg = "Wrong password"
        conn.close()
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        with sql_connection().conn as con:
                try:
                    cur = con.cursor()
                    cur.execute('UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ? WHERE email = ?', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))

                    con.commit()
                    msg = "Saved Successfully"
                except:
                    con.rollback()
                    msg = "Error occured"
        con.close()
        return redirect(url_for('editProfile'))

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            return render_template('login.html', error=error)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId = ?', (productId, ))
        productData = cur.fetchone()
    conn.close()
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        with sql_connection().conn as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE CONVERT(VARCHAR, email) = ?", (session['email'], ))
            userId = cur.fetchone()[0]
            try:
                cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                conn.commit()
                msg = "Added successfully"
            except:
                conn.rollback()
                msg = "Error occured"
        conn.close()
        return redirect(url_for('root'))

@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE CONVERT(VARCHAR, email) = ?", (email, ))
        userId = cur.fetchone()[0]
        cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = ?", (userId, ))
        products = cur.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/checkout")
def checkout():
    email = session['email']
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE CONVERT(VARCHAR, email) = ?", (email, ))
        userId = cur.fetchone()[0]
        cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = ?", (userId, ))
        products = cur.fetchall()
        # add in database orders with state.
        with sql_connection().conn as con:
            item_orderId_mapping = []
            queue_service = QueueService(account_name=STORAGE_ACCOUNT_NAME,account_key=STORAGE_ACCESS_KEY)
            for item in products:
                try:
                    cur = con.cursor()
                    cur.execute('INSERT INTO orders (userId, productId, status) VALUES (?, ?, ?)', (userId, item[0], "PENDING"))
                    con.commit()
                    msg = f"Added {item[0]} in orders table for userId:{userId}"

                    # Fetch order Id from database entry
                    cur.execute(f"SELECT orderId FROM orders where CONVERT(VARCHAR, productId)={item[0]} and userId={userId}")
                    orderId = cur.fetchone()[0]
                    order_item_dict = dict({'itemId': item[0], 'orderId': orderId})
                    item_orderId_mapping.append(order_item_dict)

                    # add the order Id and details in message queue to trigger job.
                    queue_entry = dict({
                        "userId" : userId,
                        "productId" : item[0],
                        "orderId" : orderId
                    })

                    # add the order details in queue.
                    queue_service.encode_function = QueueMessageFormat.binary_base64encode
                    queue_service.decode_function = QueueMessageFormat.binary_base64decode
                    queue_service.put_message("orders", base64.b64encode(json.dumps(queue_entry).encode()))
                except Exception as e:
                    con.rollback()
                    msg = "Error occured: " + str(e)
                    raise Exception(e)
    return (f"orders successfully created. Order id for each item: {item_orderId_mapping}")

@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE CONVERT(VARCHAR, email) = ?", (email, ))
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE userId = ? AND productId = ?", (userId, productId))
            conn.commit()
            msg = "removed successfully"
        except:
            conn.rollback()
            msg = "error occured"
    conn.close()
    return redirect(url_for('root'))

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

def is_valid(email, password):
    con = sql_connection().conn
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data    
        password = request.form['password']
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']

        with sql_connection().conn as con:
            try:
                cur = con.cursor()
                cur.execute('INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode, city, state, country, phone))
                con.commit()

                msg = "Registered Successfully"
            except Exception as e:
                con.rollback()
                msg = "Error occured: " + str(e)
        con.close()
        return render_template("login.html", error=msg)

@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

if __name__ == '__main__':
    #app.run(host="0.0.0.0",debug=True)
    
    app.run(host="0.0.0.0", port=80 ,debug=True)
