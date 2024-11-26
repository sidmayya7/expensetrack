from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="SIDMAYYA7",
        database="expensetrack"
    )

# Signup endpoint
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.callproc('InsertNewUser', [username, password])
            db.commit()
            flash('Signup successful! Please log in.')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err.msg}")
        finally:
            cursor.close()
            db.close()
    return render_template('signup.html')

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(type(username),type(password))
        
        db = get_db_connection()
        cursor = db.cursor()

        try:
            # Step 1: Initialize the session variable in MySQL for capturing the OUT parameter
            cursor.execute("SET @p_valid = 0;")

            # Step 2: Call the stored procedure using the session variable as the OUT parameter
            #cursor.callproc('VerifyUser', [username, password, "@p_valid"])
            cursor.execute("CALL VerifyUser(%s, %s, @p_valid)", (username, password))

            # Step 3: Retrieve the value of the session variable @p_valid to check if login is valid
            cursor.execute("SELECT @p_valid;")
            is_valid = cursor.fetchone()[0]  # Get the value from the result
            print(is_valid)

            # Step 4: Check if login is valid (1) or invalid (0)
            if is_valid == 1:
                session['username'] = username
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password')
        finally:
            cursor.close()
            db.close()
    return render_template('login.html')




# Default route redirects to login
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get limits from query parameters or use defaults
    income_limit = request.args.get('income_limit', 5, type=int)
    expense_limit = request.args.get('expense_limit', 5, type=int)
    
    # db = get_db_connection()
    # cursor = db.cursor(dictionary=True)
    
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        #fetch accounts
        cursor.execute("""
            SELECT account_id, account_name 
            FROM Account 
            WHERE Username = %s
        """, (session['username'],))
        accounts = cursor.fetchall()


        
        # Fetch categories
        cursor.execute("SELECT category_id, category_name FROM Category WHERE Username = %s", 
                      (session['username'],))
        categories = cursor.fetchall()
        
        # Fetch recent incomes
        cursor.execute("""
            SELECT 
                i.income_id,
                i.amount,
                DATE_FORMAT(i.date, '%Y-%m-%dT%H:%i') as date,
                a.account_name,
                a.account_id
            FROM Income i
            JOIN Account a ON i.account_id = a.account_id
            WHERE i.Username = %s
            ORDER BY i.date DESC
            LIMIT %s
        """, (session['username'], income_limit))
        
        incomes = cursor.fetchall()
        
        # Fetch recent expenses
        cursor.execute("""
        SELECT 
            e.expense_id,
            e.amount,
            DATE_FORMAT(e.date, '%Y-%m-%dT%H:%i') as date,
            c.category_name,
            c.category_id,
            a.account_name,
            a.account_id
        FROM Expenses e
        JOIN Category c ON e.category_id = c.category_id
        JOIN Account a ON e.account_id = a.account_id
        WHERE e.Username = %s
        ORDER BY e.date DESC
        LIMIT %s
    """, (session['username'], expense_limit))
        expenses = cursor.fetchall()
        
        return render_template('home.html', 
                             username=session['username'],
                             accounts=accounts,
                             categories=categories,
                             incomes=incomes,
                             expenses=expenses)
    except mysql.connector.Error as err:
        flash(f'Database error: {err.msg}')
        return redirect(url_for('login'))
    
    finally:
        cursor.close()
        db.close()

    

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        amount = float(request.form['amount'])
        category_id = int(request.form['category_id'])
        date = request.form['date']
        account_id = int(request.form['account_id'])
        username = session['username']
        
        # Convert datetime-local to time
        time_part = date.split('T')[1]  # Extract time part from "YYYY-MM-DDTHH:MM"
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Adjusted parameter order to match stored procedure
        cursor.callproc('AddExpense', [
            amount,
            category_id,
            time_part,
            account_id,
            username
        ])
        
        db.commit()
        flash('Expense added successfully!')

    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error adding expense: {err.msg}')
    except ValueError as err:
        flash(f'Invalid input: Please check your values')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/add_income', methods=['POST'])
def add_income():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        amount = float(request.form['amount'])
        date = request.form['date']
        account_id = int(request.form['account_id'])
        username = session['username']
        
        # Convert datetime-local to time
        time_part = date.split('T')[1]  # Extract time part from "YYYY-MM-DDTHH:MM"
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Adjusted parameter order to match stored procedure
        cursor.callproc('AddIncome', [
            amount,
            time_part,
            account_id,
            username
        ])
        
        db.commit()
        flash('Income added successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error adding income: {err.msg}')
    except ValueError as err:
        flash(f'Invalid input: Please check your values')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/add_category', methods=['POST'])
def add_category():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        category_name = request.form['category_name']
        username = session['username']
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call AddCategory stored procedure
        cursor.callproc('AddCategory', [category_name, username])
        
        db.commit()
        flash('Category added successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error adding category: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/add_account', methods=['POST'])
def add_account():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        account_name = request.form['account_name']
        balance = float(request.form['balance'])
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call CreateAccount stored procedure with username
        cursor.callproc('CreateAccount', [
            account_name, 
            balance,
            session['username']
        ])
        
        db.commit()
        flash('Account added successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error adding account: {err.msg}')
    except ValueError:
        flash('Invalid balance amount')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('accounts'))

@app.route('/edit_income', methods=['POST'])
def edit_income():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        income_id = int(request.form['income_id'])
        new_amount = float(request.form['amount'])
        date = request.form['date']
        
        # Convert datetime-local to time
        time_part = date.split('T')[1]  # Extract time part
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Note: EditIncome only takes income_id, new_amount, and new_date
        cursor.callproc('EditIncome', [
            income_id,
            new_amount,
            time_part
        ])
        
        db.commit()
        flash('Income updated successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error updating income: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        expense_id = int(request.form['expense_id'])
        new_amount = float(request.form['amount'])
        new_category_id = int(request.form['category_id'])
        date = request.form['date']
        
        # Convert datetime-local to time
        time_part = date.split('T')[1]  # Extract time part
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Note: EditExpense takes expense_id, new_amount, new_category_id, and new_date
        cursor.callproc('EditExpense', [
            expense_id,
            new_amount,
            new_category_id,
            time_part
        ])
        
        db.commit()
        flash('Expense updated successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error updating expense: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/remove_income/<int:income_id>')
def remove_income(income_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Changed from RemoveIncome to DeleteIncome to match your procedure name
        cursor.callproc('DeleteIncome', [income_id])
        
        db.commit()
        flash('Income removed successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error removing income: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/remove_expense/<int:expense_id>')
def remove_expense(expense_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.callproc('RemoveExpense', [expense_id])
        
        db.commit()
        flash('Expense removed successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error removing expense: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))

@app.route('/delete_category', methods=['POST'])
def delete_category():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        category_id = int(request.form['category_id'])
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call the DeleteCategory stored procedure
        cursor.callproc('DeleteCategory', [category_id])
        
        db.commit()
        flash('Category deleted successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error deleting category: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('home'))



@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('profile'))
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call the ChangePassword stored procedure
        cursor.callproc('ChangePassword', [session['username'], new_password])
        
        db.commit()
        flash('Password changed successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error changing password: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    flash('You have been logged out successfully!')
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Simple admin check - username is 'admin'
        is_admin = (session['username'] == 'admin')
        
        users = []
        if is_admin:
            # Fetch all users except current admin
            cursor.execute("""
                SELECT Username 
                FROM Users 
                WHERE Username != 'admin'
            """)
            users = cursor.fetchall()
        
        return render_template('profile.html', 
                             username=session['username'],
                             is_admin=is_admin,
                             users=users)
    
    finally:
        cursor.close()
        db.close()


@app.route('/delete_user/<username>')
def delete_user(username):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Check if current user is admin
    if session['username'] != 'admin':
        flash('Unauthorized access!')
        return redirect(url_for('profile'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call the RemoveUser stored procedure
        cursor.callproc('RemoveUser', [username])
        
        db.commit()
        flash(f'User {username} has been deleted successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error deleting user: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('profile'))

@app.route('/accounts')
def accounts():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Get accounts with their balances and transaction totals
        cursor.execute("""
            SELECT 
                a.account_id,
                a.account_name,
                a.balance,
                COALESCE((
                    SELECT SUM(amount) 
                    FROM Income 
                    WHERE account_id = a.account_id
                ), 0) as total_income,
                COALESCE((
                    SELECT SUM(amount) 
                    FROM Expenses 
                    WHERE account_id = a.account_id
                ), 0) as total_expenses
            FROM Account a
            WHERE a.Username = %s
            GROUP BY a.account_id
        """, (session['username'],))
        
        accounts = cursor.fetchall()
        return render_template('accounts.html', accounts=accounts)
        
    finally:
        cursor.close()
        db.close()

@app.route('/remove_account/<int:account_id>')
def remove_account(account_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # First verify that this account belongs to the current user
        cursor.execute("""
            SELECT Username FROM Account 
            WHERE account_id = %s
        """, (account_id,))
        
        result = cursor.fetchone()
        if not result or result[0] != session['username']:
            flash('Unauthorized access or account not found!')
            return redirect(url_for('accounts'))
        
        # Delete the account (trigger will handle related records)
        cursor.execute("DELETE FROM Account WHERE account_id = %s", (account_id,))
        
        db.commit()
        flash('Account deleted successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error deleting account: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('accounts'))

@app.route('/edit_account', methods=['POST'])
def edit_account():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        account_id = int(request.form['account_id'])
        new_account_name = request.form['account_name']
        new_balance = float(request.form['balance'])
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Verify account belongs to current user
        cursor.execute("""
            SELECT Username FROM Account 
            WHERE account_id = %s
        """, (account_id,))
        
        result = cursor.fetchone()
        if not result or result[0] != session['username']:
            flash('Unauthorized access or account not found!')
            return redirect(url_for('accounts'))
        
        # Call UpdateAccount procedure
        cursor.callproc('UpdateAccount', [
            account_id,
            new_account_name,
            new_balance
        ])
        
        db.commit()
        flash('Account updated successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error updating account: {err.msg}')
    except ValueError:
        flash('Invalid input values')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('accounts'))

@app.route('/budgets')
def budgets():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Get categories for the current user
        cursor.execute("""
            SELECT category_id, category_name 
            FROM Category 
            WHERE Username = %s
        """, (session['username'],))
        categories = cursor.fetchall()
        
        # Get budgets with their current spending within the budget period
        cursor.execute("""
            SELECT 
                b.budget_id,
                b.budget_amount as amount,
                b.start_date,
                b.end_date,
                c.category_name,
                COALESCE(SUM(
                    CASE 
                        WHEN e.date >= b.start_date 
                        AND e.date <= b.end_date 
                        THEN e.amount 
                        ELSE 0 
                    END
                ), 0) as spent
            FROM Budget b
            JOIN Category c ON b.category_id = c.category_id
            LEFT JOIN Expenses e ON c.category_id = e.category_id
            WHERE b.Username = %s
            GROUP BY 
                b.budget_id,
                b.budget_amount,
                b.start_date,
                b.end_date,
                c.category_name
        """, (session['username'],))
        
        budgets = cursor.fetchall()
        
        # Calculate total spent and prepare chart data
        total_spent = sum(budget['spent'] for budget in budgets)
        category_names = [budget['category_name'] for budget in budgets]
        category_spent = [float(budget['spent']) for budget in budgets]
        
        return render_template('budgets.html', 
                             budgets=budgets, 
                             categories=categories,
                             total_spent=total_spent,
                             category_names=category_names,
                             category_spent=category_spent)
        
    except mysql.connector.Error as err:
        flash(f'Database error: {err.msg}')
        return redirect(url_for('home'))
    finally:
        cursor.close()
        db.close()

@app.route('/add_budget', methods=['POST'])
def add_budget():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        budget_amount = float(request.form['budget_amount'])
        category_id = int(request.form['category_id'])
        start_date = request.form['start_date']  # Will be in YYYY-MM-DD format
        end_date = request.form['end_date']      # Will be in YYYY-MM-DD format
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Call AddBudget stored procedure
        cursor.callproc('AddBudget', [
            budget_amount,
            start_date,
            end_date,
            session['username'],
            category_id
        ])
        
        db.commit()
        flash('Budget added successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error adding budget: {err.msg}')
    except ValueError:
        flash('Invalid input values')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('budgets'))
    
@app.route('/edit_budget', methods=['POST'])
def edit_budget():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        budget_id = int(request.form['budget_id'])
        new_amount = float(request.form['budget_amount'])
        new_start_date = request.form['start_date']
        new_end_date = request.form['end_date']
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Verify budget belongs to current user
        cursor.execute("""
            SELECT Username FROM Budget 
            WHERE budget_id = %s
        """, (budget_id,))
        
        result = cursor.fetchone()
        if not result or result[0] != session['username']:
            flash('Unauthorized access or budget not found!')
            return redirect(url_for('budgets'))
        
        # Call EditBudget procedure
        cursor.callproc('EditBudget', [
            budget_id,
            new_amount,
            new_start_date,
            new_end_date
        ])
        
        db.commit()
        flash('Budget updated successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error updating budget: {err.msg}')
    except ValueError:
        flash('Invalid input values')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('budgets'))

@app.route('/remove_budget/<int:budget_id>')
def remove_budget(budget_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Verify budget belongs to current user
        cursor.execute("""
            SELECT Username FROM Budget 
            WHERE budget_id = %s
        """, (budget_id,))
        
        result = cursor.fetchone()
        if not result or result[0] != session['username']:
            flash('Unauthorized access or budget not found!')
            return redirect(url_for('budgets'))
        
        # Delete the budget
        cursor.execute("""
            DELETE FROM Budget 
            WHERE budget_id = %s
        """, (budget_id,))
        
        db.commit()
        flash('Budget deleted successfully!')
        
    except mysql.connector.Error as err:
        db.rollback()
        flash(f'Error deleting budget: {err.msg}')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('budgets'))

@app.route('/category_expenses')
def category_expenses():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Nested query to calculate total expenses per category
        cursor.execute("""
            SELECT c.category_name, 
                   (SELECT SUM(e.amount) 
                    FROM Expenses e 
                    WHERE e.category_id = c.category_id 
                    AND e.Username = %s) AS total_expense
            FROM Category c
            WHERE c.Username = %s
        """, (session['username'], session['username']))
        
        category_expenses = cursor.fetchall()
        
        return render_template('category_expenses.html', category_expenses=category_expenses)
        
    except mysql.connector.Error as err:
        flash(f'Database error: {err.msg}')
        return redirect(url_for('home'))
    finally:
        cursor.close()
        db.close()

if __name__ == '__main__':
    app.run(debug=True)
