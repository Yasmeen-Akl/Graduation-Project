class Config:
    DEBUG=True
    SQLALCHEMY_DATABASE_URI='mysql+pymysql://root:@127.0.0.1:3306/usersdata'
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024