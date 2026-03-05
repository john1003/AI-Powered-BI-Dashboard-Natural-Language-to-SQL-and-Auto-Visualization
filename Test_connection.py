from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://root:Jeroni%40123@localhost:3306/ai_bi_dashboard"
)

try:
    with engine.connect() as conn:
        print("✅ Connected to MySQL successfully!")
except Exception as e:
    print("❌ Connection failed")
    print(e)