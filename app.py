from datetime import timedelta
import time
from flask import Flask, render_template
from flask_login import LoginManager, login_required
from config import Config
from models import db, Owner
from routes.authentication import auth_bp
from routes.shop import shop_bp
from routes.knowledge import knowledge_bp
from routes.customer import customer_bp
from routes.owner import owner_bp

app = Flask(__name__)
app.config.from_object(Config)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=2)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(owner_id):
    return db.session.get(Owner, int(owner_id))


app.register_blueprint(auth_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(owner_bp)


@app.route("/")
@login_required
def home():
    return render_template("index.html")


# Create tables during initial deployment
with app.app_context():
    print("Starting database table check...", flush=True)

    start_time = time.time()

    db.create_all()

    print(
        f"Database tables checked successfully in {time.time() - start_time:.2f} seconds",
        flush=True
    )


if __name__ == "__main__":
    app.run(debug=True)
