from flask import Flask, render_template, request, redirect, session
import psycopg2
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

# Database connection function
def get_connection():
    return psycopg2.connect(
        dbname="shelfwise_db",
        user="srisaivarunbondalapati",
        password="default",
        host="localhost"
    )

@app.context_processor
def inject_banner():
    return dict(show_banner=('username' in session))

@app.route('/')
def index():
    if 'username' in session:
        return redirect('/dashboard')
    return render_template('index.html')

@app.route('/signup_librarian', methods=['GET', 'POST'])
def signup_librarian():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO Librarians (Username, Password) VALUES (%s, %s)", (username, password))
            conn.commit()
            cur.close()
            conn.close()
            return redirect('/login_librarian')
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return render_template('signup_librarian.html', message=f"Error: {e}")
    return render_template('signup_librarian.html', message=None)

@app.route('/signup_member', methods=['GET', 'POST'])
def signup_member():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO LibraryMembers (Username, Password) VALUES (%s, %s)", (username, password))
            conn.commit()
            cur.close()
            conn.close()
            return redirect('/login_member')
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return render_template('signup_member.html', message=f"Error: {e}")
    return render_template('signup_member.html', message=None)

@app.route('/login_librarian', methods=['GET', 'POST'])
def login_librarian():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT Password FROM Librarians WHERE Username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and user[0] == password:
            session['username'] = username
            session['role'] = 'librarian'
            return redirect('/dashboard')
        else:
            return render_template('login_librarian.html', message="Invalid credentials")
    return render_template('login_librarian.html', message=None)

@app.route('/login_member', methods=['GET', 'POST'])
def login_member():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT Password FROM LibraryMembers WHERE Username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and user[0] == password:
            session['username'] = username
            session['role'] = 'member'
            return redirect('/dashboard')
        else:
            return render_template('login_member.html', message="Invalid credentials")
    return render_template('login_member.html', message=None)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    return render_template('dashboard.html', username=session['username'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'username' not in session or session['role'] != 'librarian':
        return redirect('/')
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        genre = request.form['genre']
        copies = request.form['copies']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Books (Title, Author, ISBN, Genre, AvailableCopies) 
            VALUES (%s, %s, %s, %s, %s)
        """, (title, author, isbn, genre, copies))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/view_books')
    return render_template('add_book.html')

@app.route('/view_books', methods=['GET', 'POST'])
def view_books():
    if 'username' not in session:
        return redirect('/')
    search_query = request.form.get('search') if request.method == 'POST' else None
    conn = get_connection()
    cur = conn.cursor()
    if search_query:
        cur.execute("""
            SELECT * FROM Books 
            WHERE Title ILIKE %s OR Author ILIKE %s OR Genre ILIKE %s
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cur.execute("SELECT * FROM Books")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_books.html', books=books, search_query=search_query)

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'username' not in session or session['role'] != 'librarian':
        return redirect('/')
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        genre = request.form['genre']
        copies = request.form['copies']
        cur.execute("""
            UPDATE Books 
            SET Title = %s, Author = %s, ISBN = %s, Genre = %s, AvailableCopies = %s 
            WHERE BookID = %s
        """, (title, author, isbn, genre, copies, book_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/view_books')
    cur.execute("SELECT * FROM Books WHERE BookID = %s", (book_id,))
    book = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    if 'username' not in session or session['role'] != 'librarian':
        return redirect('/')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM Books WHERE BookID = %s", (book_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/view_books')

@app.route('/borrow_book/<int:book_id>')
def borrow_book(book_id):
    if 'username' not in session or session['role'] != 'member':
        return redirect('/')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Transactions (Username, BookID) 
        VALUES (%s, %s)
    """, (session['username'], book_id))
    cur.execute("""
        UPDATE Books 
        SET AvailableCopies = AvailableCopies - 1 
        WHERE BookID = %s
    """, (book_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/view_books')

@app.route('/return_book/<int:book_id>')
def return_book(book_id):
    if 'username' not in session or session['role'] != 'member':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT BorrowDate 
        FROM Transactions 
        WHERE BookID = %s AND Username = %s AND ReturnDate IS NULL
    """, (book_id, session['username']))
    borrow_record = cur.fetchone()

    if borrow_record:
        borrow_date = borrow_record[0]
        today = datetime.now()
        days_borrowed = (today - borrow_date).days

        fine = 0.00
        if days_borrowed > 7:
            fine = (days_borrowed - 7) * 1.00

        cur.execute("""
            UPDATE Transactions 
            SET ReturnDate = %s, FineAmount = %s
            WHERE BookID = %s AND Username = %s AND ReturnDate IS NULL
        """, (today, fine, book_id, session['username']))

        cur.execute("""
            UPDATE Books 
            SET AvailableCopies = AvailableCopies + 1 
            WHERE BookID = %s
        """, (book_id,))

        conn.commit()

    cur.close()
    conn.close()
    return redirect('/my_transactions')

@app.route('/my_transactions')
def my_transactions():
    if 'username' not in session or session['role'] != 'member':
        return redirect('/')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.BookID, b.Title, t.BorrowDate, t.ReturnDate, t.FineAmount
        FROM Transactions t 
        JOIN Books b ON t.BookID = b.BookID
        WHERE t.Username = %s
        ORDER BY t.BorrowDate DESC
    """, (session['username'],))
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_transactions.html', transactions=transactions)

@app.route('/all_transactions')
def all_transactions():
    if 'username' not in session or session['role'] != 'librarian':
        return redirect('/')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.TransactionID, t.Username, b.Title, t.BorrowDate, t.ReturnDate, t.FineAmount
        FROM Transactions t
        JOIN Books b ON t.BookID = b.BookID
        ORDER BY t.BorrowDate DESC
    """)
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('all_transactions.html', transactions=transactions)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
