#!/usr/bin/python3

from wsgiref.handlers import CGIHandler
from flask import Flask
from flask import render_template, request, redirect, url_for
from urllib.parse import quote, unquote

## Libs postgres
import psycopg2
import psycopg2.extras

app = Flask(__name__)

## SGBD configs
DB_HOST = "db"
DB_USER = "postgres"
DB_DATABASE = "postgres"
DB_PASSWORD = "postgres"
DB_CONNECTION_STRING = "host=%s dbname=%s user=%s password=%s" % (
    DB_HOST,
    DB_DATABASE,
    DB_USER,
    DB_PASSWORD,
)


## Runs the function once the root page is requested.
## The request comes with the folder structure setting ~/web as the root
@app.route("/")
def homepage():
    try:
        return render_template("index.html")
    except Exception as e:
        return render_template("error_page.html", error=e)

@app.route("/customer/insert", methods=["GET"])
def ask_customer():
    try:
        return render_template(
            "ask_input.html",
            action_url=url_for("insert_customer"),
            title="Insert Customer",
            fields=(
                {
                    "label": "New Customer Number:",
                    "name": "cust_no",
                    "required": True,
                },
                {
                    "label": "New Customer Name:",
                    "name": "name",
                    "required": True,
                },
                {
                    "label": "New Customer Email:",
                    "name": "email",
                    "required": True,
                },
                {
                    "label": "New Customer Phone:",
                    "name": "phone",
                    "required": False,
                },
                {
                    "label": "New Customer Address:",
                    "name": "address",
                    "required": False,
                },
            ),
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/customer/insert", methods=["POST"])
def insert_customer():
    query = """
        INSERT INTO customer (cust_no, name, email) VALUES (%s, %s, %s);
        """
    fields = ("cust_no", "name", "email")
    if request.form["phone"]:
        query += """
            UPDATE customer SET phone = %s WHERE cust_no = %s;
            """
        fields += ("phone", "cust_no")
    if request.form["address"]:
        query += """
            UPDATE customer SET address = %s WHERE cust_no = %s;
            """
        fields += ("address", "cust_no")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_customer")),
        data_from_request(fields),
    )



@app.route("/customer")
def list_customer():
    return exec_query(
        """
        SELECT * FROM customer
        """,
        lambda cursor: render_template(
            "query.html",
            cursor=cursor,
            title="Customer",
            row_actions=(
                {
                    "className": "remove",
                    "link": lambda record: url_for(
                        "confirm_delete_customer", customer=record[0]
                    ),
                    "name": "Remove",
                },
            ),
            page_actions=(
                {"title": "Insert Customer", "link": url_for("ask_customer")},
            ),
        ),
    )


@app.route("/customer/<string:customer>/delete", methods=["GET"])
def confirm_delete_customer(customer):
    try:
        return render_template(
            "confirm_delete.html",
            action_url=url_for("delete_customer"),
            title=f"Delete Customer '{customer}'?",
            data={"cust_no": customer},
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/customer/delete", methods=["POST"])
def delete_customer():
    query = """
        DELETE FROM process WHERE order_no IN (
            SELECT order_no FROM process INNER JOIN orders USING(order_no) WHERE cust_no = %s
        );
        DELETE FROM contains WHERE order_no IN (
            SELECT order_no FROM contains INNER JOIN orders USING(order_no) WHERE cust_no = %s
        );
        DELETE FROM pay WHERE cust_no = %s;
        DELETE FROM orders WHERE cust_no = %s;
        DELETE FROM customer WHERE cust_no = %s;
        """
    fields = ("cust_no", "cust_no", "cust_no", "cust_no", "cust_no")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_customer")),
        data_from_request(fields),
    )


@app.route("/product/insert", methods=["GET"])
def ask_product():
    try:
        return render_template(
            "ask_input.html",
            action_url=url_for("insert_product"),
            title="Insert Product",
            fields=(
                {
                    "label": "New Product SKU:",
                    "name": "sku",
                    "required": True,
                },
                {
                    "label": "New Product Name:",
                    "name": "name",
                    "required": True,
                },
                {
                    "label": "New Product Description:",
                    "name": "description",
                    "required": False,
                },
                {
                    "label": "New Product Price:",
                    "name": "price",
                    "required": True,
                },
                {
                    "label": "New Product EAN:",
                    "name": "ean",
                    "required": False,
                },
            ),
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/product/insert", methods=["POST"])
def insert_product():
    query = """
        INSERT INTO product (sku, name, price) VALUES (%s, %s, %s);
        """
    fields = ("sku", "name", "price")
    if request.form["description"]:
        query += """
            UPDATE product SET description = %s WHERE sku = %s;
            """
        fields += ("description", "sku")
    if request.form["ean"]:
        query += """
            UPDATE product SET ean = %s WHERE sku = %s;
            """
        fields += ("ean", "sku")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_product")),
        data_from_request(fields),
    )


@app.route("/product")
def list_product():
    return exec_query(
        """
        SELECT * FROM product
        """,
        lambda cursor: render_template(
            "query.html",
            cursor=cursor,
            title="Product",
            row_actions=(
                {
                    "className": "change",
                    "link": lambda record: url_for(
                        "ask_change_product", product=record[0]
                    ),
                    "name": "Change",
                },
                {
                    "className": "remove",
                    "link": lambda record: url_for(
                        "confirm_delete_product", product=record[0]
                    ),
                    "name": "Remove",
                },
            ),
            page_actions=(
                {"title": "Insert Product", "link": url_for("ask_product")},
            ),
        ),
    )

@app.route("/product/<string:product>/change", methods=["GET"])
def ask_change_product(product):
    try:
        return render_template(
            "ask_input.html",
            action_url=url_for("change_product"),
            title=f"Change Product '{product}'?",
            fields=(
                {
                    "label": "",
                    "name": "sku",
                    "type": "hidden",
                    "value": product,
                },
                {
                    "label": "New Product Description:",
                    "name": "description",
                    "required": False,
                },
                {
                    "label": "New Product Price:",
                    "name": "price",
                    "required": True,
                },
            ),
        )
    except Exception as e:
        return render_template("error_page.html", error=e)
    
@app.route("/product/change", methods=["POST"])
def change_product():
    if request.form["description"]:
        query = """
            UPDATE product SET description = %s, price = %s WHERE sku = %s;
            """
        fields = ("description","price","sku")
    else:
        query = """
            UPDATE product SET price = %s WHERE sku = %s;
            """
        fields = ("price", "sku")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_product")),
        data_from_request(fields),
    )


@app.route("/product/<string:product>/delete", methods=["GET"])
def confirm_delete_product(product):
    try:
        return render_template(
            "confirm_delete.html",
            action_url=url_for("delete_product"),
            title=f"Delete Product '{product}'?",
            data={"sku": product},
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/product/delete", methods=["POST"])
def delete_product():
    query = """
        DELETE FROM delivery WHERE tin IN (
            SELECT tin FROM supplier WHERE sku = %s
        );
        DELETE FROM supplier WHERE sku = %s;
        DELETE FROM contains WHERE sku = %s;
        DELETE FROM process WHERE order_no NOT IN (
            SELECT order_no FROM contains
        );
        DELETE FROM pay WHERE order_no NOT IN (
            SELECT order_no FROM contains
        );
        DELETE FROM orders WHERE order_no NOT IN (
            SELECT order_no FROM contains
        );
        DELETE FROM product WHERE sku = %s;
        """
    fields = ("sku", "sku", "sku", "sku")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_product")),
        data_from_request(fields),
    )


@app.route("/supplier/insert", methods=["GET"])
def ask_supplier():
    return exec_query(
        """
        SELECT sku FROM product
        ORDER BY sku;
        """,
        lambda cursor: render_template(
            "ask_input.html",
            action_url=url_for("insert_supplier"),
            title="Insert Supplier",
            fields=(
                {
                    "label": "New Supplier TIN:",
                    "name": "tin",
                    "required": True,
                },
                {
                    "label": "New Supplier Name:",
                    "name": "name",
                    "required": False,
                },
                {
                    "label": "New Supplier Address:",
                    "name": "address",
                    "required": False,
                },
                {
                    "label": "Product SKU:",
                    "name": "sku",
                    "type": "select",
                    "required": True,
                    "options": ((record[0], record[0]) for record in cursor),
                },
                {
                    "label": "New Supplier Date:",
                    "name": "date",
                    "required": False,
                },
            ),
        ),
    )


@app.route("/supplier/insert", methods=["POST"])
def insert_supplier():
    query = """
        INSERT INTO supplier (tin, sku) VALUES (%s, %s);
        """
    fields = ("tin", "sku")
    if request.form["name"]:
        query += """
            UPDATE supplier SET name = %s WHERE tin = %s;
            """
        fields += ("name", "tin")
    if request.form["address"]:
        query += """
            UPDATE supplier SET address = %s WHERE tin = %s;
            """
        fields += ("address", "tin")
    if request.form["date"]:
        query += """
            UPDATE supplier SET date = %s WHERE tin = %s;
            """
        fields += ("date", "tin")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_supplier")),
        data_from_request(fields),
    )

@app.route("/supplier")
def list_supplier():
    return exec_query(
        """
        SELECT * FROM supplier
        """,
        lambda cursor: render_template(
            "query.html",
            cursor=cursor,
            title="Supplier",
            row_actions=(
                {
                    "className": "remove",
                    "link": lambda record: url_for(
                        "confirm_delete_supplier", supplier=record[0]
                    ),
                    "name": "Remove",
                },
            ),
            page_actions=(
                {"title": "Insert supplier", "link": url_for("ask_supplier")},
            ),
        ),
    )


@app.route("/supplier/<string:supplier>/delete", methods=["GET"])
def confirm_delete_supplier(supplier):
    try:
        return render_template(
            "confirm_delete.html",
            action_url=url_for("delete_supplier"),
            title=f"Delete supplier '{supplier}'?",
            data={"tin": supplier},
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/supplier/delete", methods=["POST"])
def delete_supplier():
    query = """
        DELETE FROM delivery WHERE tin = %s;
        DELETE FROM supplier WHERE tin = %s;
        """
    fields = ("tin", "tin")
    return exec_query(
        query,
        lambda cursor: redirect(url_for("list_supplier")),
        data_from_request(fields),
    )


@app.route("/orders/insert", methods=["GET"])
def ask_orders():
    return exec_query(
        """
        SELECT cust_no FROM customer
        ORDER BY cust_no;
        """,
        lambda cursor: render_template(
            "ask_input.html",
            action_url=url_for("insert_orders"),
            title="Insert Orders",
            fields=(
                {
                    "label": "New Orders Number:",
                    "name": "order_no",
                    "required": True,
                },
                {
                    "label": "Customer Number:",
                    "name": "cust_no",
                    "type": "select",
                    "required": True,
                    "options": ((record[0], record[0]) for record in cursor),
                },
                {
                    "label": "New Orders Date:",
                    "name": "date",
                    "required": False,
                },
                #inserir skus e quantidades não sei como
            ),
        ),
    )


@app.route("/orders/insert", methods=["POST"])
def insert_orders():
    return exec_query(
        """
        INSERT INTO contains (order_no, sku, qty) VALUES (%s, %s, %s);
        INSERT INTO orders (order_no, cust_no, date) VALUES (%s, %s, %s);
        """,
        lambda cursor: redirect(url_for("list_orders")),
        (
            request.form["order_no"],
            request.form["sku"],
            request.form["qty"],
            request.form["order_no"],
            request.form["cust_no"],
            request.form["date"],
        ),
    )


@app.route("/orders")
def list_orders():
    return exec_query(
        """
        SELECT * FROM orders
        """,
        lambda cursor: render_template(
            "query.html",
            cursor=cursor,
            title="Orders",
            row_actions=(
                {
                    "className": "remove",
                    "link": lambda record: url_for(
                        "confirm_pay", orders=record[0]
                    ),
                    "name": "Pay",
                },
            ),
            page_actions=(
                {"title": "Insert orders", "link": url_for("ask_orders")},
            ),
        ),
    )

@app.route("/orders/pay")
def confirm_pay():
    pass

@app.route("/pay")
def list_pay():
    return exec_query(
        """
        SELECT * FROM pay
        """,
        lambda cursor: render_template(
            "query.html",
            cursor=cursor,
            title="Pay",
        ),
    )

###############
#    Utils    #
###############

def exec_query(query, outcome, data=None):
    return exec_queries((query,), lambda cursors: outcome(cursors[0]), (data,))


def exec_queries(queries, outcome, data):
    dbConn = None
    cursor = None
    try:
        dbConn = psycopg2.connect(DB_CONNECTION_STRING)
        cursors = []
        for query, query_data in zip(queries, data):
            cursor = dbConn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query, query_data)
            cursors.append(cursor)
        return outcome(cursors)
    except Exception as e:
        error_messages = {
            "pk_category": "There can't be two categories with the same name.",
            "pk_retailer": "There can't be two retailers with the same TIN.",
            "retailer_name_key": "There can't be two retailers with the same name.", 
            "pk_responsible_for": "An IVM can only be replenished by a single retailer.",
        }

        displayed_error = next(
            (error_messages[key] for key in error_messages.keys() if key in e.pgerror),
            "Something wrong occurred."
        )
        return render_template(
            "error_page.html",
            error=displayed_error + " Please try again."
        )
    finally:
        dbConn.commit()
        for cursor in cursors:
            cursor.close()
        dbConn.close()

def data_from_request(fields):
    return tuple(map(lambda field: request.form[field], fields))

CGIHandler().run(app)
