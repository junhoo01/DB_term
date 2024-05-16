import psycopg2
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)
connect = psycopg2.connect("dbname=term user=postgres password=011026")
cur = connect.cursor()  # create cursor


@app.route('/')
def login():
    return render_template("login.html")


@app.route('/main', methods=['get','post'])
def main():
    if request.method == 'POST':
        sort_by_m = request.form['sort_by_m']
        sort_by_r = request.form['sort_by_r']
        user_id = request.form['user_id']
    else:
        sort_by_m ='rel_date desc'
        sort_by_r = 'rev_time desc'
        user_id = request.args['user_id']

    cur.execute("WITH A as (SELECT mid, round(avg(ratings),1) as rating FROM reviews GROUP BY mid), B as (SELECT title, director, genre, rel_date, id FROM movies) SELECT B.title, A.rating, B.director, B.genre, B.rel_date from B left join A on A.mid = B.id order by {}".format(sort_by_m))
    movies_list = cur.fetchall()
    if sort_by_r != 'follow':
        cur.execute("SELECT ratings, uid, title, review, rev_time, good, bad, movies.id FROM reviews, movies where reviews.mid = movies.id and uid not in ((select id from mal_user)union(SELECT opid as id from ties where id = '{}' and tie = 'mute')) order by {}".format( user_id, sort_by_r))
        reviews_list = cur.fetchall()
    else:

        cur.execute(
            "SELECT * from (SELECT ratings, uid, title, review, rev_time, good, bad, movies.id FROM reviews, movies where reviews.mid = movies.id and uid not in ((select id from mal_user)union(SELECT opid as id from ties where id = '{}' and tie = 'mute')) order by rev_time desc) where uid in (SELECT opid from ties where id = '{}' and tie = 'follow')".format(
                user_id, user_id))
        reviews_list = cur.fetchall()
    return render_template('main.html', movies=movies_list, reviews=reviews_list, user_id=user_id, cur_m = sort_by_m, cur_r = sort_by_r)

@app.route('/movie_info', methods = ['get','post'])
def movie_info():
    movie_name = request.args.get("movie_id")
    user_id = request.args.get("user_id")
    cur.execute("SELECT director, genre, rel_date FROM movies WHERE title = '{}'".format(movie_name))
    movie_info = cur.fetchall()
    cur.execute("select id from movies where title = '{}'".format(movie_name))
    movie_id = cur.fetchone()[0]
    cur.execute("SELECT round(avg(ratings),1) FROM reviews WHERE mid = %s",movie_id)
    avg_rating_tuple = cur.fetchone()
    avg_rating = avg_rating_tuple[0]
    cur.execute("SELECT ratings, uid, review, rev_time, good, bad FROM reviews WHERE mid = '{}' and uid not in ((select id from mal_user)union(SELECT opid as id from ties where id = '{}' and tie = 'mute'))".format(movie_id,user_id))
    review_info = cur.fetchall()
    return render_template("movie_info.html", movie_info=movie_info, review_info=review_info, movie_name=movie_name, avg_rating = avg_rating, user_id = user_id, movie_id = movie_id )

@app.route('/user_info', methods = ['get'])
def user():
    user_id = request.args.get("user_id")
    user2_id = request.args.get("user2_id")
    cur.execute("SELECT ratings, title, review, rev_time, good, bad, reviews.mid FROM reviews JOIN movies ON reviews.mid = movies.id WHERE uid = %s", (user_id,))
    review = cur.fetchall()
    cur.execute("SELECT id FROM ties WHERE opid = %s and tie = 'follow'", (user_id,))
    followers = cur.fetchall()
    cur.execute("SELECT opid, tie FROM ties WHERE id = %s and tie = 'follow'", (user2_id,))
    followed = cur.fetchall()
    cur.execute("SELECT opid FROM ties WHERE id = %s and tie = 'mute'", (user2_id,))
    muted = cur.fetchall()
    cur.execute("SELECT role from users where id = %s",(user2_id,))
    role = cur.fetchone()[0]
    return render_template("user_info.html", reviews = review, user_id = user_id, user2_id = user2_id, followers = followers, followed=followed, muted = muted, role = role)

@app.route('/add_movie', methods = ['post'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        director = request.form['director']
        genre = request.form['genre']
        rel_date = request.form['rel_date']
        user_id = request.form['user_id']
        user2_id = request.form['user2_id']
    cur.execute("SELECT count(*) from movies")
    m_id = cur.fetchone()[0] + 1
    cur.execute("INSERT INTO movies VALUES('{}','{}','{}','{}','{}')".format(m_id, title, director, genre, rel_date))
    return redirect(url_for('main', user_id=user2_id))

@app.route('/register', methods=['post'])
def register():
    id = request.form["id"]
    password = request.form["password"]
    send = request.form["send"]

    if send == "sign up":
        if len(id) < 1 or len(password) < 1:
            return render_template("login.html", invalid1 = True)
        cur.execute("SELECT ID FROM users where ID = '{}';".format(id))
        existing_user = cur.fetchone()
        if  existing_user != None:
            return render_template("login.html", invalid2=True)
        else:
            cur.execute("INSERT INTO users VALUES('{}', '{}','user');".format(id, password))
            return render_template("login.html")
    else:
        cur.execute("SELECT * FROM users WHERE id = '{}' and password = '{}';".format(id, password))
        result = cur.fetchone()

        if result != None:
            return redirect(url_for('main', user_id=id))
        else:
            return render_template("login.html", login_fail=True)

@app.route('/mute', methods = ['post'])
def mute():
    user_id = request.form['user_id']
    user2_id = request.form['user2_id']
    cur.execute("DELETE FROM ties Where id = '{}' and opid = '{}'".format(user2_id, user_id))
    cur.execute("INSERT INTO ties values('{}', '{}', 'mute')".format(user2_id, user_id))
    return redirect(url_for('user', user_id=user_id, user2_id = user2_id))

@app.route('/follow', methods = ['post'])
def follow():
    user_id = request.form['user_id']
    user2_id = request.form['user2_id']
    cur.execute("DELETE FROM ties Where id = '{}' and opid = '{}'".format(user2_id, user_id))
    cur.execute("INSERT INTO ties values('{}', '{}', 'follow')".format(user2_id, user_id))
    return redirect(url_for('user', user_id=user_id, user2_id=user2_id))

@app.route('/undo', methods = ['post'])
def undo():
    user_id = request.form['user_id']
    user2_id = request.form['user2_id']
    cur.execute("DELETE FROM ties Where id = '{}' and opid = '{}'".format(user_id, user2_id))
    return redirect(url_for('user', user_id=user_id, user2_id=user_id))

@app.route('/new_review', methods = ['post'])
def new_review():
    user_id = request.form['user_id']
    movie_id = request.form['movie_id']
    rating = request.form['rating']
    review = request.form['review']
    cur.execute("SELECT title from movies where id = '{}'".format(movie_id))
    movie_name = cur.fetchone()
    cur.execute("Delete From reviews where mid = '{}' and uid ='{}'".format(movie_id,user_id))
    cur.execute("INSERT into reviews values('{}','{}',{},'{}','{}',0, 0)".format(movie_id, user_id, rating, review, datetime.now()))
    return redirect(url_for('movie_info', user_id=user_id, movie_id = movie_name))

@app.route('/like', methods = ['post'])
def like():
    user_id = request.form['user_id']
    user2_id = request.form['user2_id']
    movie_id = request.form['movie_id']
    cur.execute("UPDATE reviews SET good= good + 1 WHERE uid = '{}' and mid ='{}'".format(user_id, movie_id))
    return redirect(url_for('main', user_id=user2_id))

@app.route('/dislike', methods = ['post'])
def dislike():
    user_id = request.form['user_id']
    user2_id = request.form['user2_id']
    movie_id = request.form['movie_id']
    cur.execute("UPDATE reviews SET bad= bad + 1 WHERE uid = '{}' and mid ='{}'".format(user_id, movie_id))
    return redirect(url_for('main', user_id=user2_id))

if __name__ == '__main__':
    app.run()
