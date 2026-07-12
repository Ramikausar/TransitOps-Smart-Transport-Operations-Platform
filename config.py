import os

class Config:
      # Secret key for CSRF and session signing
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-transitops-secure-12345')
    
    # Database configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f'sqlite:///{os.path.join(BASE_DIR, "transitops.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for uploads
