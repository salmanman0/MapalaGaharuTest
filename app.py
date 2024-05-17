import datetime
import hashlib
import jwt
import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, Response, redirect, session, url_for, send_from_directory, make_response
from werkzeug.utils import secure_filename
# from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
# import bcrypt
import json
app = Flask(__name__)
app.secret_key = 'SAMS'
SECRET_KEY = 'SAMS'
# Lokasi untuk menyimpan gambar yang diunggah
UPLOAD_FOLDER = 'static/files/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

################################################################################
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

try:
    # Membuat koneksi ke MongoDB Atlas menggunakan string koneksi
    MONGODB_URI = os.environ.get("MONGODB_URI")
    DB_NAME = os.environ.get("DB_NAME")

    # Batas waktu dalam milidetik
    mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1000)
    db = mongo[DB_NAME]

    mongo.server_info()  # Memicu exception jika tidak bisa terhubung
    print("Koneksi berhasil ke MongoDB Atlas")
except Exception as e:
    print("ERROR - Tidak dapat terhubung ke MongoDB Atlas:", str(e))

################################################################################

################################### FUNCTION ###################################
def check_date_format(date_string, date_format='%Y-%m-%d'):
    try:
        # Attempt to parse the date_string with the given date_format
        parsed_date = datetime.datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        # If parsing fails, the date_string does not match the date_format
        return False

def format_tanggal(tanggal):
    tanggal_objek = datetime.datetime.strptime(tanggal, "%Y-%m-%d")
    tanggal_convert = tanggal_objek.strftime("%d %B %Y")
    return tanggal_convert


def generate_token(username_receive):
    payload = {
        "id": username_receive,
        # Expires in 10 hours
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=60 * 60 * 10),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def handle_successful_login(username_receive):
    token = generate_token(username_receive)
    cookie_data = token.decode('utf-8')
    response = make_response(redirect("/admin"))
    response.set_cookie("mytoken", cookie_data, path="/admin")
    return response


def kondisi_terpenuhi():
    status = db.status.find_one({"stats": "flex"})
    if status is not None:
        return True
    else:
        return False


@app.route("/sign_in", methods=["POST"])
def sign_in():
    # Sign in
    username_receive = request.form["username"]
    password_receive = request.form["password"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.admin.find_one({
        "username": username_receive,
        "password": pw_hash,
    })
    if result:
        return handle_successful_login(username_receive)
    else:
        return jsonify({
            "result": "fail",
            "msg": "We could not find a user with that id/password combination",
        })


@app.route('/sign_out', methods=['GET'])
def sign_out():
    response = make_response(redirect('/super_admin'))
    # Menghapus kunci sesi yang digunakan untuk mengidentifikasi pengguna
    session.pop('username', None)
    response.set_cookie('session', '', expires=0)  # Menghapus cookie sesi
    return response


@app.route("/admin-list")
def admin_list():
    admin_list = list(db.admin.find({}, {"_id": 0}))
    return jsonify({"admin": admin_list})


@app.route("/berita-list")
def berita_list():
    berita_list = list(db.berita.find({}, {"_id": 0}))
    return jsonify({"berita": berita_list})


@app.route("/anggota-list")
def anggota_list():
    anggota_list = list(db.anggota.find({}, {"_id": 0}))
    return jsonify({"anggota": anggota_list})


@app.route("/ongoing-list")
def ongoing_list():
    ongoing_list = list(db.ongoing.find({}, {"_id": 0}))
    return jsonify({"ongoing": ongoing_list})


@app.route("/event-list")
def event_list():
    event_list = list(db.event.find({}, {"_id": 0}))
    return jsonify({"event": event_list})


@app.route("/pendaftaran-list")
def pendaftaran_list():
    pendaftaran_list = list(db.pendaftaran.find({}, {"_id": 0}))
    return jsonify({"pendaftaran": pendaftaran_list})


@app.route("/status", methods=['POST', 'GET'])
def status():
    if request.method == 'POST':
        stat = request.form.get('stats_give')
        update_data = {"stats": stat}
        db.status.update_one(
            {"keterangan": "aktifasi pendaftaran"},
            {"$set": update_data}
        )
        return jsonify({"status": "Data berhasil diperbarui"})
    else:
        x = list(db.status.find({}, {"_id": 0}))
        return jsonify({"status": x})
################################### USER BIASA ############################################


@app.route("/")
def home():
    ongoing_data = list(db.ongoing.find().sort("_id", -1).limit(1))
    ongoing_tanggal = format_tanggal(ongoing_data[0]['tanggal'])
    berita_data = list(db.berita.find())
    anggota_data = db.anggota.estimated_document_count()
    ketua_umum_data = db.anggota.find_one({"status": "Ketua Umum"})
    status = list(db.status.find({}, {"_id": 0}))

    return render_template('L_index.html', ongoing=ongoing_data[0], ongoing_tanggal=ongoing_tanggal, berita=berita_data, anggota=anggota_data, ketua_umum=ketua_umum_data, status=status[0])


@app.route('/super_admin', methods=["GET"])
def login():
    return render_template("login.html")


@app.route('/anggota')
def halamanAnggota():
    status = list(db.status.find({}, {"_id": 0}))
    anggota = list(db.anggota.find({}, {"_id": 0}))
    return render_template("L_anggota.html", status=status[0], anggota = anggota)


@app.route('/pendaftaran')
def pendaftaran():
    if kondisi_terpenuhi():
        return render_template("L_pendaftaran.html")
    else:
        return render_template("404.html")


@app.route('/contact')
def halamanContact():
    status = list(db.status.find({}, {"_id": 0}))
    return render_template("L_contact.html", status=status[0])


@app.route('/ongoing', methods=["GET"])
def halamanOngoing():
    ongoing_data = list(db.ongoing.find().sort("_id", -1).limit(1))
    ongoing_tanggal = format_tanggal(ongoing_data[0]['tanggal'])
    event_data = list(db.event.find())
    status = list(db.status.find({}, {"_id": 0}))
    return render_template('L_ongoing.html', event=event_data, ongoing=ongoing_data[0], ongoing_tanggal=ongoing_tanggal, status=status[0])


@app.route('/berita/<id>/', methods=['GET'])
def halamanBerita(id):
    # Pastikan menggunakan ObjectId untuk mencari berdasarkan ID
    berita_dataID = db.berita.find_one({"_id": ObjectId(id)})
    tanggal = format_tanggal(berita_dataID['tanggal'])
    if not berita_dataID:
        return "Berita tidak ditemukan", 404
    berita_list = list(db.berita.find())
    status = list(db.status.find({}, {"_id": 0}))
    return render_template('L_berita.html', berita=berita_dataID, brt=berita_list, tanggal_berita=tanggal, status=status[0])


@app.route('/tentang', methods=["GET"])
def halamanTentang():
    ketua_umum_data = db.anggota.find_one({"status": "Ketua Umum"})
    bendahara_umum_data = db.anggota.find_one({"status": "Bendahara"})
    sekre1_umum_data = db.anggota.find_one({"status": "Sekretaris 1"})
    sekre2_umum_data = db.anggota.find_one({"status": "Sekretaris 2"})
    koor_sapras = db.anggota.find_one(
        {"status": "Koordinator Divisi Sarana Prasarana"})
    koor_albas = db.anggota.find_one(
        {"status": "Koordinator Divisi Alam Bebas"})
    koor_hid = db.anggota.find_one({"status": "Koordinator Divisi HID"})
    koor_litbang = db.anggota.find_one(
        {"status": "Koordinator Divisi Litbang"})
    anggota = list(db.anggota.find({}, {"_id": 0}))
    status = list(db.status.find({}, {"_id": 0}))
    return render_template('L_tentang.html',
                           ketua=ketua_umum_data,
                           bendahara=bendahara_umum_data,
                           sekre1=sekre1_umum_data,
                           sekre2=sekre2_umum_data,
                           koor_sapras=koor_sapras,
                           koor_albas=koor_albas,
                           koor_hid=koor_hid,
                           koor_litbang=koor_litbang,
                           data=anggota,
                           status=status[0])

############################################ ADMIN ##################################


@app.route('/admin', methods=["GET"])
def dashboard():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        total_anggota_luar_biasa = db.anggota.count_documents({'status': 'Anggota Luar Biasa'})
        total_anggota = db.anggota.estimated_document_count()
        total_pengurus = total_anggota - total_anggota_luar_biasa
        dashboard_data = list(db.anggota.find())
        ketua_umum_data = db.anggota.find_one({"status": "Ketua Umum"})
        status = list(db.status.find())
        if status[0]['stats'] == 'flex' :
            status = 'checked'
        else : 
            status = ''
        return render_template('index.html',
                               data=dashboard_data,
                               anggota=total_anggota,
                               pengurus = total_pengurus,
                               anggota_luar_biasa=total_anggota_luar_biasa,
                               ketua=ketua_umum_data,
                               user=user_info, status=status)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

##############################################################  ANGGOTA  ##############################################################

# Menambahkan data


@app.route('/anggota/create', methods=["POST"])
def create_anggota():
    namaLengkap = request.form.get("namaLengkap")
    id_anggota = request.form.get("id_anggota")
    status = request.form.get("status")
    generasi = request.form.get("generasi")
    tanggal = request.form.get("tanggal")
    tanggal = format_tanggal(tanggal)
    gambar_anggota = request.files.get("gambar")

    gambar = None
    if gambar_anggota:
        filename = secure_filename(gambar_anggota.filename)
        gambar = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gambar_anggota.save(gambar)

    anggota_data = {
        "namaLengkap": namaLengkap,
        "id_anggota": id_anggota,
        "status": status,
        "generasi": generasi,
        "gambar": gambar,
        "tanggal": tanggal
    }
    daftar = db.anggota.insert_one(anggota_data)
    if daftar.inserted_id:
        return redirect(url_for('dashboard', status="success"))
    else:
        return redirect(url_for('dashboard', status="danger"))

# Hapus Data


@app.route('/anggota/delete/<string:id>', methods=['POST', 'GET'])
def delete_anggota(id):
    try:
        object_id = ObjectId(id)
        result = db.anggota.delete_one({"_id": object_id})
        if result.deleted_count > 0:
            return redirect(url_for('dashboard', status='success'))
        else:
            # Jika ID tidak ditemukan
            return f"No document found with ID: {id}", 404
    except Exception as e:
        # Jika terjadi error selama penghapusan
        return redirect(url_for('dashboard', status='danger'))


# Update Data


@app.route('/anggota/update', methods=['POST'])
def update_anggota():
    id_data = request.form['id']  # ID dokumen di MongoDB
    object_id = ObjectId(id_data)
    namaLengkap = request.form['namaLengkap']
    id_anggota = request.form['id_anggota']
    status = request.form['status']
    generasi = request.form['generasi']
    tanggal = request.form['tanggal']
    gambar_anggota = request.files.get("gambar")
    gambar = None
    if gambar_anggota is not None and gambar_anggota.filename != '':
        filename = secure_filename(gambar_anggota.filename)
        gambar = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gambar_anggota.save(gambar)
    else:
        data = db.anggota.find_one({"_id": object_id})
        gambar = data.get("gambar", None)
        if gambar:
            # Lakukan sesuatu dengan nilai gambar
            gambar = gambar
        else:
            gambar = "static/files/defaultuser.webp"
    update_data = {
        "namaLengkap": namaLengkap,
        "id_anggota": id_anggota,
        "status": status,
        "generasi": generasi,
        "tanggal": tanggal,
        "gambar": gambar
    }
    print(gambar)
    try:
        db.anggota.update_one(
            {"_id": object_id},  # Kriteria dokumen yang akan diupdate
            {"$set": update_data}  # Update field
        )
        return redirect(url_for('dashboard', status='success'))
    except Exception as e:
        return redirect(url_for('dashboard', status='danger'))
##############################################################  ANGGOTA  ##############################################################

##############################################################  BERITA  ##############################################################


@app.route('/admin/berita', methods=["GET"])
def berita():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        berita_data = list(db.berita.find())
        return render_template('berita.html', data=berita_data, user=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

# Tambah Berita


@app.route("/berita/create", methods=["POST"])
def create_berita():
    judul = request.form.get("judul")
    penanggung_jawab = request.form.get("penanggung_jawab")
    penulis = request.form.get("penulis")
    deskripsi = request.form.get("deskripsi")
    tanggal = request.form.get("tanggal")
    konten = request.form.get("konten")

    # Simpan gambar pameran dan gambar konten, jika ada
    gambar_pameran = request.files.get("gambarPameran")
    gambar_konten = request.files.get("gambarKonten")

    gp = None
    if gambar_pameran:
        filename = secure_filename(gambar_pameran.filename)
        gp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gambar_pameran.save(gp)

    gk = None
    if gambar_konten:
        filename = secure_filename(gambar_konten.filename)
        gk = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gambar_konten.save(gk)

    # Simpan data ke MongoDB
    berita_data = {
        "judul": judul,
        "deskripsi": deskripsi,
        "tanggal": tanggal,
        "penanggung_jawab": penanggung_jawab,
        "penulis": penulis,
        "konten": konten,
        "gambarPameran": gp,
        "gambarKonten": gk
    }
    # Menyimpan data ke koleksi 'berita'
    daftar = db.berita.insert_one(berita_data)
    if daftar.inserted_id:
        return redirect(url_for('berita', status="success"))
    else:
        return redirect(url_for('berita', status="danger"))


@app.route("/files/<filename>")
def display_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Hapus Berita


@app.route('/berita/delete/<string:id>', methods=['POST', 'GET'], endpoint='delete_berita')
def delete_berita(id):
    try:
        object_id = ObjectId(id)
        doc = db.berita.find_one({"_id": object_id})
        if not doc:
            return f"No document found with ID: {id}", 404
        db.berita.delete_one({"_id": object_id})
        return redirect(url_for('berita', status='success'))
    except Exception as e:
        return redirect(url_for('berita', status='danger'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/berita/update', methods=['POST'])
def update_berita():
    # Mengambil data dari formulir POST
    id_data = request.form['id']  # ID dokumen di MongoDB
    object_id = ObjectId(id_data)
    judul = request.form['judul']
    penanggung_jawab = request.form['penanggung_jawab']
    penulis = request.form['penulis']
    deskripsi = request.form['deskripsi']
    tanggal = request.form['tanggal']
    gambarPameran = request.files.get('gambarPameran')
    konten = request.form['konten']
    gambarKonten = request.files.get('gambarKonten')

    gambar_pameran_path = None
    gambar_konten_path = None

    if gambarPameran is not None and allowed_file(gambarPameran.filename) and gambarPameran.filename != '' and gambarPameran.content_length > 0:
        filename_pameran = secure_filename(gambarPameran.filename)
        file_path_pameran = os.path.join(
            app.config['UPLOAD_FOLDER'], filename_pameran)
        gambarPameran.save(file_path_pameran)
        gambar_pameran_path = file_path_pameran
    else:
        data = db.berita.find_one({"_id": object_id})
        gambar_pameran_path = data.get("gambarPameran", None)
        if gambar_pameran_path:
            gambar_pameran_path = gambar_pameran_path
        else:
            gambar_pameran_path = "static/files/defaultuser.webp"

    if gambarKonten and allowed_file(gambarKonten.filename) and gambarKonten.filename != '' and gambarKonten.content_length > 0:
        filename_konten = secure_filename(gambarKonten.filename)
        file_path_konten = os.path.join(
            app.config['UPLOAD_FOLDER'], filename_konten)
        gambarKonten.save(file_path_konten)
        gambar_konten_path = file_path_konten
    else:
        data2 = db.berita.find_one({"_id": object_id})
        gambar_konten_path = data2.get("gambarKonten", None)
        if gambar_konten_path:
            gambar_konten_path = gambar_konten_path
        else:
            gambar_konten_path = "static/files/defaultImage.webp"
    try:
        # Update data di MongoDB
        update_data = {
            "judul": judul,
            "deskripsi": deskripsi,
            "tanggal": tanggal,
            "penanggung_jawab": penanggung_jawab,
            "penulis": penulis,
            "konten": konten,
            "gambarPameran": gambar_pameran_path,
            "gambarKonten": gambar_konten_path
        }

        # Melakukan update pada dokumen dengan ID tertentu
        db.berita.update_one(
            {"_id": object_id},  # Kriteria dokumen yang akan diupdate
            {"$set": update_data}  # Update field
        )
        return redirect(url_for('berita', status='success'))
    except Exception as e:
        return redirect(url_for('berita', status='danger'))

##############################################################  BERITA  ##############################################################

##############################################################  EVENT  ##############################################################


@app.route('/admin/event', methods=["GET"])
def event():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        event_data = list(db.event.find())
        return render_template('event.html', title="event", data=event_data, user=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

# Tambah event


@app.route("/event/create", methods=["POST"])
def create_event():
    judul = request.form.get("judul")
    deskripsi = request.form.get("deskripsi")
    konten = request.form.get("konten")
    tanggal = request.form.get("tanggal")
    gambar_event = request.files.get("gambar")

    gambar = None
    if gambar_event:
        filename = secure_filename(gambar_event.filename)
        gambar = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gambar_event.save(gambar)

    # Simpan data ke MongoDB
    event_data = {
        "judul": judul,
        "deskripsi": deskripsi,
        "konten": konten,
        "tanggal": tanggal,
        "gambar": gambar
    }
    daftar = db.event.insert_one(event_data)
    if daftar.inserted_id:
        return redirect(url_for('event', status="success"))
    else:
        return redirect(url_for('event', status="danger"))

# Hapus event


@app.route('/event/delete/<string:id>', methods=['POST', 'GET'], endpoint='delete_event')
def delete_event(id):
    try:
        object_id = ObjectId(id)
        doc = db.event.find_one({"_id": object_id})
        if not doc:
            return f"No document found with ID: {id}", 404

        db.event.delete_one({"_id": object_id})
        return redirect(url_for('event', status='success'))
    except Exception as e:
        return redirect(url_for('event', status='danger'))

# Update Event


@app.route('/event/update', methods=['POST'])
def update_event():
    id_data = request.form['id']  # ID dokumen di MongoDB
    object_id = ObjectId(id_data)
    judul = request.form['judul']
    tanggal = request.form['tanggal']
    deskripsi = request.form['deskripsi']
    gambar = request.files.get('gambar')
    konten = request.form['konten']

    gambar_path = None
    if gambar is not None and allowed_file(gambar.filename) and gambar.filename != '' and gambar.content_length > 0:
        filename_gambar = secure_filename(gambar.filename)
        file_path_gambar = os.path.join(
            app.config['UPLOAD_FOLDER'], filename_gambar)
        gambar.save(file_path_gambar)
        gambar_path = file_path_gambar
    else:
        data = db.event.find_one({"_id": object_id})
        gambar_path = data.get("gambar", None)
        if gambar_path:
            gambar_path = gambar_path
        else:
            gambar_path = "static/files/defaultuser.webp"
    try:
        # Update data di MongoDB
        update_data = {
            "judul": judul,
            "tanggal": tanggal,
            "deskripsi": deskripsi,
            "konten": konten,
            "gambar": gambar_path
        }
        db.event.update_one(
            {"_id": object_id},  # Kriteria dokumen yang akan diupdate
            {"$set": update_data}  # Update field
        )
        return redirect(url_for('event', status='success'))

    except Exception as e:
        return redirect(url_for('event', status='danger'))
##############################################################  EVENT  ##############################################################

##############################################################  ON GOING  ##############################################################


@app.route('/admin/ongoing-admin', methods=["GET"])
def ongoing():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        ongoing_data = list(db.ongoing.find())
        return render_template('ongoing.html', title="ongoing", data=ongoing_data, user=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

# Tambah onGoing


@app.route("/ongoing/create", methods=["POST"])
def create_ongoing():
    judul = request.form.get("judul")
    deskripsi = request.form.get("deskripsi")
    tanggal = request.form.get("tanggal")
    konten = request.form.get("konten")

    # Simpan gambar pameran dan gambar konten, jika ada
    poster_gambar = request.files.get("posterGambar")
    pg = None
    if poster_gambar:
        filename = secure_filename(poster_gambar.filename)
        pg = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        poster_gambar.save(pg)
    # Simpan data ke MongoDB
    berita_data = {
        "judul": judul,
        "deskripsi": deskripsi,
        "tanggal": tanggal,
        "konten": konten,
        "posterGambar": pg
    }
    daftar = db.ongoing.insert_one(berita_data)
    if daftar.inserted_id:
        return redirect(url_for('ongoing', status="success"))
    else:
        return redirect(url_for('ongoing', status="danger"))

# Hapus OnGoing


@app.route('/ongoing/delete/<string:id>', methods=['POST', 'GET'], endpoint='delete_ongoing')
def delete_ongoing(id):
    try:
        object_id = ObjectId(id)
        doc = db.ongoing.find_one({"_id": object_id})
        if not doc:
            return f"No document found with ID: {id}", 404

        db.ongoing.delete_one({"_id": object_id})
        return redirect(url_for('ongoing', status='success'))
    except Exception as e:
        return redirect(url_for('ongoing', status='danger'))


@app.route('/ongoing/update', methods=['POST'])
def update_ongoing():
    id_data = request.form['id']  # ID dokumen di MongoDB
    object_id = ObjectId(id_data)
    judul = request.form['judul']
    deskripsi = request.form['deskripsi']
    tanggal = request.form['tanggal']
    posterGambar = request.files.get('posterGambar')
    konten = request.form['konten']

    poster_gambar_path = None
    if posterGambar and allowed_file(posterGambar.filename) and posterGambar.filename != '' and posterGambar.content_length > 0:
        filename_poster = secure_filename(posterGambar.filename)
        file_path_poster = os.path.join(
            app.config['UPLOAD_FOLDER'], filename_poster)
        posterGambar.save(file_path_poster)
        poster_gambar_path = file_path_poster
    else:
        data = db.ongoing.find_one({"_id": object_id})
        poster_gambar_path = data.get("posterGambar", None)
        if poster_gambar_path:
            poster_gambar_path = poster_gambar_path
        else:
            poster_gambar_path = "static/files/defaultImage.webp"

    try:
        # Update data di MongoDB
        update_data = {
            "judul": judul,
            "deskripsi": deskripsi,
            "tanggal": tanggal,
            "konten": konten,
            "posterGambar": poster_gambar_path,
        }
        db.ongoing.update_one(
            {"_id": object_id},  # Kriteria dokumen yang akan diupdate
            {"$set": update_data}  # Update field
        )
        return redirect(url_for('ongoing', status='success'))

    except Exception as e:
        return redirect(url_for('ongoing', status='danger'))
##############################################################  ON GOING  ##############################################################


@app.route('/admin/profile')
def profile():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        tanggal = format_tanggal(user_info['tanggalBertugas'])
        return render_template('profile.html', user=user_info, tanggalBertugas = tanggal)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

##############################################################  ADMIN  ##############################################################


@app.route('/admin/anggota', methods=["GET"])
def admin():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        admin_data = list(db.admin.find())
        return render_template('admin.html', title="Admin", data=admin_data, user=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

# Menambahkan data


@app.route('/admin/create', methods=["POST"])
def create_admin():
    try:
        password=request.form["password"],
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        admin = {
            "namaLengkap": request.form["namaLengkap"],
            "username": request.form["username"],
            "tanggalBertugas": request.form["tanggalBertugas"],
            "email": request.form["email"],
            "password": password_hash
        }
        db.admin.insert_one(admin)
        return redirect(url_for('admin', status='success'))
    except Exception as ex:
        return redirect(url_for('admin', status='danger'))

# Mengubah data


@app.route('/admin/update', methods=['POST'])
def update_admin():
    id_data = request.form['id']  # ID dokumen di MongoDB
    namaLengkap = request.form['namaLengkap']
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    tanggalBertugas = request.form['tanggalBertugas']

    try:
        # Konversi ID menjadi ObjectId untuk MongoDB
        object_id = ObjectId(id_data)

        # Melakukan update pada dokumen dengan ID tertentu
        db.admin.update_one(
            {"_id": object_id},  # Kriteria dokumen yang akan diupdate
            {"$set":
                {
                    "namaLengkap": namaLengkap,
                    "email": email,
                    "username": username,
                    "password": password_hash,
                    "tanggalBertugas": tanggalBertugas
                }
             }  # Update field
        )
        return redirect(url_for('admin', status='success'))

    except Exception as e:
        return redirect(url_for('admin', status='danger'))

# Menghapus data


@app.route('/admin/delete/<string:id>', methods=['POST', 'GET'])
def delete(id):
    try:
        # Konversi string ID menjadi ObjectId MongoDB
        object_id = ObjectId(id)
        # Menghapus dokumen dengan ID yang sesuai
        db.admin.delete_one({"_id": object_id})
        return redirect(url_for('admin', status='success'))
    except Exception as e:
        return redirect(url_for('admin', status='danger'))
##############################################################  ADMIN  ##############################################################


@app.route('/admin/pendaftar')
def pendaftar():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.admin.find_one({"username": payload.get("id")})
        pendaftaran_data = list(db.pendaftaran.find())
        return render_template('pendaftaran.html', title="Pendaftaran", data=pendaftaran_data, user=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))


@app.route('/create-pendaftaran', methods=['POST'])
def create_pendaftaran():
    email = request.form.get('email')
    jenisKelamin = request.form.get('jenisKelamin')
    nama = request.form.get('nama')
    nim = request.form.get('nim')
    kelas = request.form.get('kelas')
    programStudi = request.form.get('programStudi')
    pengalamanOrganisasi = request.form.get('pengalamanOrganisasi')
    tujuanMasuk = request.form.get('tujuanMasuk')
    tanggal = datetime.datetime.now()
    tanggal = tanggal.strftime("%d %B %Y")

    data = {
        "email": email,
        "jenisKelamin": jenisKelamin,
        "nama": nama,
        "nim": nim,
        "kelas": kelas,
        "programStudi": programStudi,
        "pengalamanOrganisasi": pengalamanOrganisasi,
        "tujuanMasuk": tujuanMasuk,
        "tanggalDaftar": tanggal
    }
    daftar = db.pendaftaran.insert_one(data)
    if daftar.inserted_id:
        return redirect(url_for('pendaftaran', status="success"))
    else:
        return redirect(url_for('pendaftaran', status="warning"))


@app.route('/update-pendaftaran', methods=['POST'])
def update_pendaftaran():
    id_data = request.form['id']
    email = request.form.get('email')
    jenisKelamin = request.form.get('jenisKelamin')
    nama = request.form.get('nama')
    nim = request.form.get('nim')
    kelas = request.form.get('kelas')
    programStudi = request.form.get('programStudi')
    pengalamanOrganisasi = request.form.get('pengalamanOrganisasi')
    tujuanMasuk = request.form.get('tujuanMasuk')
    object_id = ObjectId(id_data)
    data = {
        "email": email,
        "jenisKelamin": jenisKelamin,
        "nama": nama,
        "nim": nim,
        "kelas": kelas,
        "programStudi": programStudi,
        "pengalamanOrganisasi": pengalamanOrganisasi,
        "tujuanMasuk": tujuanMasuk,
    }
    daftar = db.pendaftaran.update_one({"_id": object_id}, {"$set": data})
    if daftar.modified_count == 1:
        return redirect(url_for('pendaftar', status="success"))
    else:
        return redirect(url_for('pendaftar', status="danger"))


@app.route('/delete-pendaftaran/<string:id>', methods=['POST', 'GET'])
def delete_pendaftaran(id):
    try:
        # Konversi string ID menjadi ObjectId MongoDB
        object_id = ObjectId(id)
        # Menghapus dokumen dengan ID yang sesuai
        db.pendaftaran.delete_one({"_id": object_id})
        return redirect(url_for('pendaftar', status="success"))
    except Exception as e:
        return redirect(url_for('pendaftar', status="danger"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
