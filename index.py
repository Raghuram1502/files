import os
from flask import Flask,render_template,redirect,url_for,request,flash,send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import String,Integer,DateTime
from flask_migrate import Migrate
from nanoid import generate
from datetime import datetime,timedelta, timezone
import datetime as d

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','.exe'}

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)

migrate = Migrate(app,db)

app.config["UPLOAD"] = 'uploads/'
app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

db.init_app(app)

class File(db.Model):
    id = mapped_column(Integer,autoincrement=True,primary_key=True)
    filename = mapped_column(String(80),nullable=False)
    nanoid = mapped_column(String(50),unique=True,nullable=False)
    views = mapped_column(Integer,default=0)
    created_time = mapped_column(DateTime,default=datetime.now(d.UTC))
    expire_time = mapped_column(DateTime)

    def has_expired(self):
        return datetime.now(timezone.utc) > self.expire_time

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/upload',methods = ["GET","POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash('There is no file')
            return redirect(url_for("upload"))
    
        file = request.files["file"]

        if file.filename == '':
            flash('No selected file')
            return redirect(url_for("upload"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            nanoid = generate(size=10)
            extension = filename.rsplit(".")[1]
            file.save(os.path.join(f"{app.config['UPLOAD']}/{nanoid}.{extension}"))

            new_file = File(filename=filename,nanoid=nanoid, expire_time=datetime.now() + timedelta(hours=2))
            print("setting expiry ", new_file.expire_time)
            db.session.add(new_file)
            db.session.commit()
            return redirect(f"/{nanoid}")
    return render_template("upload.html")

@app.route('/uploads/<nanoid>')
def uploaded_file(nanoid):
    return send_from_directory(app.config['UPLOAD'],nanoid)

@app.route('/<nanoid>')
def get_file(nanoid):
    file = File.query.filter_by(nanoid=nanoid).first()
    if file is None:
        return redirect(url_for("upload"))
    file.views += 1
    db.session.commit()
    filename = file.filename
    extension = filename.rsplit(".")[1]
    print(str(file.expire_time),str(datetime.now(timezone.utc)))
    #print(exp.timestamp(),curr)
    # exp = datetime.fromtimestamp(exp.timestamp(), tz=timezone.utc)
    print(file.expire_time)

    if datetime.now() > file.expire_time:
        os.remove(f"uploads/{nanoid}.{extension}")
        db.session.delete(file)
        db.session.commit()
        return "Link is Expired"
    return render_template("files.html",file=file,link=f"http://127.0.0.1:5000/uploads/{nanoid}.{extension}")
    