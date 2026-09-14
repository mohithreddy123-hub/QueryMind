"""
setup/fake_data.py
==================
Creates the MySQL database schema and populates it with realistic fake data
using the Faker library.

What this script does:
  1. Connects to MySQL using admin credentials (MYSQL_ADMIN_* in .env)
  2. Creates the database if it doesn't exist
  3. Creates all 5 tables (drops and recreates if --reset flag is passed)
  4. Generates fake data using Faker, respecting FK relationships
  5. Inserts data in batches for performance
  6. Prints progress and a final summary

Table creation order (respects FK dependencies):
  users → products → orders → payments → reviews

Data insertion order (same reason):
  users → products → orders → payments → reviews

Usage:
  python setup/fake_data.py            # create tables + insert data (skips if data exists)
  python setup/fake_data.py --reset    # drop all tables and start fresh
"""

import sys 
import os 
import random 
import argparse 
from datetime import datetime ,timedelta 


sys .path .insert (0 ,os .path .join (os .path .dirname (__file__ ),".."))

import mysql .connector 
from faker import Faker 

from config .settings import (
MYSQL_ADMIN_HOST ,
MYSQL_ADMIN_PORT ,
MYSQL_ADMIN_USER ,
MYSQL_ADMIN_PASSWORD ,
MYSQL_DATABASE ,
NUM_USERS ,
NUM_PRODUCTS ,
NUM_ORDERS ,
NUM_PAYMENTS ,
NUM_REVIEWS ,
)


fake =Faker ("en_IN")
Faker .seed (42 )
random .seed (42 )





PRODUCT_CATALOGUE ={
"Electronics":[
("Wireless Bluetooth Headphones",2499 ,3999 ),
("Smart LED TV 43 inch",28999 ,49999 ),
("USB-C Laptop Charger",899 ,1999 ),
("Mechanical Keyboard",3499 ,7999 ),
("Webcam 1080p",1499 ,3999 ),
("Portable Power Bank 20000mAh",1299 ,2999 ),
("Noise Cancelling Earbuds",3999 ,9999 ),
("Smart Watch Fitness Tracker",2499 ,6999 ),
("Gaming Mouse",799 ,2999 ),
("4K Monitor 27 inch",18999 ,35999 ),
("Wireless Router Dual Band",1999 ,4999 ),
("External SSD 1TB",5999 ,12999 ),
("Bluetooth Speaker Waterproof",1499 ,4999 ),
("Smartphone Gimbal Stabilizer",2999 ,6999 ),
("USB Hub 7 Port",699 ,1499 ),
],
"Clothing":[
("Men's Cotton Casual Shirt",599 ,1499 ),
("Women's Kurti Ethnic Print",799 ,1999 ),
("Denim Jeans Slim Fit",999 ,2499 ),
("Sports Track Pants",499 ,1299 ),
("Winter Hoodie Fleece",899 ,2499 ),
("Formal Trouser Men",799 ,1999 ),
("Anarkali Salwar Suit",1299 ,3999 ),
("Cotton Saree with Blouse",999 ,3499 ),
("Running Shoes Men",1499 ,4999 ),
("Sandals Women Comfortable",699 ,1999 ),
("Kids School Shoes",699 ,1499 ),
("Winter Jacket Padded",1799 ,4999 ),
("Yoga Pants Women",599 ,1499 ),
("Cricket Jersey",799 ,1999 ),
("Formal Blazer Men",2499 ,6999 ),
],
"Books":[
("Atomic Habits",299 ,499 ),
("Rich Dad Poor Dad",249 ,399 ),
("The Alchemist",199 ,349 ),
("Wings of Fire Autobiography",249 ,399 ),
("Python Programming for Beginners",399 ,699 ),
("Data Structures and Algorithms",499 ,899 ),
("Machine Learning with Python",599 ,999 ),
("The Psychology of Money",349 ,549 ),
("Zero to One",299 ,499 ),
("Deep Work",349 ,599 ),
("Sapiens A Brief History",399 ,699 ),
("Clean Code",599 ,1099 ),
("System Design Interview",799 ,1299 ),
("SQL for Beginners",349 ,599 ),
("React JS Complete Guide",449 ,799 ),
],
"Home & Garden":[
("Pressure Cooker 5 Litre",1299 ,2999 ),
("Non-Stick Cookware Set",1999 ,4999 ),
("Air Purifier HEPA Filter",6999 ,14999 ),
("Robot Vacuum Cleaner",9999 ,24999 ),
("Water Purifier RO UV",7999 ,19999 ),
("Mixer Grinder 750W",1999 ,3999 ),
("Ceiling Fan Energy Saving",1499 ,3499 ),
("LED Bulb 9W Pack of 6",299 ,599 ),
("Cotton Bedsheet King Size",899 ,2499 ),
("Memory Foam Pillow",799 ,1999 ),
("Indoor Plant Fiddle Leaf",499 ,1499 ),
("Garden Hose 50 feet",799 ,1999 ),
("Steel Almirah 2 Door",8999 ,19999 ),
("Plastic Storage Box Set",599 ,1499 ),
("Bathroom Shower Set",1299 ,3499 ),
],
"Sports":[
("Cricket Bat English Willow",1999 ,5999 ),
("Football Synthetic Leather",799 ,1999 ),
("Yoga Mat Anti-Slip 6mm",499 ,1499 ),
("Resistance Bands Set",299 ,799 ),
("Adjustable Dumbbell 10kg",1299 ,3499 ),
("Badminton Racket Set",899 ,2499 ),
("Swimming Goggles UV Protection",399 ,999 ),
("Cycling Helmet Adult",999 ,2499 ),
("Treadmill Manual Home",5999 ,14999 ),
("Protein Shaker Bottle",299 ,699 ),
("Boxing Gloves 12oz",799 ,1999 ),
("Skipping Rope Adjustable",199 ,599 ),
("Tennis Racket Professional",1499 ,3999 ),
("Gym Bag Sports Large",799 ,1999 ),
("Foam Roller Massage",599 ,1499 ),
],
"Beauty":[
("Vitamin C Face Serum",499 ,1299 ),
("SPF 50 Sunscreen Lotion",349 ,799 ),
("Hair Growth Oil Ayurvedic",299 ,699 ),
("Moisturising Face Cream",399 ,999 ),
("Lipstick Matte Finish",199 ,599 ),
("Kajal Waterproof",149 ,399 ),
("Foundation SPF 15",499 ,1299 ),
("Perfume Eau de Toilette 100ml",899 ,2999 ),
("Electric Face Cleanser Brush",799 ,1999 ),
("Nail Polish Set 12 Colors",299 ,799 ),
("Hair Straightener Ceramic",999 ,2999 ),
("Shampoo Anti-Dandruff 400ml",249 ,599 ),
("Body Lotion Shea Butter",299 ,799 ),
("Eye Cream Anti-Ageing",699 ,1999 ),
("Lip Balm SPF 30 Pack of 3",199 ,499 ),
],
"Food":[
("Organic Basmati Rice 5kg",599 ,999 ),
("Cold Pressed Coconut Oil 1L",399 ,799 ),
("Whey Protein Chocolate 1kg",1299 ,2999 ),
("Dry Fruits Mixed 500g",499 ,1299 ),
("Organic Honey Raw 500g",399 ,899 ),
("Dark Chocolate 70% Cacao",199 ,499 ),
("Green Tea Bags Pack 100",299 ,699 ),
("Multigrain Atta 10kg",699 ,1299 ),
("Peanut Butter Crunchy 1kg",399 ,799 ),
("Quinoa Organic 500g",349 ,799 ),
("Apple Cider Vinegar 500ml",299 ,699 ),
("Oats Quick Cook 1kg",199 ,499 ),
("Turmeric Powder Organic 200g",149 ,399 ),
("Almond Flour 500g",399 ,899 ),
("Coffee Beans Single Origin 250g",499 ,1299 ),
],
"Toys":[
("LEGO Classic Brick Set 500pcs",1999 ,4999 ),
("Remote Control Car Kids",999 ,2999 ),
("Barbie Doll with Accessories",799 ,1999 ),
("Educational Puzzle 200 Pieces",399 ,999 ),
("Wooden Building Blocks 50pcs",599 ,1499 ),
("Board Game Family Fun",799 ,1999 ),
("Play-Doh Modelling Clay Set",299 ,799 ),
("Electric Train Set Kids",2499 ,5999 ),
("Science Experiment Kit",699 ,1799 ),
("Drawing and Art Set Kids",499 ,1299 ),
("Soft Stuffed Teddy Bear",399 ,1299 ),
("Mini Basketball Hoop Set",799 ,1999 ),
("Action Figure Superhero",499 ,1299 ),
("Musical Keyboard Kids 32 Key",899 ,2499 ),
("Magnetic Drawing Board",399 ,999 ),
],
}


PAYMENT_STATUSES =["paid"]*70 +["pending"]*20 +["failed"]*10 


INDIAN_CITIES =[
"Mumbai","Delhi","Bengaluru","Hyderabad","Chennai","Kolkata",
"Pune","Ahmedabad","Jaipur","Surat","Lucknow","Kanpur",
"Nagpur","Indore","Thane","Bhopal","Visakhapatnam","Patna",
"Vadodara","Ghaziabad","Ludhiana","Agra","Nashik","Ranchi",
"Faridabad","Meerut","Rajkot","Varanasi","Srinagar","Aurangabad",
"Dhanbad","Amritsar","Navi Mumbai","Allahabad","Howrah","Coimbatore",
"Jabalpur","Gwalior","Vijayawada","Jodhpur","Madurai","Raipur",
"Kota","Chandigarh","Guwahati","Solapur","Hubli","Mysore",
"Tiruchirappalli","Bareilly",
]






def get_admin_connection (database :str |None =None ):
    """
    Returns a MySQL connection using admin credentials.
    Used only during setup (fake_data.py) to create tables and insert data.

    Args:
        database: If provided, connects directly to that database.
                  If None, connects without selecting a database (used to
                  create the database itself).
    """
    config ={
    "host":MYSQL_ADMIN_HOST ,
    "port":MYSQL_ADMIN_PORT ,
    "user":MYSQL_ADMIN_USER ,
    "password":MYSQL_ADMIN_PASSWORD ,
    }
    if database :
        config ["database"]=database 
    return mysql .connector .connect (**config )






CREATE_TABLES_SQL ="""
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(255)        NOT NULL,
    email      VARCHAR(255)        NOT NULL UNIQUE,
    city       VARCHAR(100)        NOT NULL,
    created_at DATETIME            NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(255)          NOT NULL,
    price    DECIMAL(10, 2)        NOT NULL,
    category VARCHAR(100)          NOT NULL,
    stock    INT                   NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT                 NOT NULL,
    product_id INT                 NOT NULL,
    quantity   INT                 NOT NULL DEFAULT 1,
    order_date DATETIME            NOT NULL,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    order_id     INT                  NOT NULL,
    amount       DECIMAL(10, 2)       NOT NULL,
    status       ENUM('paid', 'pending', 'failed') NOT NULL DEFAULT 'pending',
    payment_date DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT           NOT NULL,
    user_id    INT           NOT NULL,
    rating     TINYINT       NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE
);
"""

DROP_TABLES_SQL =[

"DROP TABLE IF EXISTS reviews",
"DROP TABLE IF EXISTS payments",
"DROP TABLE IF EXISTS orders",
"DROP TABLE IF EXISTS products",
"DROP TABLE IF EXISTS users",
]


def create_database (connection ):
    """Creates the database if it doesn't already exist."""
    cursor =connection .cursor ()
    cursor .execute (
    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE }` "
    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    connection .commit ()
    cursor .close ()
    print (f"  Database '{MYSQL_DATABASE }' ready.")


def drop_all_tables (connection ):
    """Drops all tables in reverse FK order (used with --reset flag)."""
    cursor =connection .cursor ()
    cursor .execute ("SET FOREIGN_KEY_CHECKS = 0")
    for sql in DROP_TABLES_SQL :
        cursor .execute (sql )
        print (f"  {sql }")
    cursor .execute ("SET FOREIGN_KEY_CHECKS = 1")
    connection .commit ()
    cursor .close ()


def create_all_tables (connection ):
    """Creates all tables using IF NOT EXISTS (safe to call repeatedly)."""
    cursor =connection .cursor ()

    statements =[s .strip ()for s in CREATE_TABLES_SQL .split (";")if s .strip ()]
    for stmt in statements :
        cursor .execute (stmt )
    connection .commit ()
    cursor .close ()
    print ("  All 5 tables created (or already exist).")






def random_date_in_past (days :int =365 )->datetime :
    """Returns a random datetime within the last `days` days."""
    end =datetime .now ()
    start =end -timedelta (days =days )
    delta =end -start 
    random_seconds =random .randint (0 ,int (delta .total_seconds ()))
    return start +timedelta (seconds =random_seconds )


def batch_insert (cursor ,table :str ,columns :list [str ],rows :list [tuple ],batch_size :int =500 ):
    """
    Inserts rows into `table` in batches.

    Batching dramatically reduces the number of round-trips to MySQL.
    Without batching, inserting 8,000 rows means 8,000 separate INSERT
    statements. With batch_size=500, it's 16 statements — much faster.
    """
    placeholders =", ".join (["%s"]*len (columns ))
    col_names =", ".join (columns )
    sql =f"INSERT INTO {table } ({col_names }) VALUES ({placeholders })"

    for i in range (0 ,len (rows ),batch_size ):
        chunk =rows [i :i +batch_size ]
        cursor .executemany (sql ,chunk )






def generate_users (n :int )->list [tuple ]:
    """
    Generates n fake users.
    Each user has a unique email (Faker may occasionally repeat — we deduplicate).
    """
    print (f"  Generating {n :,} users...",end ="",flush =True )
    users =[]
    emails_seen =set ()

    attempts =0 
    while len (users )<n :
        attempts +=1 
        if attempts >n *10 :

            raise RuntimeError ("Could not generate enough unique emails. Increase n or check Faker config.")

        name =fake .name ()
        email =fake .email ()
        if email in emails_seen :

            email =f"{len (users )}_{email }"
        emails_seen .add (email )

        city =random .choice (INDIAN_CITIES )

        created_at =random_date_in_past (days =3 *365 )

        users .append ((name ,email ,city ,created_at ))

    print (f" done ({len (users ):,} rows)")
    return users 


def generate_products (n :int )->list [tuple ]:
    """
    Generates n fake products from the product catalogue.
    Cycles through categories to ensure coverage across all 8 categories.
    """
    print (f"  Generating {n :,} products...",end ="",flush =True )
    products =[]
    catalogue_flat =[]

    for category ,items in PRODUCT_CATALOGUE .items ():
        for name_template ,price_min ,price_max in items :
            catalogue_flat .append ((category ,name_template ,price_min ,price_max ))

    for i in range (n ):
        category ,name_template ,price_min ,price_max =catalogue_flat [i %len (catalogue_flat )]

        suffix =f" v{i //len (catalogue_flat )+1 }"if i >=len (catalogue_flat )else ""
        name =name_template +suffix 

        price =round (random .uniform (price_min ,price_max ),2 )

        stock =random .choices ([0 ,random .randint (5 ,500 )],weights =[5 ,95 ])[0 ]
        products .append ((name ,price ,category ,stock ))

    print (f" done ({len (products ):,} rows)")
    return products 


def generate_orders (n :int ,user_ids :list [int ],product_ids :list [int ])->list [tuple ]:
    """
    Generates n fake orders.
    Each order references a valid user_id and product_id (FK integrity).
    """
    print (f"  Generating {n :,} orders...",end ="",flush =True )
    orders =[]
    for _ in range (n ):
        user_id =random .choice (user_ids )
        product_id =random .choice (product_ids )
        quantity =random .randint (1 ,5 )

        order_date =random_date_in_past (days =365 )
        orders .append ((user_id ,product_id ,quantity ,order_date ))
    print (f" done ({len (orders ):,} rows)")
    return orders 


def generate_payments (
order_ids :list [int ],
order_product_ids :list [int ],
product_prices :dict [int ,float ],
order_quantities :list [int ],
order_dates :list [datetime ],
)->list [tuple ]:
    """
    Generates one payment per order (1:1 relationship).
    Amount is calculated as quantity × product price (realistic total).

    Args:
        order_ids:         List of order IDs from the DB (after insert)
        order_product_ids: product_id for each order (parallel list)
        product_prices:    Map from product_id → price
        order_quantities:  quantity for each order (parallel list)
        order_dates:       order_date for each order (parallel list)
    """
    n =len (order_ids )
    print (f"  Generating {n :,} payments...",end ="",flush =True )
    payments =[]
    for i ,order_id in enumerate (order_ids ):
        product_id =order_product_ids [i ]
        price =product_prices [product_id ]
        quantity =order_quantities [i ]
        amount =round (price *quantity ,2 )

        status =random .choice (PAYMENT_STATUSES )


        if status =="paid":
            payment_date =order_dates [i ]+timedelta (
            hours =random .randint (0 ,72 )
            )
        else :

            payment_date =None 

        payments .append ((order_id ,amount ,status ,payment_date ))
    print (f" done ({len (payments ):,} rows)")
    return payments 


def generate_reviews (n :int ,product_ids :list [int ],user_ids :list [int ])->list [tuple ]:
    """
    Generates n fake product reviews.
    Ratings are skewed toward higher values (realistic for e-commerce).
    """
    print (f"  Generating {n :,} reviews...",end ="",flush =True )


    rating_pool =[1 ]*5 +[2 ]*10 +[3 ]*15 +[4 ]*30 +[5 ]*40 


    positive_comments =[
    "Great product! Highly recommend.",
    "Excellent quality for the price.",
    "Very happy with this purchase.",
    "Works perfectly as described.",
    "Delivered quickly and in good condition.",
    "Best purchase I made this year.",
    "Solid build quality. Impressed.",
    "Exactly as shown. No complaints.",
    "Worth every rupee. Good value.",
    "Fast shipping and great packaging.",
    ]
    neutral_comments =[
    "Decent product. Does the job.",
    "Average quality but acceptable.",
    "Okay for the price. Nothing special.",
    "Met my expectations. Satisfactory.",
    "Could be better but not bad.",
    ]
    negative_comments =[
    "Not as described. Disappointed.",
    "Poor quality. Would not recommend.",
    "Stopped working after a week.",
    "Packaging was damaged on arrival.",
    "Expected better for this price.",
    ]

    reviews =[]
    for _ in range (n ):
        product_id =random .choice (product_ids )
        user_id =random .choice (user_ids )
        rating =random .choice (rating_pool )

        if rating >=4 :
            comment =random .choice (positive_comments )
        elif rating ==3 :
            comment =random .choice (neutral_comments )
        else :
            comment =random .choice (negative_comments )

        reviews .append ((product_id ,user_id ,rating ,comment ))

    print (f" done ({len (reviews ):,} rows)")
    return reviews 






def table_has_data (cursor ,table :str )->bool :
    """Returns True if the table already contains at least one row."""
    cursor .execute (f"SELECT COUNT(*) FROM {table }")
    return cursor .fetchone ()[0 ]>0 


def get_ids (cursor ,table :str )->list [int ]:
    """Returns all primary key IDs from a table."""
    cursor .execute (f"SELECT id FROM {table }")
    return [row [0 ]for row in cursor .fetchall ()]






def main (reset :bool =False ):
    print ("="*60 )
    print ("  Text-to-SQL RAG Assistant — Database Setup")
    print ("="*60 )


    print ("\n[Step 1] Creating database...")
    try :
        conn_no_db =get_admin_connection (database =None )
        create_database (conn_no_db )
        conn_no_db .close ()
    except mysql .connector .Error as e :
        print (f"\n  ERROR: Cannot connect to MySQL.")
        print (f"  {e }")
        print (f"\n  Check that MySQL is running and that MYSQL_ADMIN_* credentials")
        print (f"  in your .env file are correct.")
        sys .exit (1 )


    try :
        conn =get_admin_connection (database =MYSQL_DATABASE )
        cursor =conn .cursor ()
    except mysql .connector .Error as e :
        print (f"\n  ERROR: Cannot connect to '{MYSQL_DATABASE }': {e }")
        sys .exit (1 )


    if reset :
        print ("\n[Step 2] Dropping all existing tables (--reset flag)...")
        drop_all_tables (conn )
    else :
        print ("\n[Step 2] Skipping drop (no --reset flag).")


    print ("\n[Step 3] Creating tables...")
    create_all_tables (conn )


    print ("\n[Step 4] Inserting fake data...")


    if not table_has_data (cursor ,"users"):
        user_rows =generate_users (NUM_USERS )
        batch_insert (cursor ,"users",["name","email","city","created_at"],user_rows )
        conn .commit ()
    else :
        print (f"  users table already has data — skipping.")

    user_ids =get_ids (cursor ,"users")
    print (f"  users in DB: {len (user_ids ):,}")


    if not table_has_data (cursor ,"products"):
        product_rows =generate_products (NUM_PRODUCTS )
        batch_insert (cursor ,"products",["name","price","category","stock"],product_rows )
        conn .commit ()
    else :
        print (f"  products table already has data — skipping.")

    product_ids =get_ids (cursor ,"products")

    cursor .execute ("SELECT id, price FROM products")
    product_prices ={row [0 ]:float (row [1 ])for row in cursor .fetchall ()}
    print (f"  products in DB: {len (product_ids ):,}")


    if not table_has_data (cursor ,"orders"):
        order_rows =generate_orders (NUM_ORDERS ,user_ids ,product_ids )
        batch_insert (
        cursor ,"orders",
        ["user_id","product_id","quantity","order_date"],
        order_rows ,
        )
        conn .commit ()
    else :
        print (f"  orders table already has data — skipping.")


    cursor .execute ("SELECT id, product_id, quantity, order_date FROM orders")
    order_records =cursor .fetchall ()
    order_ids =[r [0 ]for r in order_records ]
    order_product_ids =[r [1 ]for r in order_records ]
    order_quantities =[r [2 ]for r in order_records ]
    order_dates =[r [3 ]for r in order_records ]
    print (f"  orders in DB: {len (order_ids ):,}")


    if not table_has_data (cursor ,"payments"):
        payment_rows =generate_payments (
        order_ids ,order_product_ids ,product_prices ,order_quantities ,order_dates 
        )
        batch_insert (
        cursor ,"payments",
        ["order_id","amount","status","payment_date"],
        payment_rows ,
        )
        conn .commit ()
    else :
        print (f"  payments table already has data — skipping.")

    cursor .execute ("SELECT COUNT(*) FROM payments")
    print (f"  payments in DB: {cursor .fetchone ()[0 ]:,}")


    if not table_has_data (cursor ,"reviews"):
        review_rows =generate_reviews (NUM_REVIEWS ,product_ids ,user_ids )
        batch_insert (
        cursor ,"reviews",
        ["product_id","user_id","rating","comment"],
        review_rows ,
        )
        conn .commit ()
    else :
        print (f"  reviews table already has data — skipping.")

    cursor .execute ("SELECT COUNT(*) FROM reviews")
    print (f"  reviews in DB: {cursor .fetchone ()[0 ]:,}")


    print ("\n[Step 5] Final row counts:")
    print ("-"*40 )
    for table in ["users","products","orders","payments","reviews"]:
        cursor .execute (f"SELECT COUNT(*) FROM {table }")
        count =cursor .fetchone ()[0 ]
        print (f"  {table :<12} {count :>8,} rows")
    print ("-"*40 )


    print ("\n[Step 6] Verifying FK integrity...")
    cursor .execute ("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN users u    ON o.user_id    = u.id
        LEFT JOIN products p ON o.product_id = p.id
        WHERE u.id IS NULL OR p.id IS NULL
    """)
    orphaned_orders =cursor .fetchone ()[0 ]

    cursor .execute ("""
        SELECT COUNT(*) FROM payments pay
        LEFT JOIN orders o ON pay.order_id = o.id
        WHERE o.id IS NULL
    """)
    orphaned_payments =cursor .fetchone ()[0 ]

    if orphaned_orders ==0 and orphaned_payments ==0 :
        print ("  FK integrity: PASSED (no orphaned records)")
    else :
        print (f"  WARNING: {orphaned_orders } orphaned orders, {orphaned_payments } orphaned payments")

    cursor .close ()
    conn .close ()

    print ("\n"+"="*60 )
    print ("  Setup complete! Database is ready.")
    print ("="*60 )
    print ()
    print ("  Next step: python setup/setup_chromadb.py")
    print ()
    print ("  Don't forget to create the read-only MySQL user:")
    print (f"    CREATE USER 'textsql_reader'@'localhost' IDENTIFIED BY 'your_password';")
    print (f"    GRANT SELECT ON {MYSQL_DATABASE }.* TO 'textsql_reader'@'localhost';")
    print (f"    FLUSH PRIVILEGES;")
    print ()


if __name__ =="__main__":
    parser =argparse .ArgumentParser (
    description ="Set up the Text-to-SQL RAG Assistant database with fake data."
    )
    parser .add_argument (
    "--reset",
    action ="store_true",
    help ="Drop all existing tables and recreate from scratch. WARNING: destroys all data.",
    )
    args =parser .parse_args ()

    if args .reset :
        print ("\nWARNING: --reset will drop all tables and all existing data.")
        confirm =input ("Type 'yes' to confirm: ").strip ().lower ()
        if confirm !="yes":
            print ("Aborted.")
            sys .exit (0 )

    main (reset =args .reset )
