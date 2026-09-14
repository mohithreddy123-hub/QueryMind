"""
setup/setup_chromadb.py
========================
Embeds rich schema documentation for all 5 database tables and stores the
resulting vectors in a persistent ChromaDB collection.

This is the heart of the RAG system.

What this script does:
  1. Validates the Gemini API key
  2. Connects to ChromaDB (persistent local storage at ./chroma_db/)
  3. Checks if the collection already exists — skips embedding if it does
     (use --reset to force re-embedding)
  4. For each of the 5 tables, sends its schema document to the Gemini
     embedding model and stores the resulting vector + metadata in ChromaDB

Why rich schema documentation matters:
  A bare column list like "orders: id, user_id, product_id, quantity, order_date"
  does not embed well. When a user asks "which product sold the most?", the
  embedding of that question needs to be semantically similar to the embedding
  of the orders schema document — but "sold the most" and "order_date, quantity"
  share very little semantic overlap at the token level.

  Rich documentation that says "Each row represents a purchase event. Use
  SUM(quantity) grouped by product_id to find sales volume." embeds into a
  vector that IS semantically close to "which product sold the most?", enabling
  correct retrieval.

Usage:
  python setup/setup_chromadb.py            # embed (skips if already done)
  python setup/setup_chromadb.py --reset    # delete collection and re-embed
"""

import sys 
import os 
import argparse 

sys .path .insert (0 ,os .path .join (os .path .dirname (__file__ ),".."))

from google import genai 
import chromadb 

from config .settings import (
GEMINI_API_KEY ,
EMBEDDING_MODEL ,
CHROMA_PERSIST_DIR ,
CHROMA_COLLECTION_NAME ,
)
















SCHEMA_DOCUMENTS ={


"users":{
"document":"""
Table: users

Purpose:
Stores customer account information for the e-commerce platform. Each row
represents one registered customer.

Columns:
  id (INT, PRIMARY KEY, AUTO_INCREMENT):
    Unique identifier for each customer. Referenced as a foreign key by
    orders.user_id and reviews.user_id.

  name (VARCHAR):
    Full name of the customer.

  email (VARCHAR, UNIQUE):
    Email address of the customer. Each customer has a unique email.

  city (VARCHAR):
    The city where the customer is located. Useful for geographic analysis,
    regional sales breakdowns, and identifying which cities have the most
    customers.

  created_at (DATETIME):
    The date and time when the customer registered. Use this column for:
    - Counting new sign-ups in a time period (day, week, month)
    - Tracking customer growth over time
    - Cohort analysis

Primary Key: id
Foreign Keys: None (this is a root/parent table)

Relationships:
  users.id is referenced by orders.user_id
    (one user can place many orders)
  users.id is referenced by reviews.user_id
    (one user can write many reviews)

Business Meaning:
  Each row is a customer. This table answers questions like:
  - How many customers do we have?
  - How many new customers signed up this week/month?
  - Which city has the most customers?
  - Who are our customers?

Query Guidance:
  - Count new users in a period:
      SELECT COUNT(*) FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  - Count sign-ups by city:
      SELECT city, COUNT(*) AS customer_count FROM users GROUP BY city ORDER BY customer_count DESC
  - New sign-ups this week:
      SELECT COUNT(*) FROM users WHERE WEEK(created_at) = WEEK(NOW()) AND YEAR(created_at) = YEAR(NOW())
  - New sign-ups this month:
      SELECT COUNT(*) FROM users WHERE MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())
  - To find customers who placed orders, JOIN with orders on users.id = orders.user_id
  - To find top customers by order count, GROUP BY user_id and COUNT orders
""".strip (),
"metadata":{
"table_name":"users",
"document_type":"schema",
"description":"Customer account information — name, email, city, registration date",
},
},


"products":{
"document":"""
Table: products

Purpose:
Stores the product catalogue for the e-commerce platform. Each row represents
one product available for purchase.

Columns:
  id (INT, PRIMARY KEY, AUTO_INCREMENT):
    Unique identifier for each product. Referenced as a foreign key by
    orders.product_id and reviews.product_id.

  name (VARCHAR):
    The name/title of the product (e.g., "Wireless Bluetooth Headphones",
    "Organic Basmati Rice 5kg"). Use this column in SELECT output and for
    product lookups.

  price (DECIMAL 10,2):
    The selling price of the product in Indian Rupees (INR). Use for revenue
    calculations and price-based filtering. Example: price > 5000 means
    products costing more than 5000 rupees.

  category (VARCHAR):
    The product category. Available categories include: Electronics, Clothing,
    Books, Home & Garden, Sports, Beauty, Food, Toys. Use for category-level
    analysis and filtering.

  stock (INT):
    The current inventory level (number of units available). A value of 0
    means the product is out of stock. Low stock is typically considered
    less than 10 units. Use for inventory management queries.

Primary Key: id
Foreign Keys: None (this is a root/parent table)

Relationships:
  products.id is referenced by orders.product_id
    (a product can appear in many orders)
  products.id is referenced by reviews.product_id
    (a product can have many reviews)

Business Meaning:
  Each row is a product in the store catalogue. This table answers:
  - What products do we sell?
  - Which products are expensive or cheap?
  - Which products are out of stock or running low?
  - What categories do we sell?
  - What is the price of a specific product?

Query Guidance:
  - Products running low on stock (less than 10 units):
      SELECT name, stock, category FROM products WHERE stock < 10 ORDER BY stock ASC
  - Out of stock products:
      SELECT name, category FROM products WHERE stock = 0
  - Products by category:
      SELECT category, COUNT(*) AS product_count FROM products GROUP BY category
  - Most expensive products:
      SELECT name, price, category FROM products ORDER BY price DESC LIMIT 10
  - Revenue potential per product: price * stock
  - To find best-selling products, JOIN with orders on products.id = orders.product_id
    and use SUM(orders.quantity) to get total units sold per product
  - To find highest-rated products, JOIN with reviews on products.id = reviews.product_id
    and use AVG(reviews.rating)
""".strip (),
"metadata":{
"table_name":"products",
"document_type":"schema",
"description":"Product catalogue — name, price, category, stock inventory",
},
},


"orders":{
"document":"""
Table: orders

Purpose:
Stores customer purchase transactions. Each row represents a single product
purchase made by a customer. This is the central fact table for sales analysis.

Columns:
  id (INT, PRIMARY KEY, AUTO_INCREMENT):
    Unique identifier for each order. Referenced as a foreign key by
    payments.order_id.

  user_id (INT, FOREIGN KEY -> users.id):
    The customer who placed the order. Join with the users table to get
    customer name, email, and city.

  product_id (INT, FOREIGN KEY -> products.id):
    The product that was ordered. Join with the products table to get
    product name, price, and category.

  quantity (INT):
    The number of units of the product ordered in this transaction.
    Use SUM(quantity) to get total units sold. Do NOT confuse with COUNT(*),
    which counts number of order rows, not units sold.

  order_date (DATETIME):
    The date and time when the order was placed. Use this for all time-based
    sales analysis: daily, weekly, monthly, yearly trends. All orders are
    within the last 12 months.

Primary Key: id
Foreign Keys:
  user_id REFERENCES users(id)
  product_id REFERENCES products(id)

Relationships:
  orders.id is referenced by payments.order_id
    (each order has one corresponding payment)
  orders.user_id references users.id
  orders.product_id references products.id

Business Meaning:
  Each row is a purchase event: customer X bought Y units of product Z at
  time T. This is the most important table for sales analytics. It answers:
  - Which product sold the most units?
  - How many orders were placed today/this week/this month?
  - What is the total quantity sold for each product?
  - Which customers ordered the most?
  - How many orders did we get yesterday?

Query Guidance:
  - Best-selling product by units sold:
      SELECT p.name, SUM(o.quantity) AS total_units
      FROM orders o JOIN products p ON o.product_id = p.id
      GROUP BY p.id, p.name ORDER BY total_units DESC LIMIT 1
  - Orders placed this month:
      SELECT COUNT(*) FROM orders WHERE MONTH(order_date) = MONTH(NOW()) AND YEAR(order_date) = YEAR(NOW())
  - Orders placed yesterday:
      SELECT COUNT(*) FROM orders WHERE DATE(order_date) = DATE(DATE_SUB(NOW(), INTERVAL 1 DAY))
  - Orders placed this week:
      SELECT COUNT(*) FROM orders WHERE WEEK(order_date) = WEEK(NOW()) AND YEAR(order_date) = YEAR(NOW())
  - Customers with more than 5 orders:
      SELECT u.name, COUNT(o.id) AS order_count
      FROM orders o JOIN users u ON o.user_id = u.id
      GROUP BY u.id, u.name HAVING order_count > 5
  - Average order quantity: SELECT AVG(quantity) FROM orders
  - Sales by category:
      SELECT p.category, SUM(o.quantity) AS units_sold
      FROM orders o JOIN products p ON o.product_id = p.id
      GROUP BY p.category ORDER BY units_sold DESC
  - Use order_date with DATE(), MONTH(), WEEK(), YEAR() MySQL functions for filtering
""".strip (),
"metadata":{
"table_name":"orders",
"document_type":"schema",
"description":"Customer purchase transactions — which customer bought which product, quantity, and date",
},
},


"payments":{
"document":"""
Table: payments

Purpose:
Stores payment records for each order. There is a 1:1 relationship between
orders and payments — every order has exactly one payment record.

Columns:
  id (INT, PRIMARY KEY, AUTO_INCREMENT):
    Unique identifier for each payment record.

  order_id (INT, FOREIGN KEY -> orders.id):
    The order this payment is associated with. Join with orders and products
    to get full transaction details including product name and quantity.

  amount (DECIMAL 10,2):
    The total amount paid or owed for the order, in Indian Rupees (INR).
    This is calculated as: product price × quantity ordered.
    Use SUM(amount) for total revenue calculations.

  status (ENUM: 'paid', 'pending', 'failed'):
    The current payment status:
      'paid'    — payment successfully completed (~70% of records)
      'pending' — payment not yet completed (~20% of records)
      'failed'  — payment failed (~10% of records)
    Always filter by status when calculating revenue: only 'paid' payments
    represent actual revenue received.

  payment_date (DATETIME, nullable):
    The date and time when the payment was completed. This is NULL for
    'pending' and 'failed' payments. Only 'paid' records have a payment_date.

Primary Key: id
Foreign Keys:
  order_id REFERENCES orders(id)

Relationships:
  payments.order_id references orders.id (1:1 relationship)
  To get product details: JOIN payments -> orders -> products
  To get customer details: JOIN payments -> orders -> users

Business Meaning:
  Each row records the financial transaction for one order. This table
  answers revenue and payment questions:
  - What is the total revenue?
  - What payments are still pending?
  - Which payments failed?
  - What is the revenue this month?
  - Show all pending payments above a certain amount

Query Guidance:
  - Total revenue (paid only):
      SELECT SUM(amount) AS total_revenue FROM payments WHERE status = 'paid'
  - Revenue this month (paid only):
      SELECT SUM(amount) FROM payments
      WHERE status = 'paid' AND MONTH(payment_date) = MONTH(NOW()) AND YEAR(payment_date) = YEAR(NOW())
  - Pending payments above 5000 rupees:
      SELECT pay.id, pay.amount, pay.status FROM payments pay WHERE pay.status = 'pending' AND pay.amount > 5000
  - Average order value:
      SELECT AVG(amount) FROM payments WHERE status = 'paid'
  - Revenue by product category:
      SELECT p.category, SUM(pay.amount) AS revenue
      FROM payments pay
      JOIN orders o ON pay.order_id = o.id
      JOIN products p ON o.product_id = p.id
      WHERE pay.status = 'paid'
      GROUP BY p.category ORDER BY revenue DESC
  - IMPORTANT: For true revenue figures, always filter WHERE status = 'paid'
  - pending and failed payments are NOT revenue
  - Use payment_date (not orders.order_date) for payment timing analysis
""".strip (),
"metadata":{
"table_name":"payments",
"document_type":"schema",
"description":"Payment records per order — amount, status (paid/pending/failed), payment date",
},
},


"reviews":{
"document":"""
Table: reviews

Purpose:
Stores customer product reviews and ratings. Each row represents a review
written by a customer for a product they purchased.

Columns:
  id (INT, PRIMARY KEY, AUTO_INCREMENT):
    Unique identifier for each review.

  product_id (INT, FOREIGN KEY -> products.id):
    The product being reviewed. Join with the products table to get the
    product name and category.

  user_id (INT, FOREIGN KEY -> users.id):
    The customer who wrote the review. Join with the users table to get
    the reviewer's name and city.

  rating (TINYINT, values: 1 to 5):
    Numeric star rating given by the customer:
      1 = Very poor / very negative experience
      2 = Poor
      3 = Average / neutral
      4 = Good
      5 = Excellent / very positive experience
    Use AVG(rating) for average rating. Use MIN(rating) for worst rating.
    Ratings are skewed toward higher values (4-5 stars are most common).

  comment (TEXT):
    The written review text left by the customer. Short text comments
    describing the customer's experience with the product.

Primary Key: id
Foreign Keys:
  product_id REFERENCES products(id)
  user_id    REFERENCES users(id)

Relationships:
  reviews.product_id references products.id
    (a product can have many reviews)
  reviews.user_id references users.id
    (a user can write many reviews)

Business Meaning:
  Each row is a customer's opinion of a product. This table answers questions
  about product quality, customer satisfaction, and reputation:
  - Which product has the worst average rating?
  - Which product has the best reviews?
  - What is the average rating for a specific product?
  - What do customers say about a product?
  - Which products have the most reviews?

Query Guidance:
  - Average rating per product (best to worst):
      SELECT p.name, AVG(r.rating) AS avg_rating, COUNT(r.id) AS review_count
      FROM reviews r JOIN products p ON r.product_id = p.id
      GROUP BY p.id, p.name ORDER BY avg_rating ASC
  - Worst-rated product (lowest average rating):
      SELECT p.name, AVG(r.rating) AS avg_rating
      FROM reviews r JOIN products p ON r.product_id = p.id
      GROUP BY p.id, p.name ORDER BY avg_rating ASC LIMIT 1
  - Best-rated product:
      SELECT p.name, AVG(r.rating) AS avg_rating
      FROM reviews r JOIN products p ON r.product_id = p.id
      GROUP BY p.id, p.name ORDER BY avg_rating DESC LIMIT 1
  - Products with only 1-star or 2-star reviews (poor products):
      SELECT p.name, AVG(r.rating) AS avg_rating
      FROM reviews r JOIN products p ON r.product_id = p.id
      GROUP BY p.id, p.name HAVING avg_rating < 3
  - Review count per product (most reviewed):
      SELECT p.name, COUNT(r.id) AS review_count
      FROM reviews r JOIN products p ON r.product_id = p.id
      GROUP BY p.id, p.name ORDER BY review_count DESC
  - Use AVG(rating) for average, MIN(rating) for worst single rating,
    MAX(rating) for best single rating
""".strip (),
"metadata":{
"table_name":"reviews",
"document_type":"schema",
"description":"Customer product reviews — star rating (1-5) and written comments",
},
},
}






def get_embedding (client :genai .Client ,text :str )->list [float ]:
    """
    Generates a vector embedding for the given text using the Gemini
    embedding model configured in settings.py.

    The embedding is a list of floating-point numbers. Texts with similar
    meaning produce vectors that are numerically close (high cosine similarity).

    Args:
        client: Authenticated Gemini API client
        text:   The text to embed (schema document or user question)

    Returns:
        List of floats representing the text in vector space
    """
    result =client .models .embed_content (
    model =EMBEDDING_MODEL ,
    contents =[text ],
    )


    return result .embeddings [0 ].values 






def main (reset :bool =False ):
    print ("="*60 )
    print ("  Text-to-SQL RAG — ChromaDB Schema Setup")
    print ("="*60 )


    if not GEMINI_API_KEY or GEMINI_API_KEY =="your_gemini_api_key_here":
        print ("\n  ERROR: GEMINI_API_KEY is not set in your .env file.")
        print ("  Get your key from: https://aistudio.google.com/app/apikey")
        print ("  Then add it to .env: GEMINI_API_KEY=your_actual_key")
        sys .exit (1 )

    print (f"\n  Embedding model : {EMBEDDING_MODEL }")
    print (f"  ChromaDB path   : {CHROMA_PERSIST_DIR }")
    print (f"  Collection name : {CHROMA_COLLECTION_NAME }")


    print ("\n[Step 1] Connecting to ChromaDB...")
    chroma_client =chromadb .PersistentClient (path =CHROMA_PERSIST_DIR )
    print (f"  ChromaDB connected. Data will persist at: {os .path .abspath (CHROMA_PERSIST_DIR )}")


    if reset :
        print ("\n[Step 2] Deleting existing collection (--reset flag)...")
        try :
            chroma_client .delete_collection (name =CHROMA_COLLECTION_NAME )
            print (f"  Collection '{CHROMA_COLLECTION_NAME }' deleted.")
        except Exception :
            print (f"  Collection did not exist — nothing to delete.")
    else :
        print ("\n[Step 2] Checking for existing collection...")


    try :
        existing =chroma_client .get_collection (name =CHROMA_COLLECTION_NAME )
        count =existing .count ()
        if count >0 and not reset :
            print (f"  Collection '{CHROMA_COLLECTION_NAME }' already has {count } documents.")
            print ("  Skipping re-embedding (embeddings are preserved from last run).")
            print ("  Use --reset to force re-embedding.")
            print ("\n  Setup complete. ChromaDB is ready.")
            return 
    except Exception :
        print ("  No existing collection found — will create fresh.")





    print ("\n[Step 3] Creating ChromaDB collection...")
    collection =chroma_client .get_or_create_collection (
    name =CHROMA_COLLECTION_NAME ,
    metadata ={"hnsw:space":"cosine"},
    )
    print (f"  Collection '{CHROMA_COLLECTION_NAME }' ready.")


    print ("\n[Step 4] Initializing Gemini embedding client...")
    gemini_client =genai .Client (api_key =GEMINI_API_KEY )
    print ("  Gemini client initialized.")


    print (f"\n[Step 5] Embedding {len (SCHEMA_DOCUMENTS )} schema documents...")
    print ("  (Each document is converted to a vector by the Gemini embedding model)")
    print ()

    for table_name ,info in SCHEMA_DOCUMENTS .items ():
        print (f"  [{table_name }]")
        print (f"    Sending schema document to Gemini ({EMBEDDING_MODEL })...",end ="",flush =True )

        embedding =get_embedding (gemini_client ,info ["document"])

        print (f" done. Vector dimension: {len (embedding )}")
        print (f"    Storing in ChromaDB...",end ="",flush =True )

        collection .add (
        documents =[info ["document"]],
        embeddings =[embedding ],
        metadatas =[info ["metadata"]],
        ids =[table_name ],
        )
        print (" done.")
        print ()


    final_count =collection .count ()
    print (f"[Step 6] Verification: {final_count } documents stored in ChromaDB.")

    print ("\n"+"="*60 )
    print ("  ChromaDB setup complete!")
    print ("="*60 )
    print ()
    print ("  What was stored:")
    for table_name in SCHEMA_DOCUMENTS :
        print (f"    - {table_name } schema document (with embedding)")
    print ()
    print ("  Next step: test retrieval with a sample question:")
    print ("    python -c \"")
    print ("      import sys; sys.path.insert(0,'.')")
    print ("      from app.retriever import retrieve_schema")
    print ("      results = retrieve_schema('which product sold the most?')")
    print ("      print([r['table_name'] for r in results])")
    print ("    \"")
    print ()
    print ("  Or run the full app: streamlit run main.py")
    print ()


if __name__ =="__main__":
    parser =argparse .ArgumentParser (
    description ="Embed schema documents into ChromaDB for the Text-to-SQL RAG Assistant."
    )
    parser .add_argument (
    "--reset",
    action ="store_true",
    help ="Delete the existing ChromaDB collection and re-embed all documents.",
    )
    args =parser .parse_args ()

    if args .reset :
        print ("\nWARNING: --reset will delete all existing ChromaDB embeddings.")
        confirm =input ("Type 'yes' to confirm: ").strip ().lower ()
        if confirm !="yes":
            print ("Aborted.")
            sys .exit (0 )

    main (reset =args .reset )
