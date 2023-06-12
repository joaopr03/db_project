#!/usr/bin/python3
import os
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://db:db@postgres/db")

pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
log = app.logger




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
                    "label": "New Customer Number:*",
                    "name": "cust_no",
                    "required": True,
                },
                {
                    "label": "New Customer Name:*",
                    "name": "name",
                    "required": True,
                },
                {
                    "label": "New Customer Email:*",
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
    try:
        if not request.form["cust_no"]:
            raise Exception("Customer Number is required.")
        try:
            int(request.form["cust_no"])
        except Exception as e:
            raise Exception("Customer Number must be integer.")
        if not request.form["name"]:
            raise Exception("Name is required.")
        if not request.form["email"]:
            raise Exception("Email is required.")
        
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    INSERT INTO customer (cust_no, name, email) VALUES (%(cust_no)s, %(name)s, %(email)s);
                    """
                if request.form["phone"]:
                    queries += """
                        UPDATE customer SET phone = %(phone)s WHERE cust_no = %(cust_no)s;
                        """
                if request.form["address"]:
                    queries += """
                        UPDATE customer SET address = %(address)s WHERE cust_no = %(cust_no)s;
                        """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"cust_no": request.form["cust_no"],
                            "name": request.form["name"],
                            "email": request.form["email"],
                            "phone": request.form["phone"],
                            "address": request.form["address"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_customer"))
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/customer")
def list_customer():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM customer ORDER BY cust_no;
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("cust_no", "name", "email", "phone", "address")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
                title="Customer",
                row_actions=(
                    {
                        "className": "remove",
                        "link": lambda record: url_for(
                            "list_customer_pending", cust=record[0]
                        ),
                        "name": "Orders",
                    },
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
            )
    except Exception as e:
        return render_template("error_page.html", error=e)


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
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    DELETE FROM process WHERE order_no IN (
                        SELECT order_no FROM process INNER JOIN orders USING(order_no) WHERE cust_no = %(cust_no)s
                    );
                    DELETE FROM contains WHERE order_no IN (
                        SELECT order_no FROM contains INNER JOIN orders USING(order_no) WHERE cust_no = %(cust_no)s
                    );
                    DELETE FROM pay WHERE cust_no = %(cust_no)s;
                    DELETE FROM orders WHERE cust_no = %(cust_no)s;
                    DELETE FROM customer WHERE cust_no = %(cust_no)s;
                    """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"cust_no": request.form["cust_no"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_customer"))
    except Exception as e:
        return render_template("error_page.html", error=e)
    

@app.route("/customer/<string:cust>/orders")
def list_customer_pending(cust):
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT order_no, date FROM orders
                    WHERE cust_no=%(cust_no)s AND order_no NOT IN(
                        SELECT order_no FROM pay WHERE cust_no=%(cust_no)s
                    )
                    ORDER BY date;
                    """,
                    {"cust_no": cust},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("order_no", "date")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
                title=f"Orders to pay from Customer '{cust}'",
                row_actions=(
                    {
                        "className": "remove",
                        "link": lambda record: url_for(
                            "confirm_pay", orders=record[0], customer=cust
                        ),
                        "name": "Pay",
                    },
                ),
            )
    except Exception as e:
        return render_template("error_page.html", error=e)
    
@app.route("/customer/<string:customer>/<string:orders>/pay", methods=["GET"])
def confirm_pay(orders, customer):
    try:
        return render_template(
            "confirm_delete.html",
            action_url=url_for("pay"),
            title=f"Pay '{orders}'?",
            data={"order_no": orders, "cust_no": customer},
        )
    except Exception as e:
        return render_template("error_page.html", error=e)




@app.route("/product/insert", methods=["GET"])
def ask_product():
    try:
        return render_template(
            "ask_input.html",
            action_url=url_for("insert_product"),
            title="Insert Product",
            fields=(
                {
                    "label": "New Product SKU:*",
                    "name": "sku",
                    "required": True,
                },
                {
                    "label": "New Product Name:*",
                    "name": "name",
                    "required": True,
                },
                {
                    "label": "New Product Description:",
                    "name": "description",
                    "required": False,
                },
                {
                    "label": "New Product Price:*",
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
    try:
        if not request.form["sku"]:
            raise Exception("SKU is required.")
        if not request.form["name"]:
            raise Exception("Name is required.")
        if not request.form["price"]:
            raise Exception("Price is required.")
        try:
            float(request.form["price"])
        except Exception as e:
            raise Exception("Price must be numeric.")
        if request.form["ean"]:
            if not request.form["ean"].isdigit() or len(request.form["ean"]) > 13:
                raise Exception("EAN must be numeric and less than 13 digits.")
        
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    INSERT INTO product (sku, name, price) VALUES (%(sku)s, %(name)s, %(price)s);
                    """
                if request.form["description"]:
                    queries += """
                        UPDATE product SET description = %(description)s WHERE sku = %(sku)s;
                        """
                if request.form["ean"]:
                    queries += """
                        UPDATE product SET ean = %(ean)s WHERE sku = %(sku)s;
                        """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"sku": request.form["sku"],
                            "name": request.form["name"],
                            "price": request.form["price"],
                            "description": request.form["description"],
                            "ean": request.form["ean"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_product"))
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/product")
def list_product():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM product ORDER BY sku
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("sku", "name", "description", "price", "ean")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
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
            )
    except Exception as e:
        return render_template("error_page.html", error=e)


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
                    "label": "New Product Price:*",
                    "name": "price",
                    "required": True,
                },
            ),
        )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/product/change", methods=["POST"])
def change_product():
    try:
        if not request.form["price"]:
            raise Exception("Price is required.")
        try:
            float(request.form["price"])
        except Exception as e:
            raise Exception("Price must be numeric.")

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    UPDATE product SET price = %(price)s WHERE sku = %(sku)s;
                    """
                if request.form["description"]:
                    queries += """
                        UPDATE product SET description = %(description)s WHERE sku = %(sku)s;
                        """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"price": request.form["price"],
                            "description": request.form["description"],
                            "sku": request.form["sku"],},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_product"))
    except Exception as e:
        return render_template("error_page.html", error=e)


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
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    DELETE FROM delivery WHERE tin IN (
                        SELECT tin FROM supplier WHERE sku = %(sku)s
                    );
                    DELETE FROM supplier WHERE sku = %(sku)s;
                    DELETE FROM contains WHERE sku = %(sku)s;
                    DELETE FROM process WHERE order_no NOT IN (
                        SELECT order_no FROM contains
                    );
                    DELETE FROM pay WHERE order_no NOT IN (
                        SELECT order_no FROM contains
                    );
                    DELETE FROM orders WHERE order_no NOT IN (
                        SELECT order_no FROM contains
                    );
                    DELETE FROM product WHERE sku = %(sku)s;
                    """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"sku": request.form["sku"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_product"))
    except Exception as e:
        return render_template("error_page.html", error=e)




@app.route("/supplier/insert", methods=["GET"])
def ask_supplier():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT sku FROM product ORDER BY sku;
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        return render_template(
                "ask_input.html",
                action_url=url_for("insert_supplier"),
                title="Insert Supplier",
                fields=(
                    {
                        "label": "New Supplier TIN:*",
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
                        "label": "Product SKU:*",
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
            )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/supplier/insert", methods=["POST"])
def insert_supplier():
    try:
        if not request.form["tin"]:
            raise Exception("TIN is required.")
        if not request.form["sku"]:
            raise Exception("SKU is required.")

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    INSERT INTO supplier (tin, sku) VALUES (%(tin)s, %(sku)s);
                    """
                if request.form["name"]:
                    queries += """
                        UPDATE supplier SET name = %(name)s WHERE tin = %(tin)s;
                        """
                if request.form["address"]:
                    queries += """
                        UPDATE supplier SET address = %(address)s WHERE tin = %(tin)s;
                        """
                if request.form["date"]:
                    queries += """
                        UPDATE supplier SET date = %(date)s WHERE tin = %(tin)s;
                        """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"tin": request.form["tin"],
                            "name": request.form["name"],
                            "sku": request.form["sku"],
                            "address": request.form["address"],
                            "date": request.form["date"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_supplier"))
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/supplier")
def list_supplier():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM supplier ORDER BY tin
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("sku", "name", "description", "price", "ean")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
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
            )
    except Exception as e:
        return render_template("error_page.html", error=e)


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
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                queries = """
                    DELETE FROM delivery WHERE tin = %(tin)s;
                    DELETE FROM supplier WHERE tin = %(tin)s;
                    """
                for query in queries.split(';'):
                    if len(query) > 0:
                        cur.execute(
                            query + ';',
                            {"tin": request.form["tin"]},
                        )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_supplier"))
    except Exception as e:
        return render_template("error_page.html", error=e)




@app.route("/orders/insert", methods=["GET"])
def ask_orders():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT sku, name, price FROM product ORDER BY name, sku;
                    """,
                    {},
                )
                cursor = cur.fetchall()
                cur.execute(
                    """
                    SELECT cust_no FROM customer ORDER BY cust_no;
                    """,
                    {},
                )
                cursor2 = cur.fetchall()
            cur.close()
        conn.close

        fields=(
            {
                "label": "New Order Number:*",
                "name": "order_no",
                "required": True,
            },
            {
                "label": "New Customer Number:*",
                "name": "cust_no",
                "required": True,
                "type": "select",
                "options": ((record[0], record[0]) for record in cursor2),
            },
            {
                "label": "New Date:*",
                "name": "date",
                "required": True,
            },
        )
        for record in cursor:
            fields += (
                {
                    "label": "",
                    "name": "sku",
                    "type": "hidden",
                    "value": record[0],
                },
                {
                    "label": f"{record[1]}, {record[2]}€",
                    "name": f"{record[0]}",
                    "required": False,
                },
            )

        return render_template(
                "ask_input.html",
                action_url=url_for("insert_orders"),
                title="Insert Orders",
                fields=fields,
            )
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/orders/insert",  methods=["GET", "POST"])
def insert_orders():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT sku FROM (
                        SELECT sku, name FROM product ORDER BY name, sku
                    ) as k;
                    """,
                    {},
                )
                skus = cur.fetchall()

        if request.method == "POST":

            if not request.form["order_no"]:
                raise Exception("Order Number is required.")
            try:
                int(request.form["order_no"])
            except Exception as e:
                raise Exception("Order Number must be integer.")
            if not request.form["cust_no"]:
                raise Exception("Customer Number is required.")
            try:
                int(request.form["cust_no"])
            except Exception as e:
                raise Exception("Customer Number must be integer.")
            if not request.form["date"]:
                raise Exception("Date is required.")
            
            aux = False
            for sku in skus:
                qty = request.form[sku[0]]
                if qty:
                    try:
                        int(qty)
                    except Exception as e:
                        raise Exception("Quantity must be integer.%s",sku[0])
                    if int(qty) > 0:
                        aux = True
            if not aux:
                raise Exception("Order must include a product.")


            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    for sku in skus:
                        qty = request.form[sku[0]]
                        if qty:
                            cur.execute(
                                """
                                INSERT INTO contains (order_no, sku, qty) VALUES (%(order_no)s, %(sku)s, %(qty)s);
                                """,
                                {"order_no": request.form["order_no"], "sku": sku[0], "qty": qty},
                            )
                    cur.execute(
                            """
                            INSERT INTO orders (order_no, cust_no, date) VALUES (%(order_no)s, %(cust_no)s, %(date)s);
                            """,
                            {"order_no": request.form["order_no"],
                            "cust_no": request.form["cust_no"],
                            "date": request.form["date"]},
                        )
                    conn.commit()
                cur.close()
            conn.close
            return redirect(url_for("list_orders"))
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/orders")
def list_orders():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM orders ORDER BY order_no
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("order_no", "cust_no", "date")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
                title="Orders",
                page_actions=(
                    {"title": "Insert orders", "link": url_for("ask_orders")},
                ),
            )
    except Exception as e:
        return render_template("error_page.html", error=e)






@app.route("/customer/pay", methods=["POST"])
def pay():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    INSERT INTO pay (order_no, cust_no) VALUES (%(order_no)s, %(cust_no)s);
                    """,
                    {"order_no": request.form["order_no"],
                    "cust_no": request.form["cust_no"]},
                )
                conn.commit()
            cur.close()
        conn.close
        return redirect(url_for("list_customer"))
    except Exception as e:
        return render_template("error_page.html", error=e)


@app.route("/pay")
def list_pay():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM pay ORDER BY order_no
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("order_no", "cust_no")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
                title="Pay",
            )
    except Exception as e:
        return render_template("error_page.html", error=e)
    
@app.route("/contains")
def list_contains():
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM contains ORDER BY order_no
                    """,
                    {},
                )
                cursor = cur.fetchall()
            cur.close()
        conn.close

        colnames = ("order_no", "cust_no","quantity")
        return render_template(
                "query.html",
                cursor=cursor,
                colnames=colnames,
                title="Contains",
            )
    except Exception as e:
        return render_template("error_page.html", error=e)




if __name__ == "__main__":
    app.run()
