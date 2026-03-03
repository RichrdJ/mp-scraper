"""Flask web UI - runs on port 7070."""

import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

import db
import telegram_plugin


def create_app() -> Flask:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.getenv("SECRET_KEY", "mp-notifications-changeme")

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        items = db.get_items(limit=25)
        queries = db.get_queries()
        stats = {
            "total_items": db.get_item_count(),
            "total_queries": len(queries),
        }
        return render_template("index.html", items=items, queries=queries, stats=stats)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @app.route("/queries")
    def queries():
        return render_template("queries.html", queries=db.get_queries())

    @app.route("/queries/add", methods=["POST"])
    def add_query():
        url = request.form.get("url", "").strip()
        name = request.form.get("name", "").strip()

        if not url:
            flash("URL is verplicht.", "error")
            return redirect(url_for("queries"))

        if "marktplaats.nl" not in url:
            flash("URL moet van marktplaats.nl zijn.", "error")
            return redirect(url_for("queries"))

        db.add_query(url, name or None)
        flash("Zoekopdracht toegevoegd!", "success")
        return redirect(url_for("queries"))

    @app.route("/queries/remove/<int:query_id>", methods=["POST"])
    def remove_query(query_id):
        db.remove_query(query_id)
        flash("Zoekopdracht verwijderd.", "success")
        return redirect(url_for("queries"))

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    @app.route("/items")
    def items():
        query_id = request.args.get("query_id", type=int)
        all_items = db.get_items(limit=100, query_id=query_id)
        all_queries = db.get_queries()
        return render_template(
            "items.html",
            items=all_items,
            queries=all_queries,
            selected_query=query_id,
        )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        if request.method == "POST":
            db.set_setting("telegram_token", request.form.get("telegram_token", "").strip())
            db.set_setting("telegram_chat_id", request.form.get("telegram_chat_id", "").strip())
            db.set_setting("poll_interval", request.form.get("poll_interval", "60").strip())
            flash("Instellingen opgeslagen.", "success")
            return redirect(url_for("settings"))

        return render_template("settings.html", settings=db.get_all_settings())

    @app.route("/settings/test-telegram", methods=["POST"])
    def test_telegram():
        token = db.get_setting("telegram_token")
        chat_id = db.get_setting("telegram_chat_id")

        if not token or not chat_id:
            return jsonify({"success": False, "message": "Vul eerst token en chat ID in."})

        success, message = telegram_plugin.test_connection(token, chat_id)
        return jsonify({"success": success, "message": message})

    return app
