from flask import Flask, render_template, session, redirect, request
import pymysql
from help import login_required,is_logged_in,upload_safe,CustomChatGPT
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
import random
import datetime

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

connection = pymysql.connect(host='localhost',
                             user='newuser',
                             password='password',
                             database='zenfit',
                             cursorclass=pymysql.cursors.DictCursor)

def setup():
  # with connection:
    with connection.cursor() as cursor:

      cursor.execute("""CREATE TABLE IF NOT EXISTS `user` (
        `id` int NOT NULL AUTO_INCREMENT,
        `join_time` datetime DEFAULT NULL,
        `email` varchar(255) NOT NULL,
        `username` varchar(255) NOT NULL,
        `password` varchar(255) NOT NULL,
        `image_url` varchar(255) DEFAULT NULL,
        `firstname` varchar(255) NOT NULL,
        `lastname` varchar(255) NOT NULL,
        `age` int NOT NULL,
        `height` int NOT NULL,
        `weight` int NOT NULL,
        PRIMARY KEY (`id`),
        UNIQUE KEY `username` (`username`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `product` (
        `id` int NOT NULL AUTO_INCREMENT,
        `product_name` varchar(255) DEFAULT NULL,
        `rating` int DEFAULT NULL,
        `image_url` varchar(255) DEFAULT NULL,
        `product_description` text DEFAULT NULL,
        `product_price` int DEFAULT NULL,
        `product_seller_id` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`product_seller_id`) REFERENCES `user` (`id`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `order_product` (
        `id` int NOT NULL AUTO_INCREMENT,
        `order_id` int DEFAULT NULL,
        `product_id` int DEFAULT NULL,
        `quantity` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`product_id`) REFERENCES `product` (`id`)
        )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `address` (
        `id` int NOT NULL AUTO_INCREMENT,
        `street` varchar(255) DEFAULT NULL,
        `city` varchar(255) DEFAULT NULL,
        `state` varchar(255) DEFAULT NULL,
        `zip` varchar(255) DEFAULT NULL,
        `user_id` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `post` (
        `id` int NOT NULL AUTO_INCREMENT,
        `post_title` varchar(255) DEFAULT NULL,
        `image_url` varchar(255) DEFAULT NULL,
        `post_time` datetime DEFAULT NULL,
        `post_text` text DEFAULT NULL,
        `user_id` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `reply` (
        `id` int NOT NULL AUTO_INCREMENT,
        `reply_time` datetime DEFAULT NULL,
        `reply_text` text DEFAULT NULL,
        `post_id` int DEFAULT NULL,
        `user_id` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `event` (
        `id` int NOT NULL AUTO_INCREMENT,
        `event_title` varchar(255) DEFAULT NULL,
        `event_organizer` varchar(255) DEFAULT NULL,
        `event_description` text DEFAULT NULL,
        `event_start` datetime DEFAULT NULL,
        `event_end` datetime DEFAULT NULL,
        PRIMARY KEY (`id`)
      )""")
      
      cursor.execute("""CREATE TABLE IF NOT EXISTS `order` (
        `id` int NOT NULL AUTO_INCREMENT,
        `order_status` int DEFAULT NULL,
        `user_id` int DEFAULT NULL,
        `address_id` int DEFAULT NULL,
        `order_time` datetime DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
      )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `category` (
        `id` int NOT NULL AUTO_INCREMENT,
        `name` varchar(255) NOT NULL,
        PRIMARY KEY (`id`),
        UNIQUE KEY `name` (`name`)
        )""")

      cursor.execute("""CREATE TABLE IF NOT EXISTS `product_category` (
        `id` int NOT NULL AUTO_INCREMENT,
        `product_id` int DEFAULT NULL ,
        `category_id` int DEFAULT NULL,
        PRIMARY KEY (`id`),
        FOREIGN KEY (`product_id`) REFERENCES `product` (`id`),
        FOREIGN KEY (`category_id`) REFERENCES `category` (`id`)
      )""")

setup()

def split_list_into_4(lst):
    n = len(lst)
    n_rows = n // 4 + (n % 4 > 0)
    result = [[] for _ in range(n_rows)]
    for i in range(n):
        result[i // 4].append(lst[i])
    return result

def get_trending_posts(num):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `post` LIMIT %s"""
        cursor.execute(sql,(num))
        trending = cursor.fetchall()

    for post in trending:
        author = selectuserbyid(post["user_id"])
        post["author"] = author
    
    return trending

def get_remaining_posts():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `post` LIMIT 3, 10000"""
        cursor.execute(sql,())
        posts = cursor.fetchall()

    for post in posts:
        author = selectuserbyid(post["user_id"])
        post["author"] = author

    return posts

def selectuserbyusername(username):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `user` WHERE `username`=%s"""
        cursor.execute(sql,username)
        rows = cursor.fetchall()
    return rows

def selectuserbyid(userid):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `user` WHERE `id`=%s"""
        cursor.execute(sql,userid)
        rows = cursor.fetchone()
    return rows

def retrieve_cart_id():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `order` WHERE `order_status`=%s AND `user_id`=%s"""
        cursor.execute(sql,(0,session["user_id"]))
        cart = cursor.fetchone()
        cartid = cart["id"]
    return cartid

def get_cart_from_cartid(cartid):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `order_product` WHERE `order_id`=%s"""
        cursor.execute(sql,(cartid))
        cart_products = cursor.fetchall()
    return cart_products

def get_productsandnet_from_cart(cart_products):
    products_list = []
    net_price = 0

    with connection.cursor() as cursor:
        for cart_product in cart_products:
            sql = """SELECT * FROM `product` WHERE `id`=%s"""
            cursor.execute(sql,(cart_product["product_id"]))
            actual_product = cursor.fetchone()
            actual_product["quantity"] = cart_product["quantity"]
            products_list.append(actual_product)
            net_price += cart_product["quantity"]*actual_product["product_price"]
    
    return products_list, net_price

def get_addresses():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `address` WHERE `user_id`=%s"""
        cursor.execute(sql,(session["user_id"]))
        addresses = cursor.fetchall()
    return addresses

def get4randomproducts():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `product`"""
        cursor.execute(sql,())
        products = cursor.fetchall()
    if len(products) >= 4:
        products = random.sample(products,4)
    return products


def get_orders():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `order` WHERE `order_status`=1 AND `user_id`=%s ORDER BY order_time DESC"""
        cursor.execute(sql,(session["user_id"]))
        orders = cursor.fetchall()
    return orders

def get_products_of_order(order):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `order_product` WHERE `order_id`=%s"""
        cursor.execute(sql,(order["id"]))
        products = cursor.fetchall()
    return products

def get_products_from_order_products(order_products):
    products = []
    for order_product in order_products:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM `product` WHERE `id`=%s"""
            cursor.execute(sql,(order_product["product_id"]))
            product = cursor.fetchone()
            product["num"] = order_product["quantity"]
            products.append(product)
    return products

def selectpostsbyuserid(userid):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `post` WHERE `user_id`=%s"""
        cursor.execute(sql,(userid))
        rows = cursor.fetchall()
    for row in rows:
        row["num"] = selectrepliesbypostid(row["id"])[1]
    return rows

def selectpostbyid(postid):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `post` WHERE `id`=%s"""
        cursor.execute(sql,(postid))
        post = cursor.fetchone()
    return post

def selectrepliesbypostid(postid):
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `reply` WHERE `post_id`=%s"""
        cursor.execute(sql,(postid))
        replies = cursor.fetchall()

    for reply in replies:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM `user` WHERE `id`=%s"""
            cursor.execute(sql,(reply["user_id"]))
            author = cursor.fetchone()
        reply["author"] = author

    return replies,len(replies)

@app.route("/chat",methods=["GET", "POST"])
def chat():
    request_data = request.args.get('data')
    return (CustomChatGPT(request_data))


@app.route('/', defaults={'arg': ""})
@app.route('/arg=<arg>')
def index(arg):
    print(arg)
    connection.ping()
    posts = get_remaining_posts()
    trending = get_trending_posts(5)
    return render_template('index.html', logged=(is_logged_in()),products=get4randomproducts(),trending=trending,arg=arg)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return redirect("/arg=username not submitted")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect("/arg=password not submitted")
        
        rows = selectuserbyusername(request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return (redirect("/arg=username does not exist or password is incorrect"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/arg=You have been logged in!")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return redirect("/arg=Do not access this path like that!")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == 'POST':
        username = (request.form.get("username")).strip()
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        password = request.form.get("password")
        email = request.form.get("email")
        hash = generate_password_hash(password)
        
        rows = selectuserbyusername(username)

        if not (username and firstname and lastname and request.form.get("age") and request.form.get("height") and request.form.get("weight") and password and email and hash):
            return redirect("/arg=you left a field empty")

        age = int(request.form.get("age"))
        height = int(request.form.get("height"))
        weight = int(request.form.get("weight"))

        if rows or not username:
            return redirect("/arg=name exists or empty")

        if not password:
            return redirect("/arg=passwords do not match or empty")

        with connection.cursor() as cursor:
            sql = f"INSERT INTO user (username,email,firstname,lastname,age,height,weight,password,join_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (username,email,firstname,lastname,age,height,weight,hash,(datetime.datetime.now())))
            connection.commit()

            sql = """SELECT id FROM `user` WHERE `username`=%s"""
            cursor.execute(sql,username)
            userid = cursor.fetchone()["id"]

            sql = f"INSERT INTO `order` (order_status,user_id) VALUES (%s,%s)"
            cursor.execute(sql, (0,userid))
            connection.commit()

        return redirect("/arg=You have been registered! Please Login")

    else:
        return redirect("/arg=Do not access this path like that!")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/arg=You have been logged out! ")

@app.route("/store",methods=["GET","POST"])
def store():
    connection.ping()
    if request.method == "POST":
        if request.form.get("submit") == "search":
            inputtext = request.form.get("inputtext")
            words = inputtext.split()
            products = []
            with connection.cursor() as cursor:
                for word in words:
                    word = "%"+word+"%"
                    sql = f"SELECT * FROM `product` WHERE product_name LIKE %s"
                    cursor.execute(sql,(word))
                    ans = cursor.fetchall()
                    if ans == tuple():
                        ans = []
                    products = products + ans
        elif request.form.get("submit") == "apply":
            if "category" in request.form:
                with connection.cursor() as cursor:
                    sql = """SELECT product_id FROM product_category WHERE category_id=%s """
                    cursor.execute(sql,request.form.get("category"))
                    product_ids = cursor.fetchall()
                products = []
                for prod_id in product_ids:
                    with connection.cursor() as cursor:
                        sql = """SELECT * FROM `product` WHERE `id`=%s"""
                        cursor.execute(sql,(prod_id["product_id"]))
                        products.append(cursor.fetchone())
            else:
                with connection.cursor() as cursor:
                    sql = """SELECT * FROM `product`"""
                    cursor.execute(sql,())
                    products = cursor.fetchall()
            
            if "rating" in request.form:
                with connection.cursor() as cursor:
                    sql = """SELECT * FROM `product` WHERE `rating`=%s"""
                    cursor.execute(sql,(request.form.get("rating")))
                    ratedproducts = cursor.fetchall()
                if "category" in request.form:
                    final = []
                    for product in products:
                        if product in ratedproducts:
                            final.append(product)
                    products = final
                else:
                    products = ratedproducts
            
        elif request.form.get("submit") == "reset":
            with connection.cursor() as cursor:
                sql = """SELECT * FROM `product`"""
                cursor.execute(sql,())
                products = cursor.fetchall()
    else:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM `product`"""
            cursor.execute(sql,())
            products = cursor.fetchall()
    if (len(products) > 16):
        products = random.sample(products,16)
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `category`"""
        cursor.execute(sql,())
        categories = cursor.fetchall()
    return render_template("store-page.html",products=split_list_into_4(products),categories=categories,logged=(is_logged_in()))


@app.route("/product/<productid>",methods=["GET","POST"])
def product(productid):
    if request.method == "POST":
        if ("user_id" not in session):
            return redirect("/arg=you are not logged in")
        else:
            with connection.cursor() as cursor:
                sql = """SELECT * FROM `order` WHERE `order_status`=%s AND `user_id`=%s"""
                cursor.execute(sql,(0,session["user_id"]))
                cart = cursor.fetchone()
                cartid = cart["id"]
                sql = """SELECT * FROM `order_product` WHERE `order_id`=%s"""
                cursor.execute(sql,(cartid))
                cart_products = cursor.fetchall()
                exists = 0
                number = request.form.get("number")
                for product in cart_products:
                    if int(productid) == product["product_id"]:
                        sql = """UPDATE `order_product` SET `quantity`=`quantity`+%s WHERE `id`=%s"""
                        cursor.execute(sql,(number,product["id"]))
                        connection.commit()
                        exists = 1
                        break
                
                if exists == 0:
                    sql = f"INSERT INTO `order_product` (order_id,product_id,quantity) VALUES (%s,%s,%s)"
                    cursor.execute(sql, (cartid,productid,number))
                    connection.commit()
            return redirect("/checkout")
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `product` WHERE `id`=%s"""
        cursor.execute(sql,(productid))
        product = cursor.fetchone()

        sql = """SELECT `category_id` FROM `product_category` WHERE `product_id`=%s"""
        cursor.execute(sql,(productid))
        category_ids = cursor.fetchall()
        categories = []
        for category_id in category_ids:
            sql = """SELECT name FROM `category` WHERE `id`=%s"""
            cursor.execute(sql,(category_id["category_id"]))
            category = cursor.fetchone()
            categories.append(category["name"])
    ans = get4randomproducts()
    return render_template("product-page.html",product=product,categories=categories,fourprods=ans,logged=(is_logged_in()))

@app.route("/checkout",methods=["GET","POST"])
@login_required
def checkout():
    cartid = retrieve_cart_id()
    (products_list,net_price) = get_productsandnet_from_cart(get_cart_from_cartid(cartid))
    if request.method == "POST":
        if (products_list == []):
            return redirect("/arg=Your cart was empty!")

        with connection.cursor() as cursor:
            street =request.form.get("street")
            city = request.form.get("city")
            state = request.form.get("state")
            zip = request.form.get("zip")
            if ("address") in request.form:
                if (street!="" or city!="" or state!="" or zip!=""):
                    return redirect("/arg=please select an existing address or fill in a new one not both!")
                addressid = request.form.get("address")
            else:
                if (street=="" or city=="" or state=="" or zip==""):
                    return redirect("/arg=please fill all the fields in the new address!")
                sql = f"INSERT INTO `address` (street,city,state,zip,user_id) VALUES (%s,%s,%s,%s,%s)"
                cursor.execute(sql,(street,city,state,zip,session["user_id"]))
                connection.commit()
                addressid = cursor.lastrowid
            sql = """UPDATE `order` SET `order_status`=1, `address_id`=%s, `order_time`=%s WHERE `id`=%s """
            cursor.execute(sql,(addressid,datetime.datetime.now(),cartid))
            connection.commit()

            sql = f"INSERT INTO `order` (order_status,user_id) VALUES (%s,%s)"
            cursor.execute(sql, (0,session["user_id"]))
            connection.commit()

        return redirect("/arg=Your order has been completed! Please check your items in order history!")
    else:
        addresses = get_addresses()
        return render_template("check-out-page.html",products=products_list,net=net_price,addresses=addresses)

@app.route("/AI",methods=["GET","POST"])
@login_required
def ai():
    return render_template("zen-ai-page.html")

def getevents():
    with connection.cursor() as cursor:
        sql = """SELECT * FROM `event` ORDER BY `event_start`"""
        cursor.execute(sql,())
        rows = cursor.fetchall()
    return rows

@app.route("/user",methods=["GET","POST"])
@login_required
def user():
    if request.method == "POST":
        with connection.cursor() as cursor:
            if (request.form.get("submit") == "changeuser"):
                uploadedfile = request.files["user_file"]
                firstname = request.form.get("firstname")
                lastname = request.form.get("lastname")
                email = request.form.get("email")
                age = request.form.get("age")
                height = request.form.get("height")
                weight = request.form.get("weight")
                if uploadedfile:
                    filename = upload_safe(uploadedfile)
                    sql = """UPDATE `user` SET `firstname`=%s, `lastname`=%s, `email`=%s, `age`=%s, `height`=%s, `weight`=%s, `image_url`=%s WHERE `id`=%s """
                    cursor.execute(sql,(firstname,lastname,email,age,height,weight,"https://flask-zenfit.s3.amazonaws.com/"+filename,session["user_id"]))
                else:
                    sql = """UPDATE `user` SET `firstname`=%s, `lastname`=%s, `email`=%s, `age`=%s, `height`=%s, `weight`=%s WHERE `id`=%s """
                    cursor.execute(sql,(firstname,lastname,email,age,height,weight,session["user_id"]))
                connection.commit()
            else:
                password1 = request.form.get("password")
                confirm = request.form.get("confirm")
                if (password1 != confirm or not password1):
                    return redirect("/arg=passwords do not match or empty")
                hash = generate_password_hash(password1)
                sql = """UPDATE `user` SET `password`=%s WHERE `id`=%s """
                cursor.execute(sql,(hash,session["user_id"]))
                return redirect("/logout")

    userid = session["user_id"]
    yourposts = selectpostsbyuserid(userid)
    user = selectuserbyid(userid)
    (products_list,net_price) = get_productsandnet_from_cart(get_cart_from_cartid(retrieve_cart_id()))
    events = getevents()
    return render_template("user-page.html",user=user,posts=yourposts,products=products_list,net=net_price,events=events)

@app.route("/order-history",methods=["GET","POST"])
@login_required
def history():
    orders = get_orders()
    for order in orders:
        order_products =  get_products_of_order(order)
        products = get_products_from_order_products(order_products)
        order["products"] = products

    return render_template("order-history-page.html",orders=orders)

@app.route("/post/<postid>",methods=["GET","POST"])
@login_required
def detailpost(postid):
    if request.method == "POST":
        reply = request.form.get("reply")
        userid = session["user_id"]
        with connection.cursor() as cursor:
            sql = f"INSERT INTO `reply` (reply_text,reply_time,post_id,user_id) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql, (reply,(datetime.datetime.now()),postid,userid))
            connection.commit()
    
    replies = selectrepliesbypostid(postid)[0]

    post = selectpostbyid(postid)
    author = selectuserbyid(post["user_id"])
    post["author"] = author
    return render_template("post-page.html",post=post,replies=replies)

@app.route("/community",methods=["GET","POST"])
@login_required
def comm():
    posts = get_remaining_posts()
    trending = get_trending_posts(3)

    return render_template("community-page.html",posts=split_list_into_4(posts),trending=trending)

@app.route("/post/add",methods=["GET","POST"])
def addpost():
    if request.method == "POST":
        post_title = request.form.get("post_title")
        image_url = request.form.get("image_url")
        post_time = datetime.datetime.now()
        post_text = request.form.get("post_text")
        user_id = 1
        with connection.cursor() as cursor:
            sql = f"INSERT INTO `post` (post_title,image_url,post_time,post_text,user_id) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (post_title,image_url,post_time,post_text,user_id))
            connection.commit()
    return render_template("post_add.html")