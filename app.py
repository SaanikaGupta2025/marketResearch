from flask import Flask, render_template, jsonify, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from newsapi import NewsApiClient
from flask_migrate import Migrate  # Import Flask-Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Attach Flask-Migrate to the app and database

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

newsapi = NewsApiClient(api_key='2440328392324471a6849541b7afa6d9')


# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    preferences = db.Column(db.Text, default="")  # Store liked and disliked articles


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/api/articles')
@login_required
def get_articles():
    try:
        preferences = current_user.preferences.split(',')

        # Add a fallback for empty preferences
        if not preferences or preferences == ['']:
            preferences = ['like:venture capital']

        recommended_articles = get_recommendations(preferences)
        return jsonify(recommended_articles)

 # Summarize articles using OpenAI
        summarized_articles = []
        for article in recommended_articles:
            prompt = f"Summarize this article:\n\nTitle: {article['title']}\n\n{article['description'] or article['content']}"
            response = openai.Completion.create(
                engine= "text-davinci-003",
                prompt=prompt,
                max_tokens=100 #Adjust length as needed 
            )
            # Replace this OpenAI call with a dummy summary if not using OpenAI for now
            summary = article['description'] or "No summary available."
            summarized_articles.append({
                "title": article["title"],
                "url": article["url"],
                "summary": summary
            })
       
        return jsonify(summarized_articles)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/account')
@login_required
def account():
    return render_template('account.html', name=current_user.username)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/like_article', methods=['POST'])
@login_required
def like_article():
    article_title = request.json['title']
    preferences = current_user.preferences.split(',')
    if f"like:{article_title}" not in preferences:
        preferences.append(f"like:{article_title}")
    current_user.preferences = ','.join(preferences)
    db.session.commit()
    return jsonify(success=True)


@app.route('/dislike_article', methods=['POST'])
@login_required
def dislike_article():
    article_title = request.json['title']
    preferences = current_user.preferences.split(',')
    if f"dislike:{article_title}" not in preferences:
        preferences.append(f"dislike:{article_title}")
    current_user.preferences = ','.join(preferences)
    db.session.commit()
    return jsonify(success=True)


def get_recommendations(preferences):
    print("in get recommendations")
    liked_articles = [p.split(':')[1] for p in preferences if p.startswith('like:')]
    print(liked_articles)

    # Simple implementation using NewsAPI with keywords from liked articles
    recommended_articles = []
    for title in liked_articles:
        search_results = newsapi.get_everything(q=title)
        recommended_articles.extend(search_results.get('articles', [])[:3])  # Limit to 3 per liked article

    # Add fallback if no articles were found
    if not recommended_articles:
        print("no articles")
        return newsapi.get_top_headlines(category='business', language='en').get('articles', [])[:3]

    return recommended_articles



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This creates the database and tables based on your models
    app.run(debug=True)
